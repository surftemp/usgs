# USGS EarthExplorer Library

Fork of IEA developed tool for MSc student projects which need landsat8 scenes
Changes will be worked through and when ready contributed back to the original repo at https://bitbucket.org/the-iea/usgs/src/master/

This project is in aid of phase 1 of the EDF / Met Office / IEA project
to investigate thermal plumes caused by nuclear power plant cooling exhaust
emissions of warm water into neighbouring ocean bodies.

It is a Python package to interface with the United States Geological Survey (USGS)
Earth Resources Observation and Science (EROS) EarthExplorer JSON API. 
This version of the library targets api version 1.4.0 directly.
 
https://earthexplorer.usgs.gov/inventory/documentation/json-api

Primary interest is towards querying and obtaining Landsat 8 and ASTER data.

## Requirements

A USGS / EROS account (ERS account) is required to access the API.
Register for an account @ https://ers.cr.usgs.gov/login/

It is also understood that one should apply for machine-to-machine (M2M) access,
although this is not clearly stated in the API documentation.
M2M allows access to additional api endpoints which are not used by this 
python library.

## Installation

### Git clone (or download) this repository

At the command line `git clone https://github.com/surftemp/usgs.git`

### Anaconda (recommended)

Anaconda is an open source distribution of the Python programming language,
deployed and managed with the conda package management system.

1. Install Anaconda from https://www.continuum.io/downloads
2. Create a Python 3.6 environment including required python packages
    - At the command line: `conda env create -f environment.yml` 
    - Or alternately using the Anaconda Navigator GUI
        1. Select 'Environments' from the left menu bar
        2. Click the 'import' button at the bottom of the list of environments
        3. In the dialog box enter name `usgs`
        4. For the specification file, select the environment.yml file included in this repository
        5. Click 'import'
3. Activate conda environment: `conda activate usgs` on Unix, or `activate usgs` on Windows.  
4. Install this package: `python setup.py install`

