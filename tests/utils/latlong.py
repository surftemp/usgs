import unittest
from usgs.utils.latlong import LatLong

import usgs.utils


class Test_LatLong(unittest.TestCase):

    def test_lat(self):
        ll = LatLong(10.0, 20.0)
        self.assertTrue(ll.latitude == 10.0)
        self.assertTrue(ll.longitude == 20.0)

    def test_json(self):
        ll = LatLong(10.0, 20.0)
        self.assertEqual(
            ll.json(),
            {
                "latitude": 10.0,
                "longitude": 20.0
            }
        )


class Test_PointToBB(unittest.TestCase):

    def test_BB(self):
        point = LatLong(10.0, 20.0)
        ll, ur = usgs.utils.latlong.PointToBB(point, 2.0, 4.0)
        self.assertTrue(ll.latitude == 8.0)
        self.assertTrue(ll.longitude == 19.0)
        self.assertTrue(ur.latitude == 12.0)
        self.assertTrue(ur.longitude == 21.0)

    def test_limits(self):
        point = LatLong(80.0, 20.0)
        ll, ur = usgs.utils.latlong.PointToBB(point, 2.0, 30.0)
        self.assertTrue(ll.latitude == 65.0)
        self.assertTrue(ll.longitude == 19.0)
        # ur.lat > 90 should truncate
        self.assertTrue(ur.latitude == 90.0)
        self.assertTrue(ur.longitude == 21.0)


class Test_lon_scale(unittest.TestCase):

    def test_equator(self):
        circumferance_earth = 40075017 # m
        # within 20m isn't bad
        self.assertAlmostEqual(usgs.utils.latlong.lon_scale(0.0) * 360, circumferance_earth, delta=20)

    def test_polar(self):
        self.assertAlmostEqual(usgs.utils.latlong.lon_scale(90.0), 0, delta=1)


class Test_lat_scale(unittest.TestCase):

    def test_equator(self):
        self.assertAlmostEqual(usgs.utils.latlong.lat_scale(0.0), 110574.2727, delta=1)

    def test_45(self):
        self.assertAlmostEqual(usgs.utils.latlong.lat_scale(45.0), 111131.745, delta=1)