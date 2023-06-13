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

path = "/tmp"  # Fill a valid download path
maxthreads = 5  # Threads count for downloads
sema = threading.Semaphore(value=maxthreads)
label = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # Customized label using date time
threads = []
# The entityIds/displayIds need to save to a text file such as scenes.txt.
# The header of text file should follow the format: datasetName|displayId or datasetName|entityId.
# sample file - scenes.txt
# landsat_ot_c2_l2|displayId
# LC08_L2SP_012025_20201231_20210308_02_T1
# LC08_L2SP_012027_20201215_20210314_02_T1
scenesFile = 'scenes.txt'


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


def downloadFile(url):
    sema.acquire()
    try:
        response = requests.get(url, stream=True)
        disposition = response.headers['content-disposition']
        filename = re.findall("filename=(.+)", disposition)[0].strip("\"")
        print(f"Downloading {filename} ...\n")
        if path != "" and path[-1] != "/":
            filename = "/" + filename
        open(path + filename, 'wb').write(response.content)
        print(f"Downloaded {filename}\n")
        sema.release()
    except Exception as e:
        print(f"Failed to download from {url}. Will try to re-download.")
        sema.release()
        runDownload(threads, url)


def runDownload(threads, url):
    thread = threading.Thread(target=downloadFile, args=(url,))
    threads.append(thread)
    thread.start()


