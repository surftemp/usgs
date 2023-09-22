
import requests
import os
import tempfile
import logging

""" Some code to download a scene from the Landsat 8 data stored on Google Cloud Platform
"""
LOGGER = logging.getLogger(__name__)

#
BASE_URL = "https://storage.googleapis.com/gcp-public-data-landsat/LC08/01/%s/%s/%s/%s" # row,col,product_id,filename
SUFFIXES = ["B1.TIF","B2.TIF","B3.TIF", "B4.TIF","B5.TIF","B6.TIF",
         "B7.TIF","B8.TIF","B9.TIF", "B10.TIF","B11.TIF","BQA.TIF","MTL.txt","ANG.txt"]

class GCPStorage(object):
    """
    Handle the download of a particular scene, currently only tested with catalog=EE and dataset=LANDSAT_8_C1
    """

    def __init__(self,catalog,dataset,scene_id,product_id,suffix_filter=""):
        """
        Set up, specifying the details of the scene that will be downloaded

        :param catalog: catalog for example EE
        :param dataset: dataset for example LANDSAT_8_C1
        :param scene_id: scene_id for example LC80920742019251LGN00
        :param product_id: product_id for example LC08_L1TP_092074_20190908_20190917_01_T1
        :param suffix_filter: filter out filenames not having this suffix
        """
        self.catalog = catalog
        self.dataset = dataset
        self.scene_id = scene_id
        self.product_id = product_id
        self.suffix_filter = suffix_filter
        self.destination_folder = tempfile.TemporaryDirectory()

    def download(self):
        """
        Perform the downloads for this scene

        :return list of paths of the downloaded files
        :raises requests exception if any of the downloads failed
        """
        filename_url_pairs = []
        # bit messy, pick apart the product id and get the row and column
        id_segments = self.product_id.split("_")
        row = id_segments[2][0:3]
        col = id_segments[2][3:6]

        # work through each of the file suffixes and build the (filename,download url) pairs
        for suffix in SUFFIXES:
            filename = self.product_id+"_"+suffix
            filename_url_pair = (filename,BASE_URL%(row,col,self.product_id,filename))
            filename_url_pairs.append(filename_url_pair)

        # prepare the output folder...
        outfolder = os.path.join(self.destination_folder.name,self.catalog,self.dataset,self.scene_id)
        os.makedirs(outfolder)

        # download each URL and store under the output folder
        downloaded_files = []
        for (filename,url) in filename_url_pairs:
            if self.suffix_filter and not filename.endswith(self.suffix_filter):
                LOGGER.info("Skipping: {} with no match to filter-suffix {}".format(filename,self.suffix_filter))
                continue
            resp =  requests.get(url)
            resp.raise_for_status()
            LOGGER.info("Downloading: {} from {}".format(filename,url))
            filepath = os.path.join(outfolder,filename)
            with open(filepath,"wb") as f:
                f.write(resp.content)
            downloaded_files.append(filepath)
        return downloaded_files



