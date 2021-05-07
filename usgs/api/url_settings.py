VERSIONED_URLS = {
    "root": "https://earthexplorer.usgs.gov/inventory/json/",
    "1.2.1": None,
    "1.3.0": "https://earthexplorer.usgs.gov/inventory/json/v/1.3.0/",
    "1.4.0": "https://earthexplorer.usgs.gov/inventory/json/v/1.4.0/",
    "1.5.0": "https://m2m.cr.usgs.gov/api/api/json/stable/",
    "latest": "https://earthexplorer.usgs.gov/inventory/json/v/latest/"
}

# This version of the library points directly at 1.4.0
API_VERSION = "1.5.0"
URL = VERSIONED_URLS[API_VERSION]
