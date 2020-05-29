import unittest
import json
import tempfile
import os

from io import StringIO

from usgs.api.url_settings import API_VERSION
from usgs.cli import cli
from usgs.utils.scene import Scene
from ..settings import USGS_USERNAME, USGS_PASSWORD, DATASET_NAME
from unittest.mock import patch
from usgs.datastore.datastore import Datastore


class Test_CLI(unittest.TestCase):

    def test_no_command(self):

        with patch('sys.stdout', new=StringIO()) as stdout:
            # expected to hit:
            # parser.print_help()
            # sys.exit()
            with self.assertRaises(SystemExit):
                cli.__main__([])
        out = stdout.getvalue()
        self.assertRegex(out, '^usage:')

    def test_bad_command(self):

        with patch('sys.stdout', new=StringIO()) as stdout, patch('sys.stderr', new=StringIO()) as stderr:
            with self.assertRaises(SystemExit):
                cli.__main__([
                    'this_command_does_not_exist'
                ])
        # stdout blank
        out = stdout.getvalue()
        self.assertFalse(out)
        # stderr has usage, and 'error: invalid choice'
        err = stderr.getvalue()
        self.assertRegex(err, 'usage:')
        self.assertRegex(err, 'error: invalid choice')
        self.assertRegex(err, 'choose from')

    def test_status(self):

        with patch('sys.stdout', new=StringIO()) as stdout:
            cli.__main__([
                'status'
            ])
        out = stdout.getvalue()
        J = json.loads(out)
        self.assertEqual(
            J.get('errorCode'), None
        )
        self.assertEqual(
            J.get('error'), ""
        )
        self.assertEqual(
            J.get('api_version'), API_VERSION
        )

    def test_status_h(self):

        with patch('sys.stdout', new=StringIO()) as stdout:
            with self.assertRaises(SystemExit):
                cli.__main__([
                    "status",
                    "-h"
                ])
        out = stdout.getvalue()
        self.assertRegex(out, '^usage:')

    def test_dataset_search(self):

        with patch('sys.stdout', new=StringIO()) as stdout:
            cli.__main__([
                '--username',
                USGS_USERNAME,
                '--password',
                USGS_PASSWORD,
                'dataset-search',
                'landsat 8'
            ])
        out = stdout.getvalue()
        self.assertIn(DATASET_NAME, out)

    def test_dataset_fields(self):

        with patch('sys.stdout', new=StringIO()) as stdout:
            cli.__main__([
                '--username',
                USGS_USERNAME,
                '--password',
                USGS_PASSWORD,
                'dataset-fields',
                DATASET_NAME
            ])
        out = stdout.getvalue()
        self.assertIn('Landsat Product Identifier', out)

    def test_g2ll(self):

        with patch('sys.stdout', new=StringIO()) as stdout:
            cli.__main__([
                'grid2ll',
                'WRS1',
                'point',
                '1',
                '1'
            ])
        out = stdout.getvalue()
        self.assertIn(r'"shape": "point"', out)

    def test_search_create(self):
        json_file = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
        json_file.close()
        # print(json_file.name)

        def mock_input():
            # Would you like to set any dataset-specific additional criteria?
            yield 'n'

        with patch('builtins.input', return_value=mock_input):
            cli.__main__([
                '--username',
                USGS_USERNAME,
                '--password',
                USGS_PASSWORD,
                'search-create',
                DATASET_NAME,
                json_file.name
            ])

        with open(json_file.name, 'r') as f:
            J = json.load(f)

        self.assertDictEqual(
            J,
            {
                "catalog": "EE",
                "dataset_name": DATASET_NAME,
                "lower_left": None,
                "upper_right": None,
                "start_date": None,
                "end_date": None,
                "months": None,
                "include_unknown_cloud_cover": True,
                "min_cloud_cover": 0,
                "max_cloud_cover": 100,
                "additional_criteria": None,
                "max_results": 50000,
                "starting_number": 1,
                "sort_order": "ASC"
            }
        )

        try:
            # clean up
            os.remove(json_file.name)
        except:
            pass

    def test_search_run(self):
        json_file = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
        json_file.close()
        # print(json_file.name)

        def mock_input():
            # Would you like to set any dataset-specific additional criteria?
            yield 'n'

        with patch('builtins.input', return_value=mock_input):
            cli.__main__([
                '--username',
                USGS_USERNAME,
                '--password',
                USGS_PASSWORD,
                'search-create',
                '--max-results',
                '1',
                DATASET_NAME,
                json_file.name
            ])

        with patch('sys.stdout', new=StringIO()) as stdout:
            cli.__main__([
                '--username',
                USGS_USERNAME,
                '--password',
                USGS_PASSWORD,
                'search-run',
                json_file.name
            ])

        out = stdout.getvalue()
        # 'EE, LANDSAT_8_C1, <id>'
        self.assertRegex(out, "^EE, {}, ".format(DATASET_NAME))

        try:
            # clean up
            os.remove(json_file.name)
        except:
            pass

    def test_scene_metadata(self):
        json_file = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
        json_file.close()
        # print(json_file.name)

        def mock_input():
            # Would you like to set any dataset-specific additional criteria?
            yield 'n'

        with patch('builtins.input', return_value=mock_input):
            cli.__main__([
                '--username',
                USGS_USERNAME,
                '--password',
                USGS_PASSWORD,
                'search-create',
                '--max-results',
                '1',
                DATASET_NAME,
                json_file.name
            ])

        with patch('sys.stdout', new=StringIO()) as stdout:
            cli.__main__([
                '--username',
                USGS_USERNAME,
                '--password',
                USGS_PASSWORD,
                'search-run',
                '--full-details',
                json_file.name
            ])

        # should get json object from --full-details
        J1 = json.loads(stdout.getvalue())

        with patch('sys.stdout', new=StringIO()) as stdout:
            cli.__main__([
                '--username',
                USGS_USERNAME,
                '--password',
                USGS_PASSWORD,
                'scene-metadata',
                DATASET_NAME,
                J1['entityId']
            ])

        J2 = json.loads(stdout.getvalue())

        # remove stuff that is only on scene-metadata
        self.assertTrue(J2.pop('metadataFields'))
        J2.pop('dataAccess')  # may be None

        for k, v in J2.items():
            self.assertEqual(J1[k], v)

        try:
            # clean up
            os.remove(json_file.name)
        except:
            pass

    def test_download(self):
        json_file = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
        json_file.close()
        # print(json_file.name)

        def mock_input():
            # Would you like to set any dataset-specific additional criteria?
            yield 'n'

        with patch('builtins.input', return_value=mock_input):
            cli.__main__([
                '--username',
                USGS_USERNAME,
                '--password',
                USGS_PASSWORD,
                'search-create',
                '--max-results',
                '1',
                DATASET_NAME,
                json_file.name
            ])

        with patch('sys.stdout', new=StringIO()) as stdout:
            cli.__main__([
                '--username',
                USGS_USERNAME,
                '--password',
                USGS_PASSWORD,
                'search-run',
                json_file.name
            ])

        out = stdout.getvalue()
        # 'EE, LANDSAT_8_C1, <id>'
        _catalog, _dataset, _id = [s.strip() for s in out.split(',')]

        self.assertEqual(_catalog, 'EE')
        self.assertEqual(_dataset, DATASET_NAME)

        # temp datastore
        datastore_dir = tempfile.TemporaryDirectory()
        # print(datastore_dir.name)

        # when we test the 'download', we need to mock 2 functions from
        # usgs.download

        def mock_Download_File(url: str, destination_directory: str, chunk_size: int = 8192, auth: tuple = None):
            with open(os.path.join(destination_directory, 'download.mock.txt'), 'w') as f:
                f.write(url)
                path = f.name
            return path

        def mock_get_full_product_download_url(download_url: str, usgs_username: str, usgs_password: str, product_label: str = None, scene: Scene = None):
            return "www.example.com"

        with patch(
                'usgs.download.download.Download_File',
                new=mock_Download_File
        ), patch(
                'usgs.download.scrape.get_full_product_download_url',
                new=mock_get_full_product_download_url
        ):
            cli.__main__([
                '--username',
                USGS_USERNAME,
                '--password',
                USGS_PASSWORD,
                '--data-dir',
                datastore_dir.name,
                'download',
                '--scene',
                _catalog,
                _dataset,
                _id
            ])

        scene = Scene(_catalog, _dataset, _id)
        datastore = Datastore(datastore_dir.name)
        self.assertTrue(datastore.exists(scene))
        self.assertTrue(datastore.ls(scene))

        # clean up
        datastore_dir.cleanup()
        del datastore_dir
        try:
            os.remove(json_file.name)
        except:
            pass