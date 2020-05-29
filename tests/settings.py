import unittest

from usgs.api.catalogs import Catalogs

USGS_USERNAME = ""
USGS_PASSWORD = ""


class Test_Login_Exists(unittest.TestCase):
    def test_usgs_username(self):
        self.assertTrue(USGS_USERNAME,
                        "Please set USGS_USERNAME in tests/settings.py")

    def test_usgs_password(self):
        self.assertTrue(USGS_PASSWORD,
                        "Please set USGS_PASSWORD in tests/settings.py")


CATALOG_ID = Catalogs.EarthExplorer.value
DATASET_NAME = "LANDSAT_8_C1"