Once installed into a conda environment, you need only activate the environment
in a new shell (step #3 above) to access this library.

### Pip

This library may alternately be installed via Pip into an existing python 3.6 environment.

1. Ensure local python >= 3.6
2. Install requirements `pip install -r requirements.txt`
3. Install this package: `python setup.py install`

### Updates

To install a newer version of this library, if you git-cloned the repository 
initially (as above), you can use git to perform the update:
 
```
git pull
python setup.py clean --all
python setup.py install
```

## Scenes

The API identifies a unique product (scene) via its catalog, dataset, and id.

### *catalog*

Users are directed to the EarthExplorer catalog 'EE', 
which is the default throughout this library, 
however other catalogs are available.

Name | Catalog | Web Application
--- | --- | ---
EarthExplorer | EE | http://earthexplorer.usgs.gov
LPCSExplorer | LPCS | http://lpcsexplorer.cr.usgs.gov 
CWIC / LSI Explorer | CWIC | http://lsiexplorer.cr.usgs.gov 
HDDSExplorer | HDDS | https://hddsexplorer.usgs.gov/

### *dataset*

The following dataset is of primary interest

Name | Catalog | Dataset
--- | --- | ---
Landsat 8 OLI/TIRS Collection 1 Level-1 | EE | LANDSAT_8_C1

This library was built with the above dataset targetted. 
The default behaviour may be sufficient for other datasets,
but this is not guaranteed. Other datasets may be supported 
by request.

### *id*

Each product in a dataset has a unique id.

The triple of (catalog, dataset, id) identifies a unique data product (scene). 
Tools are provided to search the API for scenes of interest.

## Data stored locally

This package stores data in a simple hierarchy according to 
scene catalog, dataset, and id: `<data-dir>/catalog/dataset/id/`. 
If the corresponding scene (path) exists on disk, then data are not re-downloaded.

## Command Line Interface

This packages exposes a command line interface (CLI) to interact with the online API. 
Ensure that the conda environment is active with `source activate usgs` on Unix, 
or `activate usgs` on Windows. 
Access the CLI via the `usgs.py` script or the automatically created `usgs` entry point.
All commands are invoked from the base command, and help may be requested
at any point with the `-h` flag.

### Environment variables

Many of the commands which one may execute from the CLI require USGS account credentials. 
These may be supplied as needed with the `--username` and `--password` arguments, 
or for convenience the CLI will pick them up from environment variables.

A third environment variable is available to define the data directory.

Environment Variable | CLI argument | Description
--- | --- | ---
`USGS_USERNAME` | `--username` | USGS account username
`USGS_PASSWORD` | `--password` | USGS account password
`USGS_DATADIR` | `--data-dir` | Directory to store data

One may set environment variables directly in a shell with:

Shell | Command
--- | ---
Bourne (sh and bash) | `export USGS_DATADIR=/datastore`
C (csh or tcsh) | `setenv USGS_DATADIR /datastore`
Windows command prompt | `set USGS_DATADIR=\datastore`

Or to set environment variables permanently edit your shell configuration.
On Unix these are your `.bashrc`, `.login`, `.cshrc`, or other shell
configuration files, usually found in your home directory.
On Windows, open the System Properties dialogue, Advanced tab, and look for
the Environment Variables button.

### Glossary of commands

Commands are invoked at the CLI with `usgs COMMAND ...`.

Command | Description
--- | ---
`status` | Retrieve api server status
`search-create` | Create a saved search query which may be executed with `search-run`
`search-run` | Execute a search query
`download` | Download api scenes
`scene-metadata` | Returns scene metadata
`dataset-search` | Search for datasets by name and spatial / temporal range
`dataset-fields` | Return additional criteria fields for a dataset
`grid2ll` | Convert grid locations to a lat/lng center point or polygon

Please note that universal arguments (if environment variables are not set)
should be supplied *before* the command.

```
> usgs [--username USERNAME] [--password PASSWORD] [--data-dir DATA_DIR] [--debug] COMMAND ...
```

For command-specific help, including descriptions of optional and positional arguments,
type `usgs COMMAND -h`, e.g. `usgs search-create -h`.

### Basic workflow

An example workflow to query and download LANDSAT data is shown below. 
One begins by defining a query on the LANDSAT_8_C1 dataset with the `search-create`
command, which saves the query to a json file. 
Once created, a query may be run by supplying this json file to `search-run`
to identify scenes of interest.
Scenes are finally downloaded with the `download` command. 

#### 1. Create (and save) a search query

- If cloud cover arguments are specified, we check that these are supported by the dataset.
- User is asked if they wish to include dataset-specific additional criteria.
- specify the lat,lon coordinates of the southeast (bottom-left) and northwest (top-right) corners of the bounding box

```
> usgs search-create LANDSAT_8_C1 my_search.json --bb-southeast=-20.91,150.83 --bb-northwest=-20.68,151.16  --start-date 2015-01-01 --max-cloud-cover 10
WARNING: this dataset does not support the min and max cloud cover options. These may be available as additional criteria.
Would you like to set any dataset-specific additional criteria? n
```

##### Notes

* For `--bb-southeast` or `--bb-northwest` in the southern hemisphere you may need to 
single-quote, e.g. `--bb-southeast '-18,140'`, or specify this argument 
with an equals sign `--bb-southeast=-18,140`.

#### 2. Run the saved search query

Find scenes identified by catalog, dataset, id

```
> usgs search-run my_search.json
EE, LANDSAT_8_C1, LC80920742019107LGN00
EE, LANDSAT_8_C1, LC80920742019171LGN00
EE, LANDSAT_8_C1, LC80920742019251LGN00
...
```

To see more detail on search results supply the `--full-details` flag.

#### 3. Download a scene

The `download` command requires either the `USGS_DATADIR` environment variable
or the `--data-dir` command line argument to specify where to save
downloads (`<data-dir>/catalog/dataset/id/`). 

```
> usgs download --scene EE LANDSAT_8_C1 LC80920742019283LGN00
Scene(catalog='EE', dataset='LANDSAT_8_C1', id='LC80920742019283LGN00')
Login
https://earthexplorer.usgs.gov/inventory/json/v/1.4.0/login
https://earthexplorer.usgs.gov/inventory/json/v/1.4.0/metadata
https://earthexplorer.usgs.gov/inventory/json/v/1.4.0/search
INFO:usgs.download.download:Download https://dds.cr.usgs.gov/ltaauth/hsm/lsat1/collection01/oli_tirs/T2/2019/092/074/LC08_L1GT_092074_20191010_20191018_01_T2.tar.gz?id=kc1btlfqf0db111ts6fgenah1k&iid=LC80920742019283LGN00&did=564165789&ver=production
INFO:usgs.download.download:Destination on disk: /var/folders/q2/v1z0vz7s2h31wwc8dyzd06br0000gs/T/LC08_L1GT_092074_20191010_20191018_01_T2.tar.gz
INFO:usgs.download.download:0% (8192/985516916 bytes) @ 0.00 MB/s
...
INFO:usgs.download.download:99% (984932352/985516916 bytes) @ 0.21 MB/s
INFO:usgs.download.download:done
```

##### Piping search to csv

To download multiple scenes it is possible to supply a comma separated values (CSV)
file as input to `download`:

```
> usgs search-run my_search.json > my_results.txt
> usgs download --csv my_results.txt
```

## Restrictions

The API is rate restricted to 1 concurrent request.
Incomplete requests incur a 15 min timeout.

This package has been tested on the LANDSAT_8_C1 dataset. 
