import datetime

from dateutil.parser import parse

from usgs.utils.latlong import LatLong


def parse_datetime(S: str) -> datetime.datetime:
    return parse(S)


def parse_latlong(S: str, sep: str = ",") -> LatLong:
    lat, long = map(float, S.strip("'").split(sep=sep))
    return LatLong(lat, long)
