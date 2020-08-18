import logging
import os
import sys
from argparse import ArgumentParser

from usgs.api.catalogs import Catalogs
from usgs.cli.util import parse_datetime, parse_latlong
from . import cli_commands


def __main__(args=None):
    """
    Command line interface entry point

    :param args: Defaults to sys.argv if not specified
    """

    parser = ArgumentParser(description="Command line interface to api data")
    parser.add_argument(
        "--username",
        help="api eros account username. overrides the USGS_USERNAME environment variable",
        default=os.environ.get("USGS_USERNAME")
    )
    parser.add_argument(
        "--password",
        help="api eros account password. overrides the USGS_PASSWORD environment variable",
        default=os.environ.get("USGS_PASSWORD")
    )
    parser.add_argument(
        "--data-dir",
        help="root folder of data directory. overrides the USGS_DATADIR environment variable",
        default=os.environ.get("USGS_DATADIR")
    )
    parser.add_argument(
        "--debug",
        action='store_true',
        help="show debug messages"
    )

    # subparsers for each command
    command_subparsers = parser.add_subparsers()

    # Status
    parser_Status: ArgumentParser = command_subparsers.add_parser(
        "status",
        description="Retrieve api server status"
    )
    parser_Status.set_defaults(func=cli_commands.Status)

    # Search Create
    parser_Search_Create: ArgumentParser = command_subparsers.add_parser(
        "search-create",
        description="Create a saved search query which may be executed with "
                    "the \'search-run\' command"
    )
    parser_Search_Create.add_argument(
        "--catalog",
        help="choice of catalog. (previously 'node')",
        choices=[cat.value for cat in Catalogs],
        default=Catalogs.EarthExplorer.value
    )
    parser_Search_Create.add_argument("dataset")
    parser_Search_Create.add_argument(
        "--bb-centre",
        help="centre of bounding box. format: \'lat,long\'",
        type=parse_latlong
    )
    parser_Search_Create.add_argument(
        "--bb-length",
        help="size of bounding box in km",
        type=float
    )
    parser_Search_Create.add_argument(
        "--lat-min",
        help="minimum latitude of bounding box",
        type=float
    )
    parser_Search_Create.add_argument(
        "--lat-max",
        help="maximum latitude of bounding box",
        type=float
    )
    parser_Search_Create.add_argument(
        "--lon-min",
        help="minimum longitude of bounding box",
        type=float
    )
    parser_Search_Create.add_argument(
        "--lon-max",
        help="maximum longitude of bounding box",
        type=float
    )

    parser_Search_Create.add_argument(
        "--noninteractive",
        help="run without promting user",
        action='store_true'
    )

    parser_Search_Create.add_argument(
        "--start-date",
        help="earliest date, e.g. \'2012-05-29\'",
        type=parse_datetime
    )
    parser_Search_Create.add_argument(
        "--end-date",
        help="latest date, e.g. \'2017-12-31\'",
        type=parse_datetime
    )
    parser_Search_Create.add_argument(
        "--months",
        help="include only specified months, e.g. \'1, 2, 3\'",
        nargs="+",
        type=int
    )
    parser_Search_Create.add_argument(
        "--exclude-unknown-cloud-cover",
        help="exclunde scenes from search where cloud cover is unknown",
        action='store_true'
    )
    parser_Search_Create.add_argument(
        "--min-cloud-cover",
        help="minimum cloud cover to include in search IF this is supported by the dataset. format: integer percent",
        type=int,
        default=0
    )
    parser_Search_Create.add_argument(
        "--max-cloud-cover",
        help="maximum cloud cover to include in search IF this is supported by the dataset. format: integer percent",
        type=int,
        default=100
    )
    # do not accept additional criteria at command line - too messy
    # pull in additional criteria interactively
    parser_Search_Create.add_argument(
        "--max-results",
        help="default 50,000 (largest value allowed)",
        type=int,
        default=50000
    )
    parser_Search_Create.add_argument(
        "--starting-number",
        type=int,
        default=1
    )
    parser_Search_Create.add_argument(
        "--sort-order",
        choices=('ASC', 'DESC'),
        default="ASC"
    )
    parser_Search_Create.add_argument(
        "file-out",
        help="Output text file. This file is json formatted, "
             "so it is suggested to assign a .json extension."
    )
    parser_Search_Create.set_defaults(
        func=cli_commands.Create_Saved_Search_To_File)

    # Search Run
    parser_Search_Run: ArgumentParser = command_subparsers.add_parser(
        "search-run",
        description="Execute a search query"
    )
    parser_Search_Run.add_argument("query-file")
    parser_Search_Run.add_argument(
        "--full-details",
        help="if specified, print full information on each search result",
        action='store_true'
    )
    parser_Search_Run.add_argument(
        "--check-encloses",
        help='add some extra checking to filter out scenes which do not significantly overlap or enclose the requested bounding box.',
        action='store_true'
    )
    parser_Search_Run.add_argument(
        "--check-using",
        help='if "metadata" check at least 4 corners lie inside metadata area.  If "wrs2" check at least 3 corners lie inside the WRS2 footprint of the scene path/row.',
        type=str,
        default="wrs2"
    )
    parser_Search_Run.set_defaults(func=cli_commands.Run_Saved_Search)

    # Download
    parser_Download: ArgumentParser = command_subparsers.add_parser(
        "download",
        description="Download api scenes. Specify an individual data product with --scene, or request multiple data products via CSV file --csv."
    )
    parser_Download_Target = parser_Download.add_mutually_exclusive_group(
        required=True)
    parser_Download_Target.add_argument(
        "--scene",
        help="triple of \'catalog dataset id\'",
        nargs=3
    )
    parser_Download_Target.add_argument(
        "--csv",
        help="comma seperated value file of scenes to download"
    )
    parser_Download.set_defaults(func=cli_commands.Download)

    # SceneMetadata
    parser_SceneMetadata: ArgumentParser = command_subparsers.add_parser(
        "scene-metadata",
        description="Returns scene metadata"
    )
    parser_SceneMetadata.add_argument(
        "--catalog",
        help="choice of catalog. (previously 'node')",
        choices=[cat.value for cat in Catalogs],
        default=Catalogs.EarthExplorer.value
    )
    parser_SceneMetadata.add_argument("dataset")
    parser_SceneMetadata.add_argument("id")
    parser_SceneMetadata.set_defaults(func=cli_commands.SceneMetadata)

    # DatasetSearch
    parser_DatasetSearch: ArgumentParser = command_subparsers.add_parser(
        "dataset-search",
        description="Search for datasets by name and spatial / temporal range"
    )
    parser_DatasetSearch.add_argument(
        "--catalog",
        help="choice of catalog. (previously 'node')",
        choices=[cat.value for cat in Catalogs],
        default=Catalogs.EarthExplorer.value
    )
    parser_DatasetSearch.add_argument("dataset-name-pattern")
    parser_DatasetSearch.add_argument(
        "--bb-centre",
        help="centre of bounding box. format: \'lat,long\'",
        type=parse_latlong
    )
    parser_DatasetSearch.add_argument(
        "--bb-length",
        help="size of bounding box in km",
        type=float
    )
    parser_DatasetSearch.add_argument(
        "--start-date",
        help="earliest date, e.g. \'2012-05-29\'",
        type=parse_datetime
    )
    parser_DatasetSearch.add_argument(
        "--end-date",
        help="latest date, e.g. \'2017-12-31\'",
        type=parse_datetime
    )
    parser_DatasetSearch.set_defaults(func=cli_commands.DatasetSearch)

    # DatasetFields
    parser_DatasetFields: ArgumentParser = command_subparsers.add_parser(
        "dataset-fields",
        description="Return additional criteria fields for a dataset. These fields may be used in advanced queries via the additionalCriteria json parameter."
    )
    parser_DatasetFields.add_argument(
        "--catalog",
        help="choice of catalog. (previously 'node')",
        choices=[cat.value for cat in Catalogs],
        default=Catalogs.EarthExplorer.value
    )
    parser_DatasetFields.add_argument("dataset")
    parser_DatasetFields.set_defaults(func=cli_commands.DatasetFields)

    # GridToLatLong
    parser_GridToLatLong: ArgumentParser = command_subparsers.add_parser(
        "grid2ll",
        description="Convert grid locations to a lat/lng center point or polygon"
    )
    parser_GridToLatLong.add_argument("grid-type", choices=('WRS1', 'WRS2'))
    parser_GridToLatLong.add_argument("response-shape", choices=('point', 'polygon'))
    parser_GridToLatLong.add_argument("path", type=int)
    parser_GridToLatLong.add_argument("row", type=int)
    parser_GridToLatLong.set_defaults(func=cli_commands.GridToLatLong)

    # Parse and call func()
    args: dict = vars(parser.parse_args(args=args))

    # logging
    if args.get("debug"):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    # turn down logging levels from packages
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    func = None
    try:
        func = args.pop("func")
    except KeyError:
        parser.print_help()
        sys.exit()

    if func:
        func(**args)
    else:
        parser.print_help()
        sys.exit()
