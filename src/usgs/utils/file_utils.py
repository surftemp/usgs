import os.path
import dbm
import os.path

class FileUtils:

    def __init__(self, path):
        self.path = path
        self.store = dbm.open(path, 'c')

    def put_path(self, filename, filepath):
        self.store[filename.encode("utf-8")] = os.path.abspath(filepath).encode("utf-8")

    def get_path(self, filename):
        try:
            return self.store[filename].decode("utf-8")
        except:
            return None

    def close(self):
        self.store.close()
        self.store = None

    def __iter__(self):
        return self

    def dump(self, to_path):
        with open(to_path, "w") as f:
            f.write("filename,path")

            for key in self.store.keys():
                path = self.store[key]
                f.write(f"\n{key.decode('utf-8')},{path.decode('utf-8')}")

    def summary(self):
        return f"Index {self.path} contains {len(self.store)} entries"