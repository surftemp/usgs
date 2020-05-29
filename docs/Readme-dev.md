# EDF Thermal Plumes project repository

## Existing libraries and apis

### NASA APIs

get a key @ https://api.nasa.gov/index.html#apply-for-an-api-key

* https://api.nasa.gov/api.html#assets
* https://api.nasa.gov/api.html#imagery

Not hugely useful. Data, thumbnail, id, cloud fraction.

### usgs python package

* http://mapbox.github.io/usgs/
* https://github.com/kapadia/usgs

Targets legacy soap api. 

> A JSON API started development after this library was originally written.

Bugs in python 3.x

### landsat-util

* https://developmentseed.org/projects/landsat-util/
* https://github.com/developmentseed/landsat-util

Uses custom api to search
 
Downloads from amazon, google & usgs (see "usgs package")

## USGS (United States Geological Survey) EROS (Earth Resources Observation and Science)

get a login @ https://ers.cr.usgs.gov/login/

usgs json api @ https://earthexplorer.usgs.gov/inventory/documentation/json-api,
also saved in this repo `docs/`.

Technically one needs to apply for machine-to-machine (M2M) access,
although this is not clearly stated. 
Once M2M is granted one has access to many more API endpoints (which I shall generally avoid here).

This API is rate restricted to 1 concurrent request.
Incomplete requests incur a 15 min timeout.

Catalog | Web Application | Node Value
--- | --- | ---
CWIC / LSI Explorer | http://lsiexplorer.cr.usgs.gov | CWIC
EarthExplorer | http://earthexplorer.usgs.gov | EE
HDDSExplorer | http://hddsexplorer.usgs.gov | HDDS
LPCSExplorer | http://lpcsexplorer.cr.usgs.gov | LPCS

***n.b.*** cloud cover not supported for landsat 8 (api v. 1.2.1) - have to use `additionalCriteria`

### Restarting downloads from usgs

Unfortunately the file downloads from the usgs server have header `Accept-Ranges: "none"`
which means that range requests are not supported.

### Changes

#### 21/06/17

Usgs release api versions 1.3.0 and 1.4.0, under a versioned url schema.

url | version
--- | ---
??? | 1.2.1
https://earthexplorer.usgs.gov/inventory/json/v/1.3.0/ | 1.3.0
https://earthexplorer.usgs.gov/inventory/json/v/1.4.0/ | 1.4.0
https://earthexplorer.usgs.gov/inventory/json/v/latest/ | 1.4.0
https://earthexplorer.usgs.gov/inventory/json/ | 1.3.0

Usgs claim that 1.3.0 is functionally identical to 1.2.1, but this is
demonstrably not the case as test fail. 

## Running tests

1. Set variables in tests/settings.py
2. `python -m unittest discover -s tests -p *.py -t .`