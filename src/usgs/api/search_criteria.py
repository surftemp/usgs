import datetime
from typing import NamedTuple, List
import dateutil.parser

from ..utils.latlong import LatLong


class Search_Criteria(NamedTuple):
    """
    Container which holds all arguments required for a SceneSearch request against the USGS EROS JSON API 
    """
    catalog: str
    dataset_name: str
    lower_left: LatLong = None
    upper_right: LatLong = None
    start_date: datetime.datetime = None
    end_date: datetime.datetime = None
    months: List[int] = None
    include_unknown_cloud_cover: bool = True
    min_cloud_cover: int = 0
    max_cloud_cover: int = 100
    additional_criteria: dict = None
    max_results: int = 10
    starting_number: int = 1
    sort_order: str = "ASC"
    day_not_night: bool = None
    row: int = ""
    path: int = ""

    def json(self) -> dict:
        D = self._asdict()

        # note: default behaviour here is LatLong <NamedTuple> -> list
        # override this to preserve json
        D['lower_left'] = self.lower_left.json() if self.lower_left else None
        D['upper_right'] = self.upper_right.json() if self.upper_right else None

        # dates to strings as no dates in json
        try:
            D["start_date"] = D["start_date"].isoformat()
        except AttributeError:
            pass
        try:
            D["end_date"] = D["end_date"].isoformat()
        except AttributeError:
            pass
        return D

    @staticmethod
    def from_json(J: dict) -> 'Search_Criteria':
        # deal with coords -> LatLong
        lower_left: dict = J["lower_left"]
        if lower_left:
            lower_left = LatLong(**lower_left)
        upper_right: dict = J["upper_right"]
        if upper_right:
            upper_right = LatLong(**upper_right)
        # deal with dates
        start_date = dateutil.parser.parse(J["start_date"]) if J["start_date"] else None
        end_date = dateutil.parser.parse(J["end_date"]) if J["end_date"] else None

        return Search_Criteria(
            J['catalog'],
            J["dataset_name"],
            lower_left = lower_left,
            upper_right = upper_right,
            start_date = start_date,
            end_date = end_date,
            months = J["months"],
            include_unknown_cloud_cover = J["include_unknown_cloud_cover"],
            min_cloud_cover = J["min_cloud_cover"],
            max_cloud_cover = J["max_cloud_cover"],
            additional_criteria = J["additional_criteria"],
            max_results = J["max_results"],
            starting_number = J["starting_number"],
            sort_order = J["sort_order"],
            day_not_night = J.get("day_not_night",None),
            row = J.get("row",None),
            path = J.get("path",None)
        )
