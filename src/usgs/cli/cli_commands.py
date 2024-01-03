import json
import sys
from functools import wraps
import getpass
import time

from ..datastore.datastore import Datastore
from ..api import api
from ..api.api_context import API_Context

from ..api.search_criteria import Search_Criteria
from ..utils import latlong
from ..utils.scene import Scene


USER_PASS_WARNING = """
api username and password are required
please set environment variables USGS_USERNAME and USGS_PASSWORD
or alternatively supply the --username and --password command line parameters
"""


def _ensure_login(f):
    def fn(**kwargs):
        wraps(f)
        # need login
        if not kwargs.get("username") or not kwargs.get("password"):
            print(USER_PASS_WARNING)
            sys.exit(1)
        return f(**kwargs)

    return fn


DATASTORE_WARNING = """
please specify a data directory with environment variable USGS_DATADIR
or alternatively supply the --data-dir command line parameter
"""


def _ensure_datastore(f):
    def fn(**kwargs):
        wraps(f)
        # need data_dir
        if not kwargs.get("data_dir"):
            print(DATASTORE_WARNING)
            sys.exit(1)
        return f(**kwargs)

    return fn


def Status(**kwargs):
    print(json.dumps(API_Context.Status(), indent=2))


@_ensure_login
def DatasetSearch(**kwargs):
    # bounding box
    lower_left = None
    upper_right = None
    centre = kwargs.get("bb_centre")
    if centre:
        l = kwargs.get("bb_length")
        if not l:
            print("bounding box size not specified")
            sys.exit(1)
        lower_left, upper_right = latlong.PointToBB_km(centre, l, l)

    with API_Context(
            kwargs.get("username"),
            kwargs.get("password"),
            kwargs.get("catalog")
    ) as context:
        print(json.dumps(
            context.DatasetSearch(
                kwargs.get("dataset-name-pattern"),
                lower_left=lower_left,
                upper_right=upper_right,
                start_date=kwargs.get("start-date"),
                end_date=kwargs.get("end-date")
            ),
            indent=2
        ))


@_ensure_login
def DatasetFields(**kwargs):
    with API_Context(
            kwargs.get("username"),
            kwargs.get("password"),
            kwargs.get("catalog")
    ) as context:
        print(json.dumps(
            context.DatasetFields(
                kwargs.get("dataset")
            ),
            indent=2
        ))


def GridToLatLong(**kwargs):
    print(json.dumps(
        API_Context.GridToLatLong(
            kwargs.get("grid-type"),
            kwargs.get("response-shape"),
            kwargs.get("path"),
            kwargs.get("row")
        ),
        indent=2
    ))


@_ensure_login
def SceneMetadata(**kwargs):
    with API_Context(
            kwargs.get("username"),
            kwargs.get("password"),
            kwargs.get("catalog")
    ) as context:
        # unpack as api returns a list
        (meta,) = context.SceneMetadata(
            kwargs.get("dataset"),
            [kwargs.get("id")]
        )
        print(json.dumps(meta, indent=2))


