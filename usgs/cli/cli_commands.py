import json
import sys
from functools import wraps
import getpass
import time

from ..datastore.datastore import Datastore
from ..api import api
from ..api.api_context import API_Context
from ..download.download_usgs import DownloadUSGS
from ..download.dataset_info import AUTH
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


@_ensure_datastore
@_ensure_login
def Download(**kwargs):

    datastore = Datastore(kwargs.get("data_dir"))
    jobs = []

    suffix_filter = kwargs.get("suffix_filter")
    prune_suffixes = kwargs.get("prune_suffixes").split(",")
    prune_suffixes = list(map(lambda suffix: suffix.strip(), prune_suffixes))
    download_names = kwargs.get("download_names")
    if download_names is None:
        download_names = []
    else:
        download_names = download_names.split(",")

    scene = kwargs.get("scene")
    if scene:
        # just the one scene specified @ command line
        jobs = [Scene(*scene)]
    elif kwargs.get("csv"):
        # potentially many scenes @ csv file
        with open(kwargs.get("csv"), "r") as f:

            def line_to_scene(l: str):
                items = [x.strip() for x in l.split(",")]
                return Scene(*items)

            jobs = list(map(line_to_scene, f.readlines()))

    if len(jobs) == 0:
        print("No scenes provided for download")
        return
    
    # require that all products to be downloaded come from the same catalog
    # and dataset
    catalog_dataset_pairs = set(
        [(scene.catalog, scene.dataset) for scene in jobs]
    )
    if len(catalog_dataset_pairs) != 1:
        raise ValueError("Downloads must be from the same catalog and dataset")

    ((catalog, dataset),) = catalog_dataset_pairs

    # look for scenes already downloaded
    on_disk = {scene: datastore.exists(scene) for scene in jobs}
    if not kwargs.get("ignore_cache") and all(on_disk.values()):
        print("All requested downloads are already on disk!")
        return

    # do we need any additional auth?
    # if so, query the user here
    auth = None
    auth_required = AUTH.get((catalog, dataset))
    if auth_required:
        print("{} authorization required".format(auth_required))
        user = input("Please enter {} username: ".format(auth_required))
        password = getpass.getpass("Please enter {} password: ".format(auth_required))
        auth = (user, password)

    for scene in jobs:

        # does it already exist on disk?
        if on_disk.get(scene) and not kwargs.get("ignore_cache"):
            print("Already on disk")
            continue

        with API_Context(
                kwargs.get("username"),
                kwargs.get("password"),
                scene.catalog
        ) as context:
            retry_count = 5
            retry_delay_s = 10
            while retry_count > 0:
                retry_count -= 1
                try:
                    product_id = None
                    meta = None
                    try:
                        meta = context.SceneMetadata(scene.dataset, scene.id)
                        if meta is not None:
                            meta_fields = meta["metadata"]
                            for meta_field in meta_fields:
                                if meta_field["fieldName"] == 'Landsat Product Identifier':
                                    product_id = meta_field['value']
                    except:
                        pass

                    if meta is None:
                        print("WARNING - failed to get scene-metadata prior to download")


                    s = DownloadUSGS(context, scene.catalog, scene.dataset, scene.id, suffix_filter=suffix_filter, download_names=download_names)
                    downloaded_files = s.download()

                except Exception as ex:
                    print("ERROR - failed to download: %s (%s) with %d retries left"%(scene.id,str(ex),retry_count))
                    if retry_count > 0:
                        print("Waiting %d seconds before retry" % retry_delay_s)
                        time.sleep(retry_delay_s)
                        retry_delay_s *= 2
                    continue
                # create a new item in datastore
                # which moves downloaded file out of temp
                if downloaded_files:
                    datastore.new(scene, files=downloaded_files, prune_suffixes=prune_suffixes)

                    # report final path of download
                    final_path = datastore.get_path(scene)
                    print("Saved to {}".format(final_path))
                break

