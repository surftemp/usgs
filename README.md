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

You should also apply for MACHINE / M2M access for downloads of scenes other than landsat8.  
Apply for this access via https://ers.cr.usgs.gov/profile/access

Some datasets (eg ECOSTRESS) may also require an account on https://urs.earthdata.nasa.gov/profile - it appears that both this account and the ERS account need the same credentials (username and password need to match).

## Installation

### Git clone (or download) this repository

At the command line `git clone https://github.com/surftemp/usgs.git`

and change into the directory usgs

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
3. Activate conda environment: `conda activate usgs_env` on Unix, or `activate usgs_env` on Windows.  
4. Install this package: `python setup.py install`

Once installed into a conda environment, you need only activate the environment
in a new shell (step #3 above) to access this library.

### Pip

This library may alternately be installed via Pip into an existing python 3.6 environment.

1. Ensure local python >= 3.6
2. Create environment: `python3 -m venv ~/usgs_env`
3. Activate environment: `. ~/usgs_env/bin/activate`   
4. Install requirements `pip install -r requirements.txt`
5. Install this package: `python setup.py install`

### Updates

To install a newer version of this library, if you git-cloned the repository 
initially (as above), you can use git to perform the update:

### Updating usgs

Use the following commands to update the usgs tool when the source code in github has changed:

```
conda activate usgs_env OR . ~/usgs_env/bin/activate
git pull
pip uninstall usgs
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

The following datasets are of primary interest or have been tested with usgs

Name | Catalog | Dataset
--- | --- | ---
Landsat 8 OLI/TIRS Collection 1 Level-1 | EE | LANDSAT_8_C1
Landsat OLI/TIRS Collection 1 Level-1 (includes Landsat8/9)| EE | LANDSAT_OT_C2_L1
Landsat OLI/TIRS Collection 1 Level-2 (includes Landsat8/9)| EE | LANDSAT_OT_C2_L2
Ecostress        | EE | ECOSTRESS_ECO1BRAD

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
~~status~~* | ~~Retrieve api server status~~
`search-create` | Create a saved search query which may be executed with `search-run`
`search-run` | Execute a search query
`download` | Download api scenes
`scene-metadata` | Returns scene metadata
~~dataset-search~~* | ~~Search for datasets by name and spatial / temporal range~~
~~dataset-fields~~* | ~~Return additional criteria fields for a dataset~~
~~grid2ll~~* | ~~Convert grid locations to a lat/lng center point or polygon~~

*commands not currently converted to use new USGS APIs

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
- specify the min/max lat,lon coordinates of the bounding box

```
> usgs search-create LANDSAT_8_C1 my_search.json --lat-min -20.91 --lon-min 150.83 --lat-max -20.68 --lon-max 151.16  --start-date 2015-01-01 --end-date 2019-01-01 --max-cloud-cover 10
WARNING: this dataset does not support the min and max cloud cover options. These may be available as additional criteria.
Would you like to set any dataset-specific additional criteria? n
```

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

To print metadata for a scene use the `scene-metadata` command, passing the dataset and id:

```
> usgs scene-metadata LANDSAT_8_C1 LC80920742019107LGN00
{
  "browse": [],
  "cloudCover": null,
  "entityId": "2427002506",
  ...
}
```

#### 3. Download a scene

The `download` command requires either the `USGS_DATADIR` environment variable
or the `--data-dir` command line argument to specify where to save
downloads (`<data-dir>/catalog/dataset/id/`).

```
> usgs download --scene EE LANDSAT_8_C1 LC80920742019283LGN00
Scene(catalog='EE', dataset='LANDSAT_8_C1', id='LC80920742019251LGN00')
INFO:usgs.download.gcp:Downloading: LC08_L1TP_092074_20190908_20190917_01_T1_B1.TIF
INFO:usgs.download.gcp:Downloading: LC08_L1TP_092074_20190908_20190917_01_T1_B2.TIF
INFO:usgs.download.gcp:Downloading: LC08_L1TP_092074_20190908_20190917_01_T1_B3.TIF
INFO:usgs.download.gcp:Downloading: LC08_L1TP_092074_20190908_20190917_01_T1_B4.TIF
INFO:usgs.download.gcp:Downloading: LC08_L1TP_092074_20190908_20190917_01_T1_B5.TIF
INFO:usgs.download.gcp:Downloading: LC08_L1TP_092074_20190908_20190917_01_T1_B6.TIF
INFO:usgs.download.gcp:Downloading: LC08_L1TP_092074_20190908_20190917_01_T1_B7.TIF
INFO:usgs.download.gcp:Downloading: LC08_L1TP_092074_20190908_20190917_01_T1_B8.TIF
INFO:usgs.download.gcp:Downloading: LC08_L1TP_092074_20190908_20190917_01_T1_B9.TIF
INFO:usgs.download.gcp:Downloading: LC08_L1TP_092074_20190908_20190917_01_T1_B10.TIF
INFO:usgs.download.gcp:Downloading: LC08_L1TP_092074_20190908_20190917_01_T1_B11.TIF
INFO:usgs.download.gcp:Downloading: LC08_L1TP_092074_20190908_20190917_01_T1_BQA.TIF
INFO:usgs.download.gcp:Downloading: LC08_L1TP_092074_20190908_20190917_01_T1_MTL.txt
Saved to /tmp/EE/LANDSAT_8_C1/LC80920742019251LGN00
```

The download option will not attempt to download a scene that has been previously downloaded to the data directory.  

Use the `--ignore-cache` option to override the cached entry and always re-download the files.

Depending on the dataset, a scene may comprise multiple files.  For example a large .h5 file and a small .xml file containing metadata.

In this case, to download just the metadata file, use the `--suffix-filter` option to select only .xml files as follows:

```
> usgs download --scene EE ECOSTRESS_ECO1BRAD 2492617597 --suffix-filter xml --ignore-cache
INFO:usgs.download.download_usgs:Skipping: ECOSTRESS_L1B_RAD_18397_033_20211003T222511_0601_01.h5 with no match to filter-suffix xml
INFO:usgs.download.download:Download https://e4ftl01.cr.usgs.gov/ECOA/ECOSTRESS/ECO1BRAD.001/2021.10.03/ECOSTRESS_L1B_RAD_18397_033_20211003T222511_0601_01.h5.xml
INFO:usgs.download.download:Destination on disk: /var/folders/5k/mnb_s_l11fv6n9kl8dstbf7r0000gp/T/tmp3y9kyi_1/EE/ECOSTRESS_ECO1BRAD/2492617597/ECOSTRESS_L1B_RAD_18397_033_20211003T222511_0601_01.h5.xml
INFO:usgs.download.download:239% (8192/3424 bytes) @ 3.53 MB/s
INFO:usgs.download.download:done
```

Landsat8 Level1 data will be downloaded from Google Cloud.  Other datasets will be downloaded from the USGS site, which may require "Machine" access.  You can request this access by logging in to https://ers.cr.usgs.gov/profile/access

![image](https://user-images.githubusercontent.com/58978249/152136005-5d8ca56e-4d6d-405e-9cb9-430428b1227d.png)


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

