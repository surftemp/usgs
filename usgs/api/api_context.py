import datetime
from functools import wraps
from typing import List

import requests

from . import api
from .catalogs import Catalogs
from ..utils.latlong import LatLong
import json

# derived from https://m2m.cr.usgs.gov/api/test/json/ API dataset-filters
metadata_filter_ids = {
    "LANDSAT_OT_C2_L2": {
        "row": "5e83d14ff1eda1b8",
        "path": "5e83d14fb9436d88"
    },
    "LANDSAT_OT_C2_L1": {
        "day_not_night": "5e81f14f61bda7c4",
        "row": "5e81f14f8d2a7c24",
        "path": "5e81f14f8faf8048"
    }
}

def _login(fn):
    """
    wrapper marking functions which require login / api key on API_Context.
    handles api timeout.
    """
    def wrapped(self: 'API_Context', *args, **kwargs):
        wraps(fn)
        if datetime.datetime.now() - self._login_time > API_Context.LOGIN_VALIDITY:
            self.__enter__()
        return fn(self, *args, **kwargs)
    return wrapped


class API_Context:
    """
    Context manager for USGS (United States Geological Survey) EROS (Earth Resources Observation and Science) JSON API
    @ https://earthexplorer.api.gov/inventory/json/

    API documentation: https://earthexplorer.api.gov/inventory/documentation/json-api
    
    Static methods map to api calls which do not require a login / api key.
    For auth use as context manager:
    
    $ with API_Context(username, password, catalog_id) as context:
        context.SceneSearch(...)
    """

    LOGIN_VALIDITY = datetime.timedelta(hours=1)

    def __init__(self, username: str, password: str, catalog_id: str):
        """
        :param catalog_id: which dataset catalog to access (previously 'node' in api version 1.2.1)
        """
        self.username = username
        self.password = password
        if catalog_id not in [cat.value for cat in Catalogs]:
            raise ValueError("catalog_id should be one of {}".format(list(Catalogs)))
        self.catalog_id = catalog_id
        self.api_key = None
        self._login_time = None

    def __enter__(self):
        self._login_time = datetime.datetime.now()
        self.api_key = API_Context.Login(self.username, self.password, self.catalog_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        API_Context.Logout(self.api_key)
        self.api_key = None
        self._login_time = None

    @staticmethod
    def Status() -> dict:
        j = api.JSON_Request("status")
        return j

    @staticmethod
    def GridToLatLong(grid_type: str, response_shape: str, path: int, row: int, api_key=None) -> dict:
        """
        convert WRS-1 and WRS-2 grid systems to lat/lng center point or polygon

        :param grid_type: WRS1 or WRS2
        :param response_shape: point or polygon

        :returns: data member of json response, which should contain either
            a point or a polygon
        """
        if grid_type not in ('WRS1', 'WRS2'):
            raise ValueError("grid_type must be WRS1 or WRS2")
        if response_shape not in ('point', 'polygon'):
            raise ValueError("response_shape must be point or polygon")

        j = api.JSON_Request(
            "grid2ll",
            data_params={
                "gridType": grid_type,
                "responseShape": response_shape,
                "path": path,
                "row": row
            },
            headers = {
                "X-Auth-Token":api_key
            }
        )
        return j["data"]

    @staticmethod
    def Login(username: str, password: str, catalog_id: str) -> str:
        """
        :param catalog_id: which dataset catalog to use (previously 'node'
            in api version 1.2.1)

        :return: api key. required by other api calls. valid for 1 hour.
        """

        if catalog_id not in [cat.value for cat in Catalogs]:
            raise ValueError("catalog_id should be one of {}".format(list(Catalogs)))

        # optional field:
        # "authType": "EROS"

        j = api.JSON_Request(
            "login",
            data_params={
                "username": username,
                "password": password
            },
            requests_fn=requests.post
        )

        return j["data"]

    @staticmethod
    def Logout(api_key: str) -> bool:
        """
        :return: success
        """
        j = api.JSON_Request(
            "logout",
            headers={"X-Auth-Token": api_key}
        )

    @_login
    def DatasetSearch(
            self,
            dataset_name_pattern: str = None,
            lower_left: LatLong = None,
            upper_right: LatLong = None,
            start_date: datetime.datetime = None,
            end_date: datetime.datetime = None
    ) -> List[dict]:
        """
        discover available datasets
        """
        params = {
            "apiKey": self.api_key
        }
        if dataset_name_pattern:
            params["datasetName"] = dataset_name_pattern
        if lower_left and upper_right:
            params["spatialFilter"] = api.SpatialFilterMBR(
                lower_left,
                upper_right
            ).json()
        if start_date or end_date:
            params["temporalFilter"] = api.TemporalFilter(
                start_date,
                end_date
            )

        j = api.JSON_Request("datasets", params)

        return j["data"]

    @_login
    def DatasetFields(self, dataset_name: str) -> List[dict]:
        """
        This request is used to return the metadata filter fields for the specified dataset.
        These values can be used as additional criteria when submitting search and hit queries.
        """
        j = api.JSON_Request(
            "datasetfields",
            {
                "datasetName": dataset_name,
                "apiKey": self.api_key
            }
        )

        return j["data"]

    @_login
    def DownloadOptions(self, dataset_name: str, scene_id: str) -> str:
        """
        This request is used to return the download options for a specified scene within a specified dataset.
        """
        j = api.JSON_Request(
            "download-options",
            data_params={
                "datasetName": dataset_name,
                "entityIds": scene_id
            },
            headers={"X-Auth-Token": self.api_key, 'User-Agent': 'USGS Client Tool 1.0'}
        )

        return j["data"]

    @_login
    def DownloadRequest(self, label: str, downloads: list) -> str:
        """
        This request is used to request downloads.
        """
        j = api.JSON_Request(
            "download-request",
            data_params={
                "label": label,
                "downloads": downloads
            },
            headers={"X-Auth-Token": self.api_key, 'User-Agent': 'USGS Client Tool 1.0'}
        )

        return j["data"]

    @_login
    def DownloadRetrieve(self, label: str) -> str:
        """
        This request is used to retrieve the status of a download.
        """
        j = api.JSON_Request(
            "download-retrieve",
            data_params={
                "label": label,
            },
            headers={"X-Auth-Token": self.api_key, 'User-Agent': 'USGS Client Tool 1.0'}
        )

        print(json.dumps(j))

        return j["data"]


    @_login
    def SceneSearch(
            self,
            dataset_name: str,
            lower_left: LatLong = None,
            upper_right: LatLong = None,
            start_date: datetime.datetime = None,
            end_date: datetime.datetime = None,
            months: List[int] = None,
            include_unknown_cloud_cover: bool = True,
            min_cloud_cover: int = 0,
            max_cloud_cover: int = 100,
            additional_criteria: dict = None,
            max_results: int = 10,
            starting_number: int = 1,
            sort_order: str = "ASC",
            day_not_night: bool = None,
            row: int = None,
            path: int = None,
            check_encloses: bool = False,
            check_using: str = "metadata"
    ) -> dict:
        """
        Data product search.

        :param dataset_name: Identifies the dataset
        :param lower_left: spatial bounding box
        :param upper_right: spatial bounding box
        :param start_date: temporal bound
        :param end_date: temporal bound
        :param months: Used to limit results to specific months. e.g. [1,2,3]
        :param include_unknown_cloud_cover: Used to determine if scenes with unknown cloud cover values should be included in the results
        :param min_cloud_cover: Valid values are [0, 100]
        :param max_cloud_cover: Valid values are [0, 100]
        :param additional_criteria: Used to filter results based on dataset specific metadata fields. See DatasetFields().
        :param max_results: max 50,000
        :param starting_number: pagination
        :param sort_order: ASC or DESC
        :param day_not_night: set to True for collecting daytime only, set to False for collecting night time only
        :param row: filter by the row number
        :param path: filter by the path number
        :param check_encloses: True iff extra checks should be performed that the image encloses the bounding box
        :param check_using: metadata or wrs2 - how to check that scenes include all/most of the bounding box
        """
        if not 0 <= max_results <= 50000:
            raise ValueError("0 <= max_results <= 50000")
        if sort_order not in ('ASC', 'DESC'):
            raise ValueError("sort_order must be ASC or DESC")
        params = {
            "datasetName": dataset_name,
            "sceneFilter": {},
            "maxResults": max_results,
            "startingNumber": starting_number,
            "sortDirection": sort_order
        }

        if min_cloud_cover > 0 or max_cloud_cover < 100:
            params["sceneFilter"]["cloudCoverFilter"] = {
                "includeUnknown": include_unknown_cloud_cover,
                "min": min_cloud_cover,
                "max": max_cloud_cover
            }

        if lower_left and upper_right:
            params["sceneFilter"]["spatialFilter"] = api.SpatialFilterMBR(
                lower_left,
                upper_right
            ).json()
        if start_date or end_date:
            if end_date:
                # extend the end-date by 1 day, as the API seems to check for scenes acquired before the end date
                end_date = (end_date+datetime.timedelta(days=1))
            params["sceneFilter"]["acquisitionFilter"] = api.TemporalFilter(
                start_date,
                end_date
            )
        if months:
            params["sceneFilter"]["seasonalFilter"] = months
        if additional_criteria:
            params["additionalCriteria"] = additional_criteria

        metadata_filters = []
        if day_not_night is not None:
            filter_id = metadata_filters.get(dataset_name,{}).get("day_or_night","")
            if filter_id:
                metadata_filters.append({
                    "filterId": filter_id,
                    "filterType": "value",
                    "value": "DAY" if day_not_night else "NIGHT",
                    "operand": "="
                })
            else:
                print(f"Warning: DAY/NIGHT selection not supported for dataset {dataset_name}")

        if row is not None:
            filter_id = metadata_filters.get(dataset_name,{}).get("row","")
            if filter_id:
                metadata_filters.append({
                    {
                        "filterId": filter_id,
                        "filterType": "between",
                        "firstValue": row,
                        "secondValue": row
                    },
                })

        if path is not None:
            filter_id = metadata_filters.get(dataset_name,{}).get("path","")
            if filter_id:
                metadata_filters.append({
                    {
                        "filterId": filter_id,
                        "filterType": "between",
                        "firstValue": path,
                        "secondValue": path
                    },
                })

        if len(metadata_filters) == 1:
            params["sceneFilter"]["metadataFilter"] = metadata_filters[0]
        elif len(metadata_filters) > 1:
            params["sceneFilter"]["metadataFilter"] = {
                "filterType": "and",
                "childFilters": metadata_filters
            }

        j = api.JSON_Request("scene-search", data_params=params, headers={"X-Auth-Token":self.api_key, 'User-Agent': 'USGS Client Tool 1.0'})

        if check_encloses:

            from shapely.geometry import Point, Polygon
            results = j["data"]["results"]
            filtered_results = []

            lat_min = lower_left.latitude
            lon_min = lower_left.longitude
            lat_max = upper_right.latitude
            lon_max = upper_right.longitude
            box_points = [Point(lon, lat) for lat in [lat_min, lat_max] for lon in [lon_min, lon_max]]

            footprints = {} # mapping from (path,row) to WRS2 footprint [{"latitude":...,"longitude":...},...,...]
            for result in results:
                entityId = result["entityId"]

                if check_using == "wrs2":
                    points_target = 3 # look for at least 3/4 corners in the wrs2 footprint
                    path = int(entityId[3:6])
                    row = int(entityId[6:9])
                    if (path,row) not in footprints:
                        footprint = API_Context.GridToLatLong("WRS2","polygon",path,row,self.api_key)["coordinates"]
                        footprints[(path,row)] = footprint
                    else:
                        footprint = footprints[(path,row)]
                    image_polygon = Polygon([[p["longitude"],p["latitude"]] for p in footprint])

                else:
                    points_target = 4 # look for all 4 corners in the metadata footprint
                    image_polygon = Polygon([[coords[0],coords[1]] for coords in result["spatialFootprint"]["coordinates"][0]])
                points = 0
                for point in box_points:
                    if image_polygon.contains(point):
                        points += 1
                if points >= points_target:
                    filtered_results.append(result)

            j["data"]["results"] = filtered_results

        return j["data"]

    @_login
    def SceneSearchHits(
            self,
            dataset_name: str,
            lower_left: LatLong = None,
            upper_right: LatLong = None,
            start_date: datetime.datetime = None,
            end_date: datetime.datetime = None,
            months: List[int] = None,
            include_unknown_cloud_cover: bool = True,
            min_cloud_cover: int = 0,
            max_cloud_cover: int = 100,
            additional_criteria: dict = None
    ) -> int:
        """
        Determine the number of hits that a search will return

        :param dataset_name: Identifies the dataset
        :param lower_left: spatial bounding box
        :param upper_right: spatial bounding box
        :param start_date: temporal bound
        :param end_date: temporal bound
        :param months: Used to limit results to specific months. e.g. [1,2,3]
        :param include_unknown_cloud_cover: Used to determine if scenes with unknown cloud cover values should be included in the results
        :param min_cloud_cover: Valid values are [0, 100]
        :param max_cloud_cover: Valid values are [0, 100]
        :param additional_criteria: Used to filter results based on dataset specific metadata fields. See DatasetFields().
        """
        params = {
            "datasetName": dataset_name,
            "apiKey": self.api_key,
            "includeUnknownCloudCover": include_unknown_cloud_cover,
            "minCloudCover": min_cloud_cover,
            "maxCloudCover": max_cloud_cover
        }
        if lower_left and upper_right:
            params["spatialFilter"] = api.SpatialFilterMBR(
                lower_left,
                upper_right
            ).json()
        if start_date or end_date:
            params["temporalFilter"] = api.TemporalFilter(
                start_date,
                end_date
            )
        if months:
            params["months"] = months
        if additional_criteria:
            params["additionalCriteria"] = additional_criteria
        j = api.JSON_Request("hits", params)

        return j["data"]

    @_login
    def SceneMetadata(self, dataset_name: str, entity_id: str) -> List[dict]:
        """
        returns the same metadata that is available via the search request.
        """
        j = api.JSON_Request(
            "scene-metadata",
            data_params={
                "datasetName": dataset_name,
                "entityId": entity_id
            },
            headers={"X-Auth-Token":self.api_key}
        )

        return j["data"]
