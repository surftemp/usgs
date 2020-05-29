import json
import os

import pkg_resources
import requests
import xmltodict


def get_metadata_xmltodict(metadata_url: str) -> dict:
    """    
    :param metadata_url: expects the scene metadataUrl as returned by the USGS EROS JSON API  
    :return: xml parsed by xmltodict
    """
    namespaces = {
        "http://earthexplorer.api.gov/eemetadata.xsd": None  # skip this namespace
    }
    return xmltodict.parse(get_metadata_xml(metadata_url), process_namespaces=True, namespaces=namespaces)


def get_metadata_xml(metadata_url: str) -> str:
    """    
    :param metadata_url: expects the scene metadataUrl as returned by the USGS EROS JSON API  
    :return: xml
    """
    # fetch xml
    r = requests.get(metadata_url)
    r.raise_for_status()
    return r.text


def staticjson(*filepath):
    """
    Load json from resource file in this package.

    :param filepath: components of path and filename inside this package/json-static/...

    :return: json object
    """
    fpath = os.path.join("json-static", *filepath)
    return json.loads(
        pkg_resources.resource_string(__name__, fpath).decode('utf-8')
    )
