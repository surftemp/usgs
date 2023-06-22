# Based on:

# ========================================================================================================================
#  USGS/EROS Inventory Service Example
#  Description: Download Landsat Collection 2 files
#  Usage: python download_sample.py -u username -p password -f fileType -g fileGroups
#         optional argument f refers to file type including 'bundle' or 'band'
#         optional argument g refers to file group ids that concatenated with comma
#         example: python download_landsat_c2.py -u username -p password -f band_group -g ls_c2l2_st_band,ls_c2l2_st_band
#  Note: This script can either read scenes from a text file (details can be found at line 28) or send
#        scene-search request to retrieve scenes (will need to comment out line 128-143 and uncomment line
#        145-160 and update the search filter at line 147-162)
# =========================================================================================================================

import json
import requests
import sys
import time
import argparse
import re
import threading
import datetime
import os


maxthreads = 5  # Threads count for downloads
sema = threading.Semaphore(value=maxthreads)
default_file_suffixes = ["sza.tif", "saa.tif", "vza.tif", "vaa.tif"]
threads = []
retry_delay = 30

# Send http request
def sendRequest(url, data, apiKey=None, exitIfNoResponse=True):
    json_data = json.dumps(data)
    print(url)
    print(json_data)

    if apiKey == None:
        response = requests.post(url, json_data)
    else:
        headers = {'X-Auth-Token': apiKey}
        response = requests.post(url, json_data, headers=headers)

    try:
        httpStatusCode = response.status_code
        if response == None:
            print("No output from service")
            if exitIfNoResponse:
                sys.exit()
            else:
                return False
        output = json.loads(response.text)
        if output['errorCode'] != None:
            print(output['errorCode'], "- ", output['errorMessage'])
            if exitIfNoResponse:
                sys.exit()
            else:
                return False
        if httpStatusCode == 404:
            print("404 Not Found")
            if exitIfNoResponse:
                sys.exit()
            else:
                return False
        elif httpStatusCode == 401:
            print("401 Unauthorized")
            if exitIfNoResponse:
                sys.exit()
            else:
                return False
        elif httpStatusCode == 400:
            print("Error Code", httpStatusCode)
            if exitIfNoResponse:
                sys.exit()
            else:
                return False
    except Exception as e:
        response.close()
        print(e)
        if exitIfNoResponse:
            sys.exit()
        else:
            return False
    response.close()

    return output['data']


def downloadFile(url, to_path):
    sema.acquire()
    try:
        response = requests.get(url, stream=True)
        disposition = response.headers['content-disposition']
        filename = re.findall("filename=(.+)", disposition)[0].strip("\"")
        print(f"Downloading {filename} ...")
        with open(os.path.join(to_path,filename), 'wb') as f:
            f.write(response.content)
        print(f"Downloaded {filename}")
        sema.release()
    except Exception as e:
        print(f"Failed to download from {url}. Will try to re-download after a {retry_delay} second display.")
        sema.release()
        time.sleep(retry_delay)
        runDownload(threads, url, to_path)


def runDownload(threads, url, to_path):
    thread = threading.Thread(target=downloadFile, args=(url,to_path))
    threads.append(thread)
    thread.start()

