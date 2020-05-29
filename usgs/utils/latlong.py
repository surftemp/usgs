import math
from typing import NamedTuple, Tuple


class LatLong(NamedTuple):
    latitude: float
    longitude: float

    def json(self) -> dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude
        }


def PointToBB(ll: LatLong, dx: float, dy: float) -> Tuple[LatLong, LatLong]:
    """
    LatLong -> bounding box
    
    :param ll: point
    :param dx: length of bounding box in degrees
    :param dy: height of bounding box in degrees
    :returns: (lower_left, upper_right) 
    """
    dx = abs(dx)
    dy = abs(dy)
    x0 = ll.longitude - dx / 2
    x1 = ll.longitude + dx / 2
    y0 = ll.latitude - dy / 2
    y1 = ll.latitude + dy / 2
    # deal with long if range > 360
    if x1 - x0 > 360:
        x0 = 0
        x1 = 360
    # deal with lat outside range [-90, 90]
    if y0 < -90:
        y0 = -90
    if y1 > 90:
        y1 = 90
    return LatLong(y0, x0), LatLong(y1, x1)


def PointToBB_km(ll: LatLong, dx: float, dy: float) -> Tuple[LatLong, LatLong]:
    """
    LatLong -> bounding box

    :param ll: point
    :param dx: length of bounding box in km
    :param dy: height of bounding box in km
    :returns: (lower_left, upper_right) 
    """
    xscale = lon_scale(ll.latitude)
    dx_degrees = dx * 1000 / xscale
    yscale = lat_scale(ll.latitude)
    dy_degrees = dy * 1000 / yscale
    return PointToBB(ll, dx_degrees, dy_degrees)


def lat_scale(lat: float) -> float:
    """
    https://en.wikipedia.org/wiki/Geographic_coordinate_system#Expressing_latitude_and_longitude_as_linear_units
    
    On the WGS84 spheroid, the length in meters of a degree of latitude. units: m / deg
    
    correct to 1cm
    
    :param lat: lattitude in degrees
    """
    _lat = math.radians(lat)
    return 111132.92 - 559.82 * math.cos(2 * _lat) + 1.175 * math.cos(4 * _lat) - 0.0023 * math.cos(6 * _lat)


def lon_scale(lat: float) -> float:
    """
    https://en.wikipedia.org/wiki/Geographic_coordinate_system#Expressing_latitude_and_longitude_as_linear_units

    On the WGS84 spheroid, the length in meters of a degree of longitude. units: m / deg

    correct to 1cm
    
    :param lat: lattitude in degrees
    """
    _lat = math.radians(lat)
    return 111412.84 * math.cos(_lat) - 93.5 * math.cos(3 * _lat) + 0.118 * math.cos(5 * _lat)