import tempfile
import time
import os
import os.path
import urllib.parse
from .download import Download_File
import logging

LOGGER = logging.getLogger(__name__)

class DownloadUSGS(object):
    """
    Handle the download of a particular scene from USGS
    Your account may likely need to request access at this page: https://ers.cr.usgs.gov/profile/access
    """

    def __init__(self,context,catalog,dataset,scene_id):
        """
        Set up, specifying the details of the scene that will be downloaded

        :param context: the API context
        :param catalog: catalog for example EE
        :param dataset: dataset for example LANDSAT_8_C1
        :param scene_id: scene_id for example LC80920742019251LGN00
        """
        self.context = context
        self.catalog = catalog
        self.dataset = dataset
        self.scene_id = scene_id
        self.destination_folder = tempfile.TemporaryDirectory()

    def download(self):
        """
        Perform the downloads for this scene

        :return list of paths of the downloaded files
        :raises requests exception if any of the downloads failed
        """
        options = self.context.DownloadOptions(self.dataset, self.scene_id)
        if options is None:
            LOGGER.error("Download failed.  Check that you have MACHINE / M2M access for your USGS account - visit https://ers.cr.usgs.gov/profile/access")

        downloads = []
        for option in options:
            displayId = option["displayId"]
            available = option["available"]
            if available:
                downloads.append({'entityId': option['entityId'], 'productId': option['id']})
            else:
                LOGGER.warning(displayId + " is not available for download")

        downloaded_files = []
        if downloads:
            label = "dl_"+self.scene_id
            requested_results = self.context.DownloadRequest(label, downloads)
            availableDownloads = requested_results.get("availableDownloads",[])
            requestedDownloads = requested_results.get("requestedDownloads", [])

            while len(availableDownloads) < len(downloads):
                LOGGER.info("%d downloads available, awaiting %d requested downloads"
                      % (len(availableDownloads),len(requestedDownloads)))
                time.sleep(30)
                status = self.context.DownloadRetrieve(label)
                availableDownloads = status.get("available",[])
                requestedDownloads = status.get("requested", [])

            filename_url_pairs = []
            for available_download in availableDownloads:
                url = available_download["url"]
                path = urllib.parse.urlparse(url)[2]
                filename = os.path.split(path)[1]
                filename_url_pairs.append((filename,url))

            # prepare the output folder...
            outfolder = os.path.join(self.destination_folder.name, self.catalog, self.dataset, self.scene_id)
            os.makedirs(outfolder)

            for (filename, url) in filename_url_pairs:
                downloaded_files.append(Download_File(url, outfolder, metadata={},
                                                      auth=(self.context.username, self.context.password)))

        return downloaded_files






