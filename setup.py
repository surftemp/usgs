from setuptools import setup, find_packages

import os


def package_data(package_dir, internal_path):
    paths = []
    for (dirpath, dirnames, filenames) in os.walk(
            os.path.join(
                package_dir,
                internal_path
            )
    ):
        for filename in filenames:
            paths.append(
                os.path.relpath(
                    os.path.join(dirpath, filename),
                    start=package_dir
                )
            )
    return paths


setup(
    name="usgs",
    version="0.2.4",
    packages=find_packages(
        exclude=[
            "tests",
            "tests.*"
        ]
    ),
    package_data={
        "": package_data('usgs', 'api/json-static')
    },
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'usgs = usgs.cli.cli:__main__'
        ]
    }
)
