"""
Functions to interact with the USGS (United States Geological Survey) EROS (Earth Resources Observation and Science) JSON API
@ https://earthexplorer.usgs.gov/inventory/json/

https://earthexplorer.usgs.gov/inventory/documentation/json-api
"""

import abc
import json
from typing import Callable, List
from urllib.parse import urljoin
import datetime

import requests
import jsonschema

from .url_settings import URL, API_VERSION
from .util import staticjson
from ..utils.latlong import LatLong


def JSON_Request(endpoint: str, api_params: dict = None, data_params: dict = None, requests_fn: Callable = requests.get) -> dict:
    """
    executes request against earth explorer json api
    """
    # url = .../json/endpoint?jsonRequest=<json>
    params = {"jsonRequest": json.dumps(api_params)} if api_params else None
    data_params = {"jsonRequest": json.dumps(data_params)} if data_params else None
    url = urljoin(URL, endpoint)
    r = requests_fn(url, params=params, data=data_params)
    r.raise_for_status()
    j = r.json()
    _Check_JSON(j)
    return j


class API_Exception(Exception):
    def __init__(self, message: str = None, json: dict = None):
        self.message = message
        self.json = json

    def __str__(self):
        S = self.message if self.message else ""
        if self.json:
            if S:
                S += "\n"
            S += json.dumps(self.json)
        return S


class NotAuthorisedException(API_Exception):
    pass


def _Check_JSON(json: dict):
    """
    sanity check returned json
    """
    if not isinstance(json, dict):
        raise API_Exception("Expected json object, got " + str(type(json)))
    try:
        # json-schema
        schema = staticjson(
            API_VERSION,
            "GenericResponse.schema.json"
        )
        # catch ValidationError below
        # jsonschema.validate(json, schema)

        # Auth
        if json["errorCode"] == 'AUTH_INVALID' or json["error"] == 'Authentication Failed':
            raise NotAuthorisedException(json=json)
        # error reported in JSON
        elif json["errorCode"] or json["error"]:
            raise API_Exception(
                "{}: {}".format(json["errorCode"], json["error"]),
                json
            )

        # no data
        if not json["data"]:
            raise API_Exception("No data", json)

    except jsonschema.ValidationError as e:
        raise API_Exception(
            "API returned improper response",
            json
        ) from e

    except KeyError as e:
        raise API_Exception("KeyError in json", json) from e


class API_Nested_Object_Base(dict, abc.ABC):
    """
    Base class to encode USGS EROS JSON API nested fields.
    
    see: https://earthexplorer.api.gov/inventory/documentation/datamodel
    """

    def json(self) -> dict:
        return self


class SpatialFilterMBR(API_Nested_Object_Base):
    """
    minimum bounding rectangle

    https://earthexplorer.usgs.gov/inventory/documentation/datamodel#SpatialFilterMbr
    """

    def __init__(self, ll: LatLong, ur: LatLong):
        super().__init__()
        self.update({
            "filterType": "mbr",
            "lowerLeft": ll.json(),
            "upperRight": ur.json()
        })


class TemporalFilter(API_Nested_Object_Base):
    """
    https://earthexplorer.usgs.gov/inventory/documentation/datamodel#TemporalFilter
    """

    def __init__(
        self,
        start: datetime.datetime = None,
        end: datetime.datetime= None
    ):
        super().__init__()
        self.update({
            "dateField": "search_date",
            "startDate": start.isoformat() if start else None,
            "endDate": end.isoformat() if end else None
        })


class AdditionalCriteria_Value(API_Nested_Object_Base):
    """
    Class to encode additionalCriteria SearchFilterValue for USGS EROS JSON API

    see: https://earthexplorer.api.gov/inventory/documentation/datamodel#Service_Inventory_SearchFilter
    """

    def __init__(self, field_id: int, operand: str, value: str):
        """
        Encodes additionalCriteria SearchFilterValue for USGS EROS JSON API

        :param operand: "=" or "like"
        """
        super().__init__()
        if operand not in ("=", "like"):
            raise ValueError("invalid operand {}".format(operand))
        self.update(
            {
                "filterType": "value",
                "fieldId": field_id,
                "operand": operand,
                "value": value
            }
        )


class AdditionalCriteria_Between(API_Nested_Object_Base):
    """
    Class to encode additionalCriteria SearchFilterBetween for USGS EROS JSON API

    see: https://earthexplorer.api.gov/inventory/documentation/datamodel#Service_Inventory_SearchFilter
    """

    def __init__(self, field_id: int, first_value: str, second_value: str):
        """
        Encodes additionalCriteria SearchFilterBetween for USGS EROS JSON API
        """
        super().__init__()
        self.update(
            {
                "filterType": "between",
                "fieldId": field_id,
                "firstValue": first_value,
                "secondValue": second_value
            }
        )


class AdditionalCriteria_And(API_Nested_Object_Base):
    """
    Class to encode additionalCriteria SearchFilterAnd for USGS EROS JSON API

    see: https://earthexplorer.api.gov/inventory/documentation/datamodel#Service_Inventory_SearchFilter
    """

    def __init__(self, child_filters: List[API_Nested_Object_Base]):
        """
        Encodes additionalCriteria SearchFilterAnd for USGS EROS JSON API
        """
        super().__init__()
        self.update(
            {
                "filterType": "and",
                "childFilters": [x.json() for x in child_filters]
            }
        )


class AdditionalCriteria_Or(API_Nested_Object_Base):
    """
   Class to encode additionalCriteria SearchFilterOr for USGS EROS JSON API

   see: https://earthexplorer.api.gov/inventory/documentation/datamodel#Service_Inventory_SearchFilter
   """

    def __init__(self, child_filters: List[API_Nested_Object_Base]):
        """
        Encodes additionalCriteria SearchFilterOr for USGS EROS JSON API
        """
        super().__init__()
        self.update(
            {
                "filterType": "or",
                "childFilters": [x.json() for x in child_filters]
            }
        )