if __name__ == '__main__':
    # User input
    parser = argparse.ArgumentParser()

    parser.add_argument('-u', '--username', required=True, help='Username')
    parser.add_argument('-p', '--password', required=True, help='Password')
    parser.add_argument('-f', '--filename', required=True, help='download entityId list')
    parser.add_argument('-o', '--output-folder', default=".", help='output folder path')
    parser.add_argument('-s', '--file-suffixes', nargs="+", help='output folder path')
    parser.add_argument('-t', '--type-of-id', choices=('entity','display'), default='display', help='output folder path')

    args = parser.parse_args()

    username = args.username
    password = args.password
    scenefile = args.filename
    output_folder = args.output_folder

    suffixes = args.file_suffixes
    if suffixes is None or len(suffixes) == 0:
        suffixes = default_file_suffixes
    print(suffixes)

    def include_file(displayId):
        name = displayId.lower()
        for ending in suffixes:
            if name.lower().endswith(ending.lower()):
                return True
        return False

    label = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\nRunning Scripts...\n")
    startTime = time.time()

    serviceUrl = "https://m2m.cr.usgs.gov/api/api/json/stable/"

    # Login
    payload = {'username': username, 'password': password}
    apiKey = sendRequest(serviceUrl + "login", payload)
    print("API Key: " + apiKey + "\n")

    entityIds = []

    with open(scenefile, "r") as f:
        lines = f.readlines()

    datasetName = lines[0].strip()

    print("Scenes details:")
    print(f"Dataset name: {datasetName}")

    lines.pop(0)
    for line in lines:
        line_id = line.strip()
        if args.type_of_id == "display":
            payload = {
                "datasetName":datasetName,
                "entityId":line_id,
                "idType": "displayId",
                "metadataType": "summary"
            }
            results = sendRequest(serviceUrl + "scene-metadata", payload, apiKey)
            if results:
                entityIds.append(results["entityId"])
            else:
                print(f"WARNING No metadata found for scene {line_id}, ignoring")
        else:
            entityIds.append(line_id)



    payload = {
        "entityIds": entityIds,
        "datasetName": datasetName
    }

    print("Getting product download options...\n")
    products = sendRequest(serviceUrl + "download-options", payload, apiKey)
    print("Got product download options\n")

    # Select products
    downloads = []

    # Select band files
    for product in products:
        if product["secondaryDownloads"] is not None and len(product["secondaryDownloads"]) > 0:
            for secondaryDownload in product["secondaryDownloads"]:
                if secondaryDownload["bulkAvailable"]:
                    if include_file(secondaryDownload["displayId"]):
                        downloads.append(
                            {"entityId": secondaryDownload["entityId"], "productId": secondaryDownload["id"]})

    if len(downloads) == 0:
        print("No downloads")
        sys.exit(0)

    payload = {
        "downloads": downloads,
        "label": label
    }

    print(f"Sending download request ...\n")
    results = sendRequest(serviceUrl + "download-request", payload, apiKey)
    print(f"Done sending download request\n")

    # Attempt the download URLs
    for result in results['availableDownloads']:
        # print(f"Get download url: {result['url']}\n")
        runDownload(threads, result['url'], output_folder)

    preparingDownloadCount = len(results['preparingDownloads'])
    preparingDownloadIds = []
    if preparingDownloadCount > 0:
        for result in results['preparingDownloads']:
            preparingDownloadIds.append(result['downloadId'])

        payload = {"label": label}

        results = sendRequest(serviceUrl + "download-retrieve", payload, apiKey, False)
        if results != False:
            for result in results['available']:
                if result['downloadId'] in preparingDownloadIds:
                    preparingDownloadIds.remove(result['downloadId'])
                    print(f"Get download url: {result['url']}\n")
                    runDownload(threads, result['url'],output_folder)

            for result in results['requested']:
                if result['downloadId'] in preparingDownloadIds:
                    preparingDownloadIds.remove(result['downloadId'])
                    print(f"Get download url: {result['url']}\n")
                    runDownload(threads, result['url'],output_folder)

        # Didn't get all download URLs, retrieve again after 30 seconds
        while len(preparingDownloadIds) > 0:
            print(f"{len(preparingDownloadIds)} downloads are not available yet. Waiting for 30s to retrieve again\n")
            time.sleep(30)
            results = sendRequest(serviceUrl + "download-retrieve", payload, apiKey, False)
            if results != False:
                for result in results['available']:
                    if result['downloadId'] in preparingDownloadIds:
                        preparingDownloadIds.remove(result['downloadId'])
                        print(f"Get download url: {result['url']}\n")
                        runDownload(threads, result['url'], output_folder)

    print("\nGot download urls for all downloads\n")

    # Logout
    endpoint = "logout"
    if sendRequest(serviceUrl + endpoint, None, apiKey) == None:
        print("Logged Out\n")
    else:
        print("Logout Failed\n")

    print("Downloading files... Please do not close the program\n")
    for thread in threads:
        thread.join()

    print("Complete Downloading")

    executionTime = round((time.time() - startTime), 2)
    print(f'Total time: {executionTime} seconds')
