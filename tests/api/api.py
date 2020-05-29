import unittest
import datetime
from usgs.api import api
from usgs.utils.latlong import LatLong


class Test_SpatialFilterMBR(unittest.TestCase):
    def test(self):
        self.assertEqual(
            api.SpatialFilterMBR(
                LatLong(10, 10),
                LatLong(20, 20)
            ),
            {
                "filterType": "mbr",
                "lowerLeft": {
                    "latitude": 10,
                    "longitude": 10
                },
                "upperRight": {
                    "latitude": 20,
                    "longitude": 20
                }
            }
        )


class Test_TemporalFilter(unittest.TestCase):
    def test(self):
        self.assertEqual(
            api.TemporalFilter(
                datetime.datetime(2012, 1, 1),
                datetime.datetime(2016, 1, 1)
            ),
            {
                "dateField": "search_date",
                "startDate": "2012-01-01T00:00:00",
                "endDate": "2016-01-01T00:00:00"
            }
        )


class Test_AdditionalCriteria(unittest.TestCase):
    def test_value(self):
        self.assertEqual(
            api.AdditionalCriteria_Value(23632, "=", "test me"),
            {
                "filterType": "value",
                "fieldId": 23632,
                "operand": "=",
                "value": "test me"
            }
        )

    def test_value_operator_exception(self):
        with self.assertRaises(ValueError):
            api.AdditionalCriteria_Value(23632, "bad operator", "test me")

    def test_between(self):
        self.assertEqual(
            api.AdditionalCriteria_Between(23632, "1", "2"),
            {
                "filterType": "between",
                "fieldId": 23632,
                "firstValue": "1",
                "secondValue": "2"
            }
        )

    def test_and(self):
        cond = api.AdditionalCriteria_And(
            [
                api.AdditionalCriteria_Value(23632, "=", "test me"),
                api.AdditionalCriteria_Value(91298, "like", "some string")
            ]
        )
        d = {
                "filterType": "and",
                "childFilters": [
                    {"filterType": "value", "fieldId": 23632, "operand": "=", "value": "test me"},
                    {"filterType": "value", "fieldId": 91298, "operand": "like", "value": "some string"}
                ]
        }
        self.assertEqual(cond, d)

    def test_or(self):
        cond = api.AdditionalCriteria_Or(
            [
                api.AdditionalCriteria_Value(23632, "=", "test me"),
                api.AdditionalCriteria_Value(91298, "like", "some string")
            ]
        )
        d = {
            "filterType": "or",
            "childFilters": [
                {"filterType": "value", "fieldId": 23632, "operand": "=", "value": "test me"},
                {"filterType": "value", "fieldId": 91298, "operand": "like", "value": "some string"}
            ]
        }
        self.assertEqual(cond, d)