if __name__ == '__main__':
    # User input
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', required=True, help='Username')
    parser.add_argument('-p', '--password', required=True, help='Password')
    parser.add_argument('-f', '--fileType', required=False, choices=['bundle', 'band', 'band_group'],
                        help='File types to download, "bundle" for bundle files, "band" for band files and "band_group" for band files using file groups')
    parser.add_argument('-g', '--fileGroups', required=False, help='The file groups IDs used in the download request')

    args = parser.parse_args()

    username = args.username
    password = args.password
    fileType = args.fileType

    print("\nRunning Scripts...\n")
    startTime = time.time()

    serviceUrl = "https://m2m.cr.usgs.gov/api/api/json/stable/"

    # Login
    payload = {'username': username, 'password': password}
    apiKey = sendRequest(serviceUrl + "login", payload)
    print("API Key: " + apiKey + "\n")

    entityIds = []
    idField = 'entityId'

    # Option 1: Read scenes from a text file
    f = open(scenesFile, "r")
    lines = f.readlines()
    f.close()
    header = lines[0].strip()
    datasetName = header[:header.find("|")]
    idField = header[header.find("|") + 1:]

    print("Scenes details:")
    print(f"Dataset name: {datasetName}")
    print(f"Id field: {idField}\n")

    entityIds = []

    lines.pop(0)
    for line in lines:
        entityIds.append(line.strip())

    # Option 2: Search scenes by sending scene-search request
    # If you don't have a scenes text file that you can use scene-search to identify scenes you're interested in
    # datasetName = ''
    # payload = {
    #             'datasetName' : datasetName, # dataset alias
    #             'maxResults' : 10, # max results to return
    #             'startingNumber' : 1,
    #             'sceneFilter' : {} # scene filter
    #           }

    # results = sendRequest(serviceUrl + "scene-search", payload, apiKey)
    # for result in results['results']:
    #     if result['options']['bulk'] == True:
    #         entityIds.append(result['entityId'])

    # if len(entityIds) == 0:
    #     print('No entity is available for bulk download, please update your search filter')
    #     sys.exit()
    # Add scenes to a list
    listId = f"temp_{datasetName}_list"  # customized list id
    payload = {
        "listId": listId,
        'idField': idField,
        "entityIds": entityIds,
        "datasetName": datasetName
    }

    print("Adding scenes to list...\n")
    count = sendRequest(serviceUrl + "scene-list-add", payload, apiKey)
    print("Added", count, "scenes\n")

    # Get download options
    payload = {
        "listId": listId,
        "datasetName": datasetName
    }

    if fileType == 'band_group':
        payload['includeSecondaryFileGroups'] = True

    print("Getting product download options...\n")
    products = sendRequest(serviceUrl + "download-options", payload, apiKey)
    print("Got product download options\n")

    # Select products
    downloads = []
    if fileType == 'bundle':
        # Select bundle files
        for product in products:
            if product["bulkAvailable"] and product['downloadSystem'] != 'folder':
                downloads.append({"entityId": product["entityId"], "productId": product["id"]})
    elif fileType == 'band':
        # Select band files
        for product in products:
            if product["secondaryDownloads"] is not None and len(product["secondaryDownloads"]) > 0:
                for secondaryDownload in product["secondaryDownloads"]:
                    if secondaryDownload["bulkAvailable"]:
                        downloads.append(
                            {"entityId": secondaryDownload["entityId"], "productId": secondaryDownload["id"]})
    elif fileType == 'band_group':
        # Get secondary dataset ID and file group IDs with the scenes
        sceneFileGroups = []
        entityIds = []
        datasetId = None
        for product in products:
            if product["secondaryDownloads"] is not None and len(product["secondaryDownloads"]) > 0:
                for secondaryDownload in product["secondaryDownloads"]:
                    if secondaryDownload["bulkAvailable"] and secondaryDownload["fileGroups"] is not None:
                        if datasetId == None:
                            datasetId = secondaryDownload['datasetId']
                        for fg in secondaryDownload["fileGroups"]:
                            if fg not in sceneFileGroups:
                                sceneFileGroups.append(fg)
                            if secondaryDownload['entityId'] not in entityIds:
                                entityIds.append(secondaryDownload['entityId'])

        # Send dataset request to get the secondary dataset name by the dataset ID
        payload = {
            "datasetId": datasetId,
        }
        results = sendRequest(serviceUrl + "dataset", payload, apiKey)
        secondaryDatasetName = results['datasetAlias']

        # Add secondary scenes to a list
        secondaryListId = f"temp_{datasetName}_scecondary_list"  # customized list id
        payload = {
            "listId": secondaryListId,
            "entityIds": entityIds,
            "datasetName": secondaryDatasetName
        }

        print("Adding secondary scenes to list...\n")
        count = sendRequest(serviceUrl + "scene-list-add", payload, apiKey)
        print("Added", count, "secondary scenes\n")

        # Compare the provided file groups Ids with the scenes' file groups IDs
        fgs = args.fileGroups
        if fgs:
            fgs = fgs.split(",")
            fileGroups = []
            for fg in fgs:
                fg = fg.strip()
                if fg in sceneFileGroups:
                    fileGroups.append(fg)
        else:
            fileGroups = sceneFileGroups
    else:
        # Select all available files
        for product in products:
            if product["bulkAvailable"]:
                if product['downloadSystem'] != 'folder':
                    downloads.append({"entityId": product["entityId"], "productId": product["id"]})
                if product["secondaryDownloads"] is not None and len(product["secondaryDownloads"]) > 0:
                    for secondaryDownload in product["secondaryDownloads"]:
                        if secondaryDownload["bulkAvailable"]:
                            downloads.append(
                                {"entityId": secondaryDownload["entityId"], "productId": secondaryDownload["id"]})

                            # Send download-request
    if fileType != 'band_group':
        payload = {
            "downloads": downloads,
            "label": label
        }
    else:
        if len(fileGroups) > 0:
            payload = {
                "dataGroups": [
                    {
                        "fileGroups": fileGroups,
                        "datasetName": secondaryDatasetName,
                        "listId": secondaryListId
                    }
                ],
                "label": label
            }
        else:
            print('No file groups found')
            sys.exit()

    print(f"Sending download request ...\n")
    results = sendRequest(serviceUrl + "download-request", payload, apiKey)
    print(f"Done sending download request\n")

    if len(results['newRecords']) == 0 and len(results['duplicateProducts']) == 0:
        print('No records returned, please update your scenes or scene-search filter')
        sys.exit()

    # Attempt the download URLs
    for result in results['availableDownloads']:
        print(f"Get download url: {result['url']}\n")
        runDownload(threads, result['url'])

    preparingDownloadCount = len(results['preparingDownloads'])
    preparingDownloadIds = []
    if preparingDownloadCount > 0:
        for result in results['preparingDownloads']:
            preparingDownloadIds.append(result['downloadId'])

        payload = {"label": label}
        # Retrieve download URLs
        print("Retrieving download urls...\n")
        results = sendRequest(serviceUrl + "download-retrieve", payload, apiKey, False)
        if results != False:
            for result in results['available']:
                if result['downloadId'] in preparingDownloadIds:
                    preparingDownloadIds.remove(result['downloadId'])
                    print(f"Get download url: {result['url']}\n")
                    runDownload(threads, result['url'])

            for result in results['requested']:
                if result['downloadId'] in preparingDownloadIds:
                    preparingDownloadIds.remove(result['downloadId'])
                    print(f"Get download url: {result['url']}\n")
                    runDownload(threads, result['url'])

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
                        runDownload(threads, result['url'])

    print("\nGot download urls for all downloads\n")

    # Remove the scene list
    payload = {
        "listId": listId
    }
    sendRequest(serviceUrl + "scene-list-remove", payload, apiKey)

    if fileType == 'band_group':
        # Remove the secondary scene list
        payload = {
            "listId": secondaryListId
        }
        sendRequest(serviceUrl + "scene-list-remove", payload, apiKey)

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
