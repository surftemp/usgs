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

Installation into a miniforge enviromnent is suggested.  See [https://github.com/conda-forge/miniforge](https://github.com/conda-forge/miniforge) for installing miniforge.

Create a miniforge environment called usgs_env using:

```
mamba create -n usgs_env python=3.11
mamba activate usgs_env
mamba install python-dateutil requests shapely rioxarray
```

Install the usgs tools into this environment:

```
git clone git@github.com:surftemp/usgs.git
cd usgs
pip install .
```

### Updating usgs

Use the following commands to update the usgs tool when the source code in github has changed:

```
conda activate usgs_env
# go to the folder where the usgs source code was cloned
cd path/to/usgs
git pull
pip uninstall usgs
pip install .
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
Landsat OLI/TIRS Collection 2 Level-1 (includes Landsat8/9)| EE | LANDSAT_OT_C2_L1
Landsat OLI/TIRS Collection 2 Level-2 (includes Landsat8/9)| EE | LANDSAT_OT_C2_L2
Landsat 7 ETM Collection 2 Level-1 | EE |  LANDSAT_ETM_C2_L1
Landsat 7 ETM Collection 2 Level-2 | EE |  LANDSAT_ETM_C2_L2
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
These may be supplied as needed with the `--username` and `--token` arguments, 
or for convenience the CLI will pick them up from environment variables.

A third environment variable is available to define the data directory.

Environment Variable | CLI argument | Description
--- |--------------| ---
`USGS_USERNAME` | `--username` | USGS account username
`USGS_TOKEN` | `--token`    | USGS access token
`USGS_DATADIR` | `--data-dir` | Directory to store data

Note: USGS access tokens may be created on your account page: https://ers.cr.usgs.gov/

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
`search-create` | Create a saved search query which may be executed with `search-run`
`search-run` | Execute a search query
`scene-metadata` | Returns scene metadata

*commands not currently converted to use new USGS APIs

Please note that universal arguments (if environment variables are not set)
should be supplied *before* the command.

```
> usgs [--username USERNAME] [--token TOKEN] [--data-dir DATA_DIR] [--debug] COMMAND ...
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
- specify the min/max lat,lon coordinates of the bounding box.  For LANDSAT, an alternative is to specify row and path filters (see dataset specific filters, below)

```
> usgs search-create  LANDSAT_OT_C2_L1 my_search.json --lat-min -20.91 --lon-min 150.83 --lat-max -20.68 --lon-max 151.16 --start-date 2015-01-01 --end-date 2019-01-01 --max-cloud-cover 10
Would you like to set any dataset-specific additional criteria? n
```

The following dataset specific filters are supported:

| option         | description                                                            |
|----------------|------------------------------------------------------------------------|
| `--day-only`   | include only descending/day scenes (LANDSAT_OT_C2_L1 only)             |
| `--night-only` | include only ascending/night scenes (LANDSAT_OT_C2_L1 only)            |
| `--path`       | include scenes from the specified path only (LANDSAT_OT_C2_L1/L2 only) |
|  `--row`       | include scenes from the specified row only (LANDSAT_OT_C2_L1/L2 only)  |

#### 2. Run the saved search query

Find scenes identified by catalog, dataset, id

```
> usgs search-run my_search.json
EE,  LANDSAT_OT_C2_L1, LC80920742019107LGN00
EE,  LANDSAT_OT_C2_L1, LC80920742019171LGN00
EE,  LANDSAT_OT_C2_L1, LC80920742019251LGN00
...
```

You may want to pipe the results to a CSV file for later use with `usgs_download`

```
> usgs search-run my_search.json > scenes.csv
```

To see more detail on search results supply the `--full-details` flag.

To print metadata for a scene use the `scene-metadata` command, passing the dataset and id:

```
> usgs scene-metadata  LANDSAT_OT_C2_L1 LC80920742019107LGN00
{
  "browse": [],
  "cloudCover": null,
  "entityId": "2427002506",
  ...
}
```

#### 3. Download

Use the usgs_download command to download scenes, selecting which files from each scene are relevant.  Each file corresponds to a band or supplies metadata about the scene.

Example usage:

```
usgs_download --filename <scenes.csv> --username <username> --token <token> --output-folder outputs --download-folder downloads --file-suffixes B4.TIF B5.TIF
```

##### Choosing which files/bands to download

The `--file-suffixes` option specifies the suffixes of the files within each scene to download.  

Note - although not included in the above example, you will almost certainly need to include either suffix `.XML` or `.MTL` to download metadata files which will be needed to decode the scene

Consult the dataset's documentation for the filenames and suffixes that map to bands of interest in your selected dataset.

The CSV file passed to the `--filename` option specifies which scenes to download, for example (Landsat 7 Collection 2 Level 1).  Two formats are supported:

Format1 (the output from `usgs search-run`):

```
EE,  LANDSAT_OT_C2_L1, LC80920742019107LGN00
EE,  LANDSAT_OT_C2_L1, LC80920742019171LGN00
EE,  LANDSAT_OT_C2_L1, LC80920742019251LGN00
```

Format2 (legacy):

```
LANDSAT_ETM_C2_L1
LE70090121999183AGS01
LE70100121999190EDC00
LE70080121999240EDC00
LE70100121999254EDC00
LE70090121999263EDC00
LE70832321999269EDC00
LE70090122000074AGS00
LE70100122000081EDC00
```

The first line specifies the dataset id (LANDSAT_ETM_C2_L1) and the remaining lines specify the ids of each scene to download.

Note - each execution of `usgs_download` can only obtain files from a single dataset

##### download and output folders

The `usgs_download` tool can be used to download the files to a separate area (specify the root directory of the cache using the `--download-folder` option), into which files are donwloaded 
using the directory structure described in the following example:

```
<download-folder>/1999
    /07
        /02
            /LE07_L1TP_009012_19990702_20200918_02_T1_B4.TIF
            /LE07_L1TP_009012_19990702_20200918_02_T1_B5.TIF
        /09
            /LE07_L1TP_010012_19990709_20200918_02_T1_B4.TIF
            /LE07_L1TP_010012_19990709_20200918_02_T1_B5.TIF
```

Note - if a file already exists in the download folder, it will not be re-downloaded from USGS.

Symbolic links are created from the download locations into the folder specified using the `--output-folder` option 

##### Download summary files

During operation, the tool will attempt to download all requested files, with retries on failure, and report errors.  A useful option `--download-summary-path` can be used to output a CSV file containing the expected output files

The format of the download summary CSV file is:

```
LC82320182014114LGN01,LC08_L1GT_232018_20140424_20200911_02_T2_B10.TIF
LC82320182014114LGN01,LC08_L1GT_232018_20140424_20200911_02_T2_B11.TIF
LC82320182014114LGN01,LC08_L1GT_232018_20140424_20200911_02_T2_B1.TIF
...
```

After the tool is run, the caller can consult this file and check if any files listed in this CSV file were not actually included in the output

##### Working with a file index

Sometimes, there is already a cache of downloaded files that can be re-used.  These can be utilised instead of re-downloading files from USGS, by consulting a file index

A separate tool `index_files` is used to build the index

```
index_files --scan-folder <folders> --index-path <index-path>
```

where `<folders>` provides one or more folders to search under and `<index-path>` is the path to an index to create or update

Once the index is built, its path can be supplied to the `usgs_download` tool using the `--file-cache-index` option and the tool will check that files do not already exist in this index before downloading them.

##### Other options

| option                    | description                                                                                                      |
|---------------------------|------------------------------------------------------------------------------------------------------------------|
| `--limit`                 | if specified, limit the number of scenes to be downloaded                                                        |
| `--no-download`           | if specified, do not download any files from USGS (the tool will still link already downloaded or indexed files) |
| `--exclude-file-suffixes` | if specified, ignore files with these suffixes |
 | `--verbose`               | log verbose output during downloading |

Note: the --exclude-file-suffixes option is useful to avoid downloading spurious landsat7 "gap mask" files 

```
usgs_download --file-suffixes B4.TIF B5.TIF --exclude-file-suffixes _GM_B4.TIF _GM_B5.TIF ...
```