@_ensure_login
def Create_Saved_Search_To_File(**kwargs):

    # bounding box
    lower_left = None
    upper_right = None
    centre = kwargs.get("bb_centre")
    if centre:
        l = kwargs.get("bb_length")
        if not l:
            print("bounding box size not specified")
            sys.exit(1)
        lower_left, upper_right = latlong.PointToBB_km(centre, l, l)
    else:
        lower_left = latlong.LatLong(kwargs.get("lat_min"),kwargs.get("lon_min"))
        upper_right = latlong.LatLong(kwargs.get("lat_max"),kwargs.get("lon_max"))


    # test cloud cover supported
    catalog = kwargs.get("catalog")
    dataset = kwargs.get("dataset")
    cloud_min = kwargs.get("min_cloud_cover")
    cloud_max = kwargs.get("max_cloud_cover")
    day_not_night = None
    if kwargs.get("day_only") and not kwargs.get("night_only"):
        day_not_night = True
    if kwargs.get("night_only") and not kwargs.get("day_only"):
        day_not_night = False
    row = kwargs.get("row")
    path = kwargs.get("path")

    # if cloud_min != 0 or cloud_max != 100:
    #     # if cloud parameters not at their defaults then check this is supported
    #     with API_Context(
    #             kwargs.get("username"),
    #             kwargs.get("password"),
    #             catalog
    #     ) as context:
    #         datasets = context.DatasetSearch(dataset)
    #         # filter to dataset
    #         (dataset_meta,) = filter(lambda x: x["datasetName"] == dataset, datasets)
    #         if not dataset_meta["supportCloudCover"]:
    #             print("WARNING: this dataset does not support the min and max cloud cover options. These may be available as additional criteria.")

    additional_criteria = None
    if not kwargs["noninteractive"]:
        yn = input("Would you like to set any dataset-specific additional criteria? ")
        if yn in ("Y", "y", "YES", "yes", "Yes"):

            with API_Context(
                    kwargs.get("username"),
                    kwargs.get("password"),
                    catalog
            ) as context:
                fields = context.DatasetFields(dataset)

            # list of user-specified criteria to combine
            criteria = []

            while True:

                if not fields:
                    print("No additional criteria")
                    break

                print("Please select from the following criteria or type \'q\' to exit:")
                for i, field in enumerate(fields):
                    print(i, ":", field["name"])
                i = input("? ")
                print()

                try:
                    field = fields[int(i)]
                except:
                    break

                if field["valueList"]:
                    option_dict = {x["value"]: x["name"] for x in field["valueList"]}
                    print("Value list for {}:".format(field["name"]))
                    for k, v in option_dict.items():
                        print("{} : {}".format(k, v))

                print("Please enter query in format \'=x\' (equals x) or \'x<y\' (between x and y)")
                i: str = input("? ")

                if i.startswith("="):
                    # value
                    selected_value = i[1:]
                    if selected_value in ("None", ""):
                        selected_value = None
                    criteria.append(
                        api.AdditionalCriteria_Value(
                            int(field["fieldId"]),
                            "=",
                            selected_value
                        )
                    )
                else:
                    # between
                    try:
                        (x, y) = i.split("<")
                    except:
                        print("unrecognised input")
                        print()
                        continue
                    if x in ("None", ""):
                        x = None
                    if y in ("None", ""):
                        y = None
                    criteria.append(
                        api.AdditionalCriteria_Between(
                            int(field["fieldId"]),
                            x,
                            y
                        )
                    )

                print("Criterion saved")
                print()

                # remove this field from options and continue
                fields.remove(field)

            if criteria:
                if len(criteria) == 1:
                    # unpack singe criterion
                    (additional_criteria,) = criteria
                else:
                    # AND many criteria
                    additional_criteria = api.AdditionalCriteria_And(criteria)

    criteria = Search_Criteria(
        catalog,
        dataset,
        lower_left=lower_left,
        upper_right=upper_right,
        start_date=kwargs.get("start_date"),
        end_date=kwargs.get("end_date"),
        months=kwargs.get("months"),
        include_unknown_cloud_cover=False if kwargs.get("exclude_unknown_cloud_cover") else True,
        min_cloud_cover=cloud_min,
        max_cloud_cover=cloud_max,
        additional_criteria=additional_criteria,
        max_results=kwargs.get("max_results"),
        starting_number=kwargs.get("starting_number"),
        sort_order=kwargs.get("sort_order"),
        day_not_night=day_not_night,
        row=row,
        path=path
    )

    with open(kwargs.get("file-out"), "w") as f:
        json.dump(criteria.json(), f, indent=2)


@_ensure_login
def Run_Saved_Search(**kwargs):
    with open(kwargs.get("query-file"), "r") as f:
        J = json.load(f)
    criteria = Search_Criteria.from_json(J)
    with API_Context(
            kwargs.get("username"),
            kwargs.get("password"),
            criteria.catalog
    ) as context:
        # when we unpack Search_Criteria into SceneSearch() we need to
        # throw away 'catalog', which is the first member of the tuple
        J = context.SceneSearch(*criteria[1:],check_encloses=kwargs.get("check_encloses"),
                                check_using=kwargs.get("check_using"))
        for scene in J["results"]:
            if kwargs.get("full_details"):
                print(json.dumps(scene, indent=2))
            else:
                print("{}, {}, {}".format(criteria.catalog, criteria.dataset_name, scene["entityId"]))


