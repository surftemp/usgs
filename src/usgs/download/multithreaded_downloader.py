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
import shutil

import requests
import sys
import time
import argparse
import re
import threading
import datetime
import os

from usgs.utils.file_utils import FileUtils

class MultiThreadedDownloader:

    def __init__(self, file_cache_index_path=None, maxthreads=5, retry_delay=30):

        self.maxthreads = maxthreads  # Threads count for downloads
        self.sema = threading.Semaphore(value=maxthreads)
        self.threads = []
        self.retry_delay = retry_delay
        self.file_cache = FileUtils(file_cache_index_path) if file_cache_index_path else None

    # Send http request
    def sendRequest(self, url, data, apiKey=None, exitIfNoResponse=True):
        json_data = json.dumps(data)

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

    def download_file(self, url, download_folder, output_folder):
        self.sema.acquire()
        try:
            response = requests.get(url, stream=True)
            disposition = response.headers['content-disposition']
            filename = re.findall("filename=(.+)", disposition)[0].strip("\"")
            print(f"Downloading {filename} ...")
            download_path = os.path.join(download_folder, filename)
            output_path = os.path.join(output_folder, filename)
            with open(download_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded {filename}")
            if download_path != output_path:
                print("creating symlink to download: " + filename)
                os.symlink(download_path,output_path)

            self.sema.release()
        except Exception as e:
            print(
                f"Failed to download from {url}: {str(e)}. Will try to re-download after a {self.retry_delay} second display.")
            self.sema.release()
            time.sleep(self.retry_delay)
            self.run_download(url, download_folder, output_folder)

    def run_download(self, url, download_folder, output_folder):
        thread = threading.Thread(target=lambda *dargs: self.download_file(*dargs), args=(url, download_folder, output_folder))
        self.threads.append(thread)
        thread.start()

    def fetch(self, username, password, scenefile, download_folder, output_folder, limit, suffixes):

        with open(scenefile, "r") as f:
            lines = f.readlines()

        dataset_name = lines[0].strip()
        download_folder = download_folder if download_folder is not None else output_folder

        os.makedirs(output_folder, exist_ok=True)
        if output_folder != download_folder:
            os.makedirs(download_folder, exist_ok=True)

        def include_file(display_id):
            required_suffix = False
            filename = display_id
            for ending in suffixes:
                if filename.lower().endswith(ending.lower()):
                    required_suffix = True

            if not required_suffix:
                return False

            download_path = os.path.join(download_folder, filename)
            output_path = os.path.join(output_folder,filename)

            if os.path.exists(output_path):
                print("already in output: "+filename)
                return False

            if os.path.exists(download_path):
                print("already downloaded: "+download_path)
                if download_path != output_path:
                    print("creating symlink from download to output: "+filename)
                    os.symlink(download_path, output_path)
                return False

            if self.file_cache is not None:
                cached_path = self.file_cache.get_path(filename)
                if cached_path:
                    print("creating symlink from cache to output: " + filename)
                    os.symlink(cached_path, output_path)
                    return False

            return True

        label = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        startTime = time.time()

        serviceUrl = "https://m2m.cr.usgs.gov/api/api/json/stable/"

        # Login
        payload = {'username': username, 'password': password}
        apiKey = self.sendRequest(serviceUrl + "login", payload)

        entity_ids = []

        lines.pop(0)
        ctr = 0
        for line in lines:
            entity_id = line.strip()

            ctr += 1
            if limit is None or ctr <= limit:
                entity_ids.append(entity_id)

        payload = {
            "entityIds": entity_ids,
            "datasetName": dataset_name
        }

        print("Getting product download options...\n")
        products = self.sendRequest(serviceUrl + "download-options", payload, apiKey)
        print("Got product download options\n")

        # Select products
        downloads = []

        # Select band files
        scanned_files = set()
        for product in products:
            if product["secondaryDownloads"] is not None and len(product["secondaryDownloads"]) > 0:
                for secondaryDownload in product["secondaryDownloads"]:
                    if secondaryDownload["bulkAvailable"]:
                        display_id = secondaryDownload["displayId"]
                        if display_id in scanned_files:
                            continue
                        scanned_files.add(display_id)
                        if include_file(display_id):
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
        results = self.sendRequest(serviceUrl + "download-request", payload, apiKey)
        print(f"Done sending download request\n")

        # Attempt the download URLs
        for result in results['availableDownloads']:
            self.run_download(result['url'], download_folder, output_folder)

        preparingDownloadCount = len(results['preparingDownloads'])
        preparingDownloadIds = []
        if preparingDownloadCount > 0:
            for result in results['preparingDownloads']:
                preparingDownloadIds.append(result['downloadId'])

            payload = {"label": label}

            results = self.sendRequest(serviceUrl + "download-retrieve", payload, apiKey, False)
            if results != False:
                for result in results['available']:
                    if result['downloadId'] in preparingDownloadIds:
                        preparingDownloadIds.remove(result['downloadId'])
                        self.run_download(result['url'], download_folder, output_folder)

                for result in results['requested']:
                    if result['downloadId'] in preparingDownloadIds:
                        preparingDownloadIds.remove(result['downloadId'])
                        self.run_download(result['url'], download_folder, output_folder)

            # Didn't get all download URLs, retrieve again after 30 seconds
            while len(preparingDownloadIds) > 0:
                print(
                    f"{len(preparingDownloadIds)} downloads are not available yet. Waiting for 30s to retrieve again\n")
                time.sleep(30)
                results = self.sendRequest(serviceUrl + "download-retrieve", payload, apiKey, False)
                if results != False:
                    for result in results['available']:
                        if result['downloadId'] in preparingDownloadIds:
                            preparingDownloadIds.remove(result['downloadId'])
                            self.run_download(result['url'], download_folder, output_folder)

        print("\nGot download urls for all downloads\n")

        # Logout
        endpoint = "logout"
        if self.sendRequest(serviceUrl + endpoint, None, apiKey) == None:
            print("Logged Out\n")
        else:
            print("Logout Failed\n")

        print("Downloading files... Please do not close the program\n")
        for thread in self.threads:
            thread.join()

        print("Complete Downloading")

        executionTime = round((time.time() - startTime), 2)
        print(f'Total time: {executionTime} seconds')

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-u', '--username', default=os.getenv("USGS_USERNAME"), help='Username')
    parser.add_argument('-p', '--password', default=os.getenv("USGS_PASSWORD"), help='Password')
    parser.add_argument('-f', '--filename', required=True, help='download entityId list')
    parser.add_argument('-d', '--download-folder', default=None, help='download folder path')
    parser.add_argument('-o', '--output-folder', default=".", help='output folder path')
    parser.add_argument('-s', '--file-suffixes', nargs="+", help='specify file suffix to download')
    parser.add_argument('-c', '--file-cache-index', type=str,
                        help='path to an key-value DBM index with filename->path cache lookup',default=None)
    parser.add_argument('-l', '--limit', type=int, help='limit to this many items', default=None)

    args = parser.parse_args()

    dl = MultiThreadedDownloader(args.file_cache_index)
    dl.fetch(args.username, args.password, args.filename,
             args.download_folder, args.output_folder, args.limit,
             args.file_suffixes)

if __name__ == '__main__':
    main()


