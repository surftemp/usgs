"""
Required information about each (catalog, dataset)
"""


# Expected name of product label on api download page
# dict of (catalog, dataset): label
LABEL = {
    ("EE", "LANDSAT_8"): "Level 1 GeoTIFF Data Product",
    ("EE", "ASTER_L1T"): "Standard Product",
    ("EE", "LANDSAT_8_C1"): "Level-1 GeoTIFF Data Product"
}


# Auth required to access data file download
# dict of (catalog, dataset): auth
AUTH = {
    ("EE", "LANDSAT_8"): None,
    ("EE", "ASTER_L1T"): "Earthdata",
    ("EE", "LANDSAT_8_C1"): None
}
