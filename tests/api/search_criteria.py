import datetime
import unittest

from ..settings import USGS_PASSWORD, USGS_USERNAME, CATALOG_ID, DATASET_NAME
from usgs.api.api_context import API_Context
from usgs.api.search_criteria import Search_Criteria
from usgs.utils.latlong import LatLong


class Test_SearchCriteria(unittest.TestCase):
    def test_unpacking(self):
        N = 5
        search_obj = Search_Criteria(
            CATALOG_ID,
            DATASET_NAME,
            max_results=N
        )
        with API_Context(USGS_USERNAME, USGS_PASSWORD, CATALOG_ID) as context:
            # when we unpack Search_Criteria into SceneSearch() we need to
            # throw away 'catalog', which is the first member of the tuple
            j = context.SceneSearch(*search_obj[1:])

            self.assertTrue(j["numberReturned"] == N)
            self.assertTrue(len(j["results"]) == N)

    def test_json_pickle(self):
        search_obj = Search_Criteria(
            CATALOG_ID,
            DATASET_NAME,
            lower_left = LatLong(10, 10),
            upper_right = LatLong(20, 20),
            start_date = datetime.datetime(2015, 5, 20),
            end_date = datetime.datetime(2015, 6, 1, 14, 23, 35)
        )
        self.assertEqual(search_obj, Search_Criteria.from_json(search_obj.json()))
