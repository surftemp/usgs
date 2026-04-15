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
import logging
import csv
import requests
import sys
import time
import argparse
import re
import threading
import datetime
import os
import queue
import rioxarray
import math

from usgs import VERSION as USGS_VERSION

from usgs.utils.file_utils import FileUtils

EXCLUDE_PRODUCTS = ["L2SR"]


def create_download_path(download_folder, filename):
    # for downloading to a separate cache folder, use year, month and day as subdirectories
    # to avoid creating a single folder with a massive number of files
    # split components to get the year and month
    # example LC08_L2SP_009012_20180324_20200901_02_T1_MTL.xml
    name_comps = filename.split("_")
    year = name_comps[3][0:4]
    month = name_comps[3][4:6]
    day = name_comps[3][6:8]
    download_folder_ymd = os.path.join(download_folder, year, month, day)
    os.makedirs(download_folder_ymd, exist_ok=True)
    return os.path.join(download_folder_ymd, filename)


class MultiThreadedDownloader:

    def __init__(self, file_cache_index_path=None, maxthreads=5, retry_limit=3, batch_size=5):
        self.maxthreads = maxthreads  # Threads count for downloads
        self.jobqueue = queue.Queue()
        self.threads = []
        self.retry_limit = retry_limit
        self.file_cache = FileUtils(file_cache_index_path) if file_cache_index_path else None
        self.logger = logging.getLogger("MultiThreadedDownloader")

        self.scanned_files = set()
        self.expected_downloads = set()
        self.failed_downloads = set()
        self.completed_downloads = set()
        self.lock = threading.Lock()

        self.queue_loading = True
        self.batch_size = batch_size

    def report_failure(self, filename):
        self.lock.acquire()
        try:
            self.failed_downloads.add(filename)
        finally:
            self.lock.release()

    def report_success(self, filename):
        self.lock.acquire()
        try:
            self.completed_downloads.add(filename)
        finally:
            self.lock.release()

    # remove a path, ignoring any exceptions
    def remove_path(self, path):
        try:
            os.remove(path)
        except:
            self.logger.exception(f"removing {path}")

    # Send http request
    def send_request(self, url, data, apiKey=None):
        json_data = json.dumps(data)

        if apiKey == None:
            response = requests.post(url, json_data)
        else:
            headers = {'X-Auth-Token': apiKey}
            response = requests.post(url, json_data, headers=headers)
        try:
            if response is None:
                self.logger.error(f"No output from service for {url}")
                return False
            output = json.loads(response.text)
            httpStatusCode = response.status_code
            if output.get('errorCode', None) != None:
                error_code = output['errorCode']
                error_message = output.get('errorMessage', '')
                self.logger.error(f"{error_code}/{error_message} for {url}")
                return False
            if httpStatusCode >= 400:
                self.logger.error(f"{httpStatusCode} Not Found for {url}")
                return False
            response.close()
            return output['data']
        except Exception as e:
            if response is not None:
                response.close()
            self.logger.exception(f"fetching {url}")
            return False

    def check_download(self,download_path):
        if os.lstat(download_path).st_size == 0:
            self.logger.warning(f"Downloaded file {download_path} is empty")
            return False
        if download_path.lower().endswith(".tif"):
            # check that the TIF file can be loaded
            da = None
            try:
                da = rioxarray.open_rasterio(download_path).squeeze()
                # access the pixels in the 4 corners to test for corruption
                d1 = da[0, 0].item()
                d2 = da[0, -1].item()
                d3 = da[-1, 0].item()
                d4 = da[-1, -1].item()
            except:
                self.logger.exception(f"Download file {download_path} appears to be corrupt")
                return False
            finally:
                if da is not None:
                    da.close()
        return True

    def download_files(self):
        try:
            while True:
                job = self.jobqueue.get()
                if job is None:
                    return
                (url, download_folder, output_folder) = job
                try:
                    self.logger.debug(f"Downloading from {url}")
                    response = requests.get(url, stream=True)
                    if not response.ok:
                        raise ValueError("bad response")
                    disposition = response.headers['content-disposition']
                    filename = re.findall("filename=(.+)", disposition)[0].strip("\"")
                    self.logger.debug(f"Downloading {filename} ...")
                    if download_folder != output_folder:
                        download_path = create_download_path(download_folder, filename)
                    else:
                        download_path = os.path.join(download_folder, filename)
                    output_path = os.path.join(output_folder, filename)
                    content = response.content  # this should read the data from the connection
                    with open(download_path, 'wb') as f:
                        try:
                            f.write(content)
                        except:
                            # write failed
                            # do not leave a broken file behind
                            self.remove_path(download_path)
                            raise

                    # check that the downloaded file is not empty or corrupt before marking as complete
                    if self.check_download(download_path):
                        self.logger.info(f"Downloaded {filename}")
                        if download_path != output_path:
                            if os.path.exists(output_path):
                                self.remove_path(output_path)
                            self.logger.debug(f"creating symlink {output_path} to {download_path}")
                            os.symlink(download_path, output_path)
                        self.report_success(url)
                    else:
                        self.remove_path(download_path)
                        self.jobqueue.put((url, download_folder, output_folder))
                except Exception:
                    self.logger.exception(f"Failed to download from {url}")
                    self.jobqueue.put((url, download_folder, output_folder))
        except:
            self.logger.exception("download_files") # this should not be reachable

    def fetch(self, username, token, scenefile, download_folder, output_folder, limit, suffixes, exclude_suffixes,
              no_download=False, download_summary_path=""):

        # read the input file
        lines = []
        with open(scenefile, "r") as f:
            rdr = csv.reader(f)
            for row in rdr:
                lines.append(row)

        if len(lines) == 0:
            self.logger.warning(f"input CSV file is empty")
            return

        # decode it
        all_entity_ids = []
        if len(lines[0]) == 1:
            # expected format is:
            #
            # datasetId
            # entityId
            # entityId
            # .....
            dataset_name = lines[0][0].strip()
            for line in lines[1:]:
                all_entity_ids.append(line[0].strip())
        elif len(lines[0]) == 3:
            # format is
            #
            # catalogId, datasetId, entityId
            # catalogId, datasetId, entityId
            # ...
            dataset_name = lines[0][1].strip()
            for line in lines:
                all_entity_ids.append(line[2].strip())
        else:
            raise ValueError("input file format not recognized")

        download_folder = download_folder if download_folder is not None else output_folder

        os.makedirs(output_folder, exist_ok=True)
        if output_folder != download_folder:
            os.makedirs(download_folder, exist_ok=True)

        def require_file(display_id):
            filename = display_id
            filename_comps = filename.split("_")
            product = filename_comps[1]
            if product in EXCLUDE_PRODUCTS:
                return False
            if exclude_suffixes:
                for ending in exclude_suffixes:
                    if filename.lower().endswith(ending.lower()):
                        return False
            if suffixes:
                for ending in suffixes:
                    if filename.lower().endswith(ending.lower()):
                        return True
                return False
            return True

        def include_file_for_download(display_id):
            filename = display_id
            if download_folder != output_folder:
                download_path = create_download_path(download_folder, filename)
            else:
                download_path = os.path.join(download_folder, filename)

            output_path = os.path.join(output_folder, filename)

            # check that the file exists, is not empty or points to a missing or empty symlink

            if os.path.isfile(output_path):
                if os.lstat(output_path).st_size > 0:
                    self.logger.debug(f"{filename} already in output")
                    return None
                else:
                    self.logger.warning(f"removing empty copies of {filename}")
                    self.remove_path(output_path)

            if os.path.islink(output_path):
                linked_path = os.readlink(output_path)
                if os.path.exists(linked_path):
                    if os.lstat(linked_path).st_size > 0:
                        self.logger.debug(f"{filename} already linked in output")
                        return None
                    else:
                        self.logger.warning(f"removing empty copies of {filename}")
                        self.remove_path(linked_path)
                        self.remove_path(output_path)
                else:
                    self.logger.warning(f"removing {filename} with broken sym-link")
                    self.remove_path(output_path)

            if os.path.exists(download_path):
                if os.lstat(download_path).st_size > 0:
                    self.logger.debug(f"{filename} already downloaded")
                    if download_path != output_path:
                        self.logger.debug(f"creating symlink from already downloaded {download_path} to {output_path}")
                        os.symlink(download_path, output_path)
                    return None
                else:
                    self.logger.warning(f"removing empty copies of {filename}")
                    self.remove_path(download_path)

            if self.file_cache is not None:
                cached_path = self.file_cache.get_path(filename)
                if cached_path:
                    self.logger.debug(f"creating symlink from cache {cached_path} to output {output_path}")
                    os.symlink(cached_path, output_path)
                    return None

            if no_download:
                self.logger.warning(f"{filename}: download required but not enabled")
                return None

            self.expected_downloads.add(filename)
            return download_path  # this file needs to be downloaded

        if limit is not None:
            all_entity_ids = all_entity_ids[:limit]

        serviceUrl = "https://m2m.cr.usgs.gov/api/api/json/stable/"

        # Login
        payload = {'username': username, 'token': token}
        apiKey = self.send_request(serviceUrl + "login-token", payload)

        if apiKey == False:
            self.logger.error("login failed, exiting")
            sys.exit(1)

        pending_entity_ids = all_entity_ids[:]

        startTime = time.time()

        batch_count = math.ceil(len(pending_entity_ids)/self.batch_size)
        batch_number = 0

        expected_outputs = []

        while len(pending_entity_ids):

            batch_number += 1
            self.logger.info(f"Processing batch: {batch_number}/{batch_count}")

            # get the next batch of entity ids
            entity_ids = pending_entity_ids[:self.batch_size]
            pending_entity_ids = pending_entity_ids[self.batch_size:]

            # process this batch
            label = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            payload = {
                "entityIds": entity_ids,
                "datasetName": dataset_name
            }

            self.logger.info(f"getting product download options for {len(entity_ids)} entities")
            products = self.send_request(serviceUrl + "download-options", payload, apiKey)
            if apiKey == False:
                self.logger.error("failed to get download options, exiting")
                sys.exit(1)

            if products is False:
                self.logger.error("api failure, exiting")
                sys.exit(1)

            if products is None:
                self.logger.error("no products returned, exiting")
                sys.exit(1)

            self.logger.info(f"got {len(products)} products for download")

            # Select products
            downloads = []

            # Select band files

            for product in products:
                product_entity_id = product["entityId"]
                if product["secondaryDownloads"] is not None and len(product["secondaryDownloads"]) > 0:
                    for secondaryDownload in product["secondaryDownloads"]:
                        if secondaryDownload["bulkAvailable"]:
                            display_id = secondaryDownload["displayId"]
                            if not require_file(display_id):
                                continue
                            if display_id in self.scanned_files:
                                continue
                            expected_outputs.append([product_entity_id, display_id])
                            self.scanned_files.add(display_id)

                            if include_file_for_download(display_id):
                                downloads.append(
                                    {"entityId": secondaryDownload["entityId"], "productId": secondaryDownload["id"]})

            nr_downloads = len(downloads)
            if nr_downloads == 0:
                self.logger.warning("no downloads required, exiting")
                continue
            else:
                self.logger.info(f"{nr_downloads} downloads required")

            payload = {
                "downloads": downloads,
                "label": label
            }

            self.logger.info("sending download request...")
            results = self.send_request(serviceUrl + "download-request", payload, apiKey)
            if results == False:
                self.logger.error("download request failed, exiting")
                sys.exit(1)

            self.logger.info("sent download request...")

            # Attempt the download URLs, add them to the job queue
            for result in results['availableDownloads']:
                self.jobqueue.put((result['url'], download_folder, output_folder))

            # start the worker threads
            for i in range(0, self.maxthreads):
                thread = threading.Thread(target=lambda *dargs: self.download_files())
                thread.start()
                self.threads.append(thread)

            self.logger.info("downloading files...")

            # for downloads that are still being prepared, wait for those
            preparingDownloadCount = len(results['preparingDownloads'])
            preparingDownloadIds = []
            if preparingDownloadCount > 0:
                for result in results['preparingDownloads']:
                    preparingDownloadIds.append(result['downloadId'])

                payload = {"label": label}

                # Didn't get all download URLs, retrieve again after 30 seconds
                while len(preparingDownloadIds) > 0:
                    self.logger.info(
                        f"{len(preparingDownloadIds)} downloads are not available yet. Waiting for 30s to retrieve again")
                    time.sleep(30)
                    results = self.send_request(serviceUrl + "download-retrieve", payload, apiKey)
                    if results != False:
                        for result in results['available']:
                            if result['downloadId'] in preparingDownloadIds:
                                preparingDownloadIds.remove(result['downloadId'])
                                self.jobqueue.put((result['url'], download_folder, output_folder))

            self.logger.info("got download urls for all downloads")

            # queue None values to terminate workers after first attempt to download
            for i in range(len(self.threads)):
                self.jobqueue.put(None)

            # wait for workers to complete first attempt
            for thread in self.threads:
                thread.join()
            self.threads = []

            # retries
            for retry in range(1,self.retry_limit+1):
                if not self.jobqueue.empty():
                    self.logger.warning(f"Retrying {self.jobqueue.qsize()} downloads (retry {retry}/{self.retry_limit})")
                    # start the worker threads
                    for i in range(0, self.maxthreads):
                        thread = threading.Thread(target=lambda *dargs: self.download_files())
                        thread.start()
                        self.threads.append(thread)
                    for i in range(len(self.threads)):
                        self.jobqueue.put(None)
                    for thread in self.threads:
                        thread.join()
                    self.threads = []

            if not self.jobqueue.empty():
                self.logger.warning(f"Failed {self.jobqueue.qsize()} downloads (no retries left)")
                while not self.jobqueue.empty():
                    (url, download_folder, output_folder) = self.jobqueue.get()
                    self.report_failure(url)

        self.logger.info("Completed")

        if download_summary_path:
            # write out a list of all the files that should have been downloaded
            download_summary_folder = os.path.split(download_summary_path)[0]
            os.makedirs(download_summary_folder, exist_ok=True)
            with open(download_summary_path, "w") as f:
                writer = csv.writer(f)
                for expected_output in expected_outputs:
                    writer.writerow(expected_output)

        # Logout
        endpoint = "logout"
        if self.send_request(serviceUrl + endpoint, None, apiKey) == None:
            self.logger.info("logged Out\n")
        else:
            self.logger.warning("logout Failed\n")

        executionTime = round((time.time() - startTime), 2)

        self.logger.info(
            f"Summary: \n\ttotal time: {executionTime} seconds\n\tscanned files: {len(self.scanned_files)} \n\tdownload attempted: {len(self.expected_downloads)} \n\tdownloads completed: {len(self.completed_downloads)} \n\tfailed downloads: {len(self.failed_downloads)}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-u', '--username', default=os.getenv("USGS_USERNAME"), help='Username')
    parser.add_argument('-t', '--token', default=os.getenv("USGS_TOKEN"), help='Access Token')
    parser.add_argument('-f', '--filename', required=True,
                        help='download entityId list or 3-column "catalogId,datasetId,entityId" CSV format')
    parser.add_argument('-d', '--download-folder', default=None, help='download folder path')
    parser.add_argument('-n', '--no-download', action="store_true", help='Do not download any new files')
    parser.add_argument('-o', '--output-folder', default=".", help='output folder path')
    parser.add_argument('-s', '--file-suffixes', nargs="+", help='specify file suffix to download')
    parser.add_argument('-x', '--exclude-file-suffixes', nargs="+", help='specify file suffix to exclude')
    parser.add_argument('-c', '--file-cache-index', type=str,
                        help='path to an key-value DBM index with filename->path cache lookup', default=None)
    parser.add_argument('-l', '--limit', type=int, help='limit to this many items', default=None)
    parser.add_argument('-e', '--download-summary-path', help='path to write a CSV with summary of expected downloads',
                        default='')
    parser.add_argument('-b', '--batch-size', type=int, help='divide into batches with this many scenes', default=5)
    parser.add_argument('-v', '--verbose', action="store_true", help='Enable verbose output')
    parser.add_argument(
        "--check-version",
        help="check that the version number of this tool matches the specified version string",
        default=None
    )

    args = parser.parse_args()

    if args.check_version:
        if USGS_VERSION != args.check_version:
            print(f"--check-version failed:  installed version {USGS_VERSION} is not equal to the requested version {args.check_version}")
            sys.exit(0)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if args.file_suffixes:
        xml_found = False
        txt_found = False
        for suffix in args.file_suffixes:
            suffix = suffix.lower()
            if suffix.endswith('xml'):
                xml_found = True
            if suffix.endswith('txt'):
                txt_found = True
        if not xml_found and not txt_found:
            logging.warning("--file-suffixes was specified but did not include xml or txt, it is recommended to download at least one of these to help with decoding")

    dl = MultiThreadedDownloader(file_cache_index_path=args.file_cache_index, batch_size=args.batch_size)
    dl.fetch(username=args.username, token=args.token, scenefile=args.filename,
             download_folder=os.path.abspath(args.download_folder) if args.download_folder else None,
             output_folder=os.path.abspath(args.output_folder), limit=args.limit,
             suffixes=args.file_suffixes, exclude_suffixes=args.exclude_file_suffixes,
             no_download=args.no_download, download_summary_path=args.download_summary_path)


if __name__ == '__main__':
    main()
