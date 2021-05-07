import os
import shutil
from typing import List
import json

from ..utils.scene import Scene


class Datastore:
    """
    Simple class mapping a directory structure:
    
    .../catalog/dataset/id/...
    
    Each id scene-entry should contain data files and may additionally contain:
    
    - .scene.json
    - .metadata.xml
    """

    def __init__(self, root: str):
        if not os.path.isdir(root):
            os.makedirs(root)
        self.root = root

    def get_path(self, scene: Scene):
        return self._get_path(scene.catalog, scene.dataset, scene.id)

    def get_catalogs(self):
        path = self._get_path()
        if not os.path.isdir(path):
            return []
        else:
            _, catalogs, _ = next(os.walk(path))
            return catalogs

    def get_datasets(self, catalog):
        path = self._get_path(catalog)
        if not os.path.isdir(path):
            return []
        else:
            _, datasets, _ = next(os.walk(path))
            return datasets

    def get_ids(self, catalog, dataset):
        path = self._get_path(catalog, dataset)
        if not os.path.isdir(path):
            return []
        else:
            _, ids, _ = next(os.walk(path))
            return ids

    def _get_path(self, catalog: str = None, dataset: str = None, id: str = None):
        path = self.root
        if catalog:
            path = os.path.join(path, catalog)
            if dataset:
                path = os.path.join(path, dataset)
                if id:
                    path = os.path.join(path, id)
        return path

    def exists(self, scene: Scene):
        return os.path.isdir(self.get_path(scene))

    def search(self, catalog: str = None, dataset: str = None, id: str = None):
        yield from self._filtered_iter(catalog=catalog, dataset=dataset, id=id)

    def __iter__(self):
        yield from self._filtered_iter()

    def _filtered_iter(self, catalog: str = None, dataset: str = None, id: str = None, remove_empty: bool = False):
        """
        iterate through datastore, filtering by catalog/dataset/id
        
        :param remove_empty: if True, remove empty catalog/dataset/id directories
        """

        catalogs = self.get_catalogs()

        # filter?
        if catalog:
            catalogs = filter(lambda x: x == catalog, catalogs)

        for _catalog in catalogs:

            datasets = self.get_datasets(_catalog)

            # remove if empty?
            if remove_empty:
                path = self._get_path(_catalog)
                if not os.listdir(path):
                    os.rmdir(path)
                    continue

            # filter?
            if dataset:
                datasets = filter(lambda x: x == dataset, datasets)

            for _dataset in datasets:

                ids = self.get_ids(_catalog, _dataset)

                # remove if empty?
                if remove_empty:
                    path = self._get_path(_catalog, _dataset)
                    if not os.listdir(path):
                        os.rmdir(path)
                        continue

                # filter?
                if id:
                    ids = filter(lambda x: x == id, ids)

                for _id in ids:

                    # remove if empty?
                    if remove_empty:
                        path = self._get_path(_catalog, _dataset, _id)
                        if not os.listdir(path):
                            os.rmdir(path)
                            continue

                    yield Scene(_catalog, _dataset, _id)

    def delete(self, scene: Scene):
        path = self.get_path(scene)
        if os.path.isdir(path):
            shutil.rmtree(path)

    def new(self, scene: Scene, files: List[str] = None):
        """
        Create and populate new Scene(catalog, dataset, id) in datastore

        :param files: files to move into datastore
        """
        if self.exists(scene):
            raise ValueError("Scene already exists in datastore: {}".format(scene))
        path = self.get_path(scene)
        os.makedirs(path)
        if files:
            for file in files:
                shutil.move(file, path)

    def delete_all(self, yes_really: bool = False):
        """There is no going back"""
        if yes_really:
            for catalog in self.get_catalogs():
                shutil.rmtree(self._get_path(catalog))

    def clean_up(self):
        """Remove empty dirs"""
        for _ in self._filtered_iter(remove_empty=True):
            pass

    def ls(self, scene: Scene):
        path = self.get_path(scene)
        return [os.path.join(path, x) for x in os.listdir(path)]
