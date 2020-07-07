import logging
import re

import requests
from bs4 import BeautifulSoup, element

from .dataset_info import LABEL
from ..api.api import NotAuthorisedException
from ..utils.scene import Scene

LOGGER = logging.getLogger(__name__)


def get_full_product_download_url(download_url: str, usgs_username: str, usgs_password: str, product_label: str = None, scene: Scene = None) -> str:
    """
    utility function to retrieve the full product download url from the download_url page which the USGS EROS JSON API returns.
    
    - fetch the USGS EROS login page
    - scrape login page for login form & inputs (including hidden csrf token)
    - submit login
    - fetch the page from download_url
    - scrape this page for the download button corresponding to product_label
    - follow url of this button
    - return product download url
    
    :param download_url: expects the scene downloadUrl as returned by the USGS EROS JSON API
    :param usgs_username: USGS EROS username
    :param usgs_password: USGS EROS password
    :param product_label: expected name of product on downloadUrl page. e.g. Standard Product
    :param scene: if product_label not known, provides a best guess based on scene
    :return: direct url to file
    """

    USGS_LOGIN_URL = "https://ers.cr.usgs.gov/login"

    # product_type_name
    if not product_label:
        if not scene:
            raise ValueError("Must provide either product_label or scene")
        product_label = LABEL.get(
            (scene.catalog, scene.dataset),
            "Standard"  # default guess
        )

    # need a session to persist login cookies
    with requests.Session() as s:

        s.headers["User-Agent"] = None

        # first grab the api login page

        LOGGER.debug("Fetch login page @ {}".format(USGS_LOGIN_URL))

        r = s.get(USGS_LOGIN_URL)
        r.raise_for_status()

        # make soup
        soup = BeautifulSoup(r.text, 'html.parser')

        # extract the form
        form = soup.html.find(
            "form",
            attrs={
                "id": "loginForm",
                "name": "loginForm"
            }
        )

        if not form:
            raise Exception("Failed to find login form @ {}".format(r.url))

        # expect these things:
        if form.attrs.get("method") != "post":
            raise Exception("Login form method != post @ {}".format(r.url))
        if form.attrs.get("action") != "/login/":
            raise Exception("Login form action != /login/ @ {}".format(r.url))

        # construct login request
        inputs = form.find_all("input")
        params = {x.attrs.get("name"): x.attrs.get("value") for x in inputs if x.attrs.get("name")}

        if "username" not in params:
            raise Exception("No username in login form @ {}".format(r.url))

        if "password" not in params:
            raise Exception("No password in login form @ {}".format(r.url))

        params["username"] = usgs_username
        params["password"] = usgs_password

        LOGGER.debug("Post login @ {}".format(USGS_LOGIN_URL))

        # make the login post request, but do not follow 302 redirect
        r = s.post(USGS_LOGIN_URL, data=params, allow_redirects=False)
        r.raise_for_status()

        # if login success:
        # response "302 Found" which redirects to Location: http://ers.cr.usgs.gov/
        # if login fails:
        # response "200 OK" which loads the login page with
        # <div id="pageError">Invalid username/password</div>

        if r.status_code == requests.codes.found and r.headers.get('Location') == 'http://ers.cr.usgs.gov/':
            # happy path
            pass
        else:
            # anticipate that login has failed

            # follow the expected login fail
            if r.status_code == requests.codes.ok:
                # make soup
                soup = BeautifulSoup(r.text, 'html.parser')

                # see if div exists
                if soup.html:
                    if soup.html.find("div", attrs={"id": "pageError"}, text="Invalid username/password"):
                        raise NotAuthorisedException("Login failed: Invalid username/password")

            # if we end up here then something unexpected has happened
            raise NotAuthorisedException("Login failed")

        # now logged into api

        LOGGER.debug("Load downloads page @ {}".format(download_url))

        # grab the downloads page
        r = s.get(download_url)
        r.raise_for_status()

        LOGGER.debug("Find download link for {}".format(product_label))

        # make soup
        soup = BeautifulSoup(r.text, 'html.parser')

        # extract the divs (enclosing the "Download" buttons")
        input_divs = soup.html.find_all(
            "div",
            attrs={
                "class": "row clearfix"
            }
        )

        def filter_input_divs(tag: element.Tag):
            inner_div = tag.findChild(
                "div",
                attrs={
                    "class": "name"
                },
                recursive=False
            )
            if not inner_div:
                return False
            elif inner_div.text.strip().startswith(product_label):
                # have to strip() as lots of white space
                return True
            else:
                return False

        input_divs = list(filter(filter_input_divs, input_divs))

        if len(input_divs) != 1:
            raise Exception("Failed to find {} download url @ {}".format(product_label, r.url))

        (input_div,) = input_divs
        input = input_div.findChild("input")

        REGEX = r"^window.location='(?P<url>.+)'$"
        MatchObject = re.match(REGEX, input.attrs.get("onclick"))
        if not MatchObject:
            raise Exception("Failed to find {} download url @ {}".format(product_label, r.url))
        D = MatchObject.groupdict()
        product_url = D["url"]

        # expect a "302 Found" redirect to the actual download
        # if login has failed we get "302 Found" redirect back to login page

        r = s.head(product_url)
        r.raise_for_status()

        if r.status_code != requests.codes.found:
            raise Exception("Expected 302 Found redirect @ {}".format(r.url))
        if r.headers.get('Location').startswith(USGS_LOGIN_URL):
            raise NotAuthorisedException("Got redirected back to login page @ {}".format(r.url))
        else:
            actual_download_url = r.headers["Location"]

        LOGGER.debug("url: {}".format(actual_download_url))

        return actual_download_url
