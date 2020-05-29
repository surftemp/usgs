import datetime
import errno
import logging
import os
import re
from urllib.parse import urlparse

import requests

LOGGER = logging.getLogger(__name__)


def Download_File(url: str, destination_directory: str, chunk_size: int = 8192, auth: tuple = None) -> str:

    LOGGER.info("Download {}".format(url))
    if auth:
        LOGGER.debug("with auth")

    # NOTE: this is not very pretty
    class AlwaysAuthSession(requests.Session):
        """
        Session class which always includes auth, even after redirect to other domain
        """
        def rebuild_auth(self, prepared_request, response):
            # override logic which strips authentication on redirect
            return

    with AlwaysAuthSession() as s:

        s.headers["User-Agent"] = None
        s.auth = auth

        r = s.get(url, stream=True)
        r.raise_for_status()

        filename = None
        if r.headers.get("Content-Disposition") and r.headers.get("Content-Disposition").startswith("Attachment; filename="):
            # try to get filename from header
            REGEX = "^Attachment; filename=(?P<filename>\S+?)(?:$|;|\s)"
            MatchObject = re.match(REGEX, r.headers.get("Content-Disposition"))
            if not MatchObject:
                raise Exception("Failed to retrieve filename from Content-Disposition header")
            D = MatchObject.groupdict()
            filename = D["filename"]
        else:
            # take filename from end of url
            parsed = urlparse(r.url)
            path = parsed.path
            _, filename = os.path.split(path)

        size: int = int(r.headers.get("Content-Length"))

        mkdir_p(destination_directory)
        file_out = os.path.join(destination_directory, filename)

        LOGGER.info("Destination on disk: {}".format(file_out))

        bytes_downloaded: int = 0
        download_start = datetime.datetime.now()
        NOTIFY_INTERVAL = datetime.timedelta(seconds=10)
        download_tick = download_start - NOTIFY_INTERVAL

        with open(file_out, 'wb') as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    bytes_downloaded += chunk_size
                    if datetime.datetime.now() - download_tick > NOTIFY_INTERVAL:
                        percent_downloaded = 100 * bytes_downloaded // size
                        runtime = datetime.datetime.now() - download_start
                        download_speed = bytes_downloaded / runtime.total_seconds() / 1000000  # MB/s
                        LOGGER.info("{}% ({}/{} bytes) @ {:.2f} MB/s".format(percent_downloaded, bytes_downloaded, size, download_speed))
                        download_tick = datetime.datetime.now()

        LOGGER.info("done")
        return file_out


def mkdir_p(path):
    """emulate mkdir -p functionality"""
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
