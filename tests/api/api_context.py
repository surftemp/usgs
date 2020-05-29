import unittest

from ..settings import USGS_USERNAME, USGS_PASSWORD, CATALOG_ID, DATASET_NAME
from usgs.api import api
from usgs.api.api_context import API_Context


class Test_API_Context(unittest.TestCase):
    def test_bad_login(self):
        with self.assertRaises(api.NotAuthorisedException):
            with API_Context(
                "this user does not exist",
                "password",
                CATALOG_ID
            ):
                pass

    def test_Status(self):
        self.assertTrue(API_Context.Status())

    def test_DatasetSearch(self):
        with API_Context(USGS_USERNAME, USGS_PASSWORD, CATALOG_ID) as context:
            j = context.DatasetSearch("landsat 8")
            dataset_names = [x["datasetName"] for x in j]
            self.assertIn(DATASET_NAME, dataset_names)

    def test_DatasetFields(self):
        with API_Context(USGS_USERNAME, USGS_PASSWORD, CATALOG_ID) as context:
            j = context.DatasetFields(DATASET_NAME)
            field_names = [x["name"] for x in j]
            self.assertIn("Landsat Product Identifier", field_names)

    def test_GridToLatLong(self):
        self.assertTrue(API_Context.GridToLatLong("WRS1", "polygon", 1, 1))

    def test_SceneSearch(self):
        N = 5
        with API_Context(USGS_USERNAME, USGS_PASSWORD, CATALOG_ID) as context:
            j = context.SceneSearch(DATASET_NAME, max_results=N)
            self.assertTrue(j["numberReturned"] == N)
            self.assertTrue(len(j["results"]) == N)

    def test_SceneSearchHits(self):
        with API_Context(USGS_USERNAME, USGS_PASSWORD, CATALOG_ID) as context:
            n = context.SceneSearchHits(DATASET_NAME)
            j = context.SceneSearch(DATASET_NAME, max_results=0)
            # could fail if api updates between calls
            self.assertEqual(
                j["totalHits"],
                n,
                "note: if these counts are approximately equal, the server may have updated during test running"
            )

    def test_SceneMetadata(self):
        with API_Context(USGS_USERNAME, USGS_PASSWORD, CATALOG_ID) as context:
            # grab 1 result
            j = context.SceneSearch(DATASET_NAME, max_results=1)
            # unpack
            (product1,) = j['results']
            # fetch SceneMetadata()
            j = context.SceneMetadata(DATASET_NAME, [product1["entityId"]])
            # unpack
            (product2,) = j

            # SceneMetadata has bonus metadataFields
            self.assertTrue(product2.pop('metadataFields'))

            # SceneSearch has extra dataAccess (Jan 2018)
            product2.pop('dataAccess')  # may be None

            # the rest of SceneMetadata should be a subset of SceneSearch
            # assertDictContainsSubset is depreciated :-(
            for k, v in product2.items():
                self.assertEqual(product1[k], v)

    def test_SceneSearch_additional_criteria(self):
        with API_Context(USGS_USERNAME, USGS_PASSWORD, CATALOG_ID) as context:
            # how many landsat scenes?
            total = context.SceneSearchHits(DATASET_NAME)
            # cloud cover
            CLOUD_COVER_FIELD_ID = 10037
            # null = all, "0" = "Less than 10%", "1" = "Less than 20%" ... "9" = "Less than 100%"
            cloud_free = context.SceneSearchHits(
                DATASET_NAME,
                additional_criteria=api.AdditionalCriteria_Value(
                    CLOUD_COVER_FIELD_ID,
                    "=",
                    "0"
                )
            )
            self.assertTrue(total > cloud_free > 0)
