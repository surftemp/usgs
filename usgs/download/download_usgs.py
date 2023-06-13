import tempfile
import time
import os
import os.path
import urllib.parse
import logging
import json
import uuid

from .download import Download_File

LOGGER = logging.getLogger(__name__)

class DownloadUSGS(object):
    """
    Handle the download of a particular scene from USGS
    Your account may likely need to request access at this page: https://ers.cr.usgs.gov/profile/access
    """

    def __init__(self,context,catalog,dataset,scene_id,suffix_filter="",download_names=[]):
        """
        Set up, specifying the details of the scene that will be downloaded

        :param context: the API context
        :param catalog: catalog for example EE
        :param dataset: dataset for example LANDSAT_8_C1
        :param scene_id: scene_id for example LC80920742019251LGN00
        :param suffix_filter: filter out files not having this suffix
        :param download_names: a list of the names of individual scene files, eg B10.TIF, SZA.TIF
        """
        self.context = context
        self.catalog = catalog
        self.dataset = dataset
        self.scene_id = scene_id
        self.suffix_filter = suffix_filter
        self.download_names = download_names
        self.destination_folder = tempfile.TemporaryDirectory()

    def download(self):
        if len(self.download_names) > 0:
            self.download_selected()
        else:
            self.download_all()

    def download_all(self):
        """
        Perform the downloads for this scene

        :return list of paths of the downloaded files
        :raises requests exception if any of the downloads failed
        """
        options = self.context.DownloadOptions(self.dataset, self.scene_id, support_download_names=False)
        if options is None:
            LOGGER.error(
                "Download failed.  Check that you have MACHINE / M2M access for your USGS account - visit https://ers.cr.usgs.gov/profile/access")
            return []

        downloads = []
        for option in options:
            displayId = option["displayId"]
            available = option["available"]
            if available:
                downloads.append({'entityId': option['entityId'], 'productId': option['id']})
                LOGGER.info(displayId + " is available for download")
            else:
                LOGGER.warning(displayId + " is not available for download")

        return self.run_downloads(downloads)


    def download_selected(self):
        """
        Perform the downloads for this scene

        :return list of paths of the downloaded files
        :raises requests exception if any of the downloads failed
        """
        # prepare the output folder...
        outfolder = os.path.join(self.destination_folder.name, self.catalog, self.dataset, self.scene_id)
        os.makedirs(outfolder)

        options = self.context.DownloadOptions(self.dataset, self.scene_id, support_download_names=True)
        if options is None:
            LOGGER.error("Download failed.  Check that you have MACHINE / M2M access for your USGS account - visit https://ers.cr.usgs.gov/profile/access")
            return []

        downloads = []
        download_names_included = set()
        for option in options:
            available = option["available"]
            if available:
                secondaryDownloads = option["secondaryDownloads"]
                download_name = secondaryDownload["downloadName"]
                for secondaryDownload in secondaryDownloads:
                    if download_name in self.download_names and download_name not in download_names_included:
                        downloads.append({'entityId': secondaryDownload['entityId'], 'productId': secondaryDownload['id']})
                        download_names_included.add(download_name)
                    displayId = secondaryDownload["displayId"]
                    LOGGER.info(displayId + " is available for download")
            else:
                LOGGER.warning(displayId + " is not available for download")

        return self.run_downloads(downloads)

    def run_downloads(self,downloads):
        downloaded_files = []
        if downloads:
            label = uuid.uuid4().hex
            requested_results = self.context.DownloadRequest(label, downloads)
            time.sleep(5)
            status = self.context.DownloadRetrieve(label)
            availableDownloads = status.get("available", [])
            requestedDownloads = status.get("requested", [])

            while len(availableDownloads) < len(downloads):
                LOGGER.info("%d downloads available, awaiting %d requested downloads"
                            % (len(availableDownloads), len(requestedDownloads)))
                time.sleep(30)
                status = self.context.DownloadRetrieve(label)
                availableDownloads = status.get("available", [])
                requestedDownloads = status.get("requested", [])

            filename_url_pairs = []
            for available_download in availableDownloads:
                url = available_download["url"]
                path = urllib.parse.urlparse(url)[2]
                filename = os.path.split(path)[1]
                filename_url_pairs.append((filename, url))

            # prepare the output folder...
            outfolder = os.path.join(self.destination_folder.name, self.catalog, self.dataset, self.scene_id)
            os.makedirs(outfolder)

            for (filename, url) in filename_url_pairs:
                if self.suffix_filter and not filename.endswith(self.suffix_filter):
                    LOGGER.info(
                        "Skipping: {} with no match to filter-suffix {}".format(filename, self.suffix_filter))
                    continue
                downloaded_files.append(Download_File(url, outfolder, metadata={},
                                                      auth=(self.context.username, self.context.password)))


        return downloaded_files
