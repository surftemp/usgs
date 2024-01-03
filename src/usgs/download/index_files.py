import argparse
import os
import re

from usgs.utils.file_utils import FileUtils

class SceneScanner:

    PATH_PATTERN = re.compile("<WRS_PATH>([0-9]+)</WRS_PATH>")
    ROW_PATTERN = re.compile("<WRS_ROW>([0-9]+)</WRS_ROW>")

    def __init__(self, index_path):
        self.utils = FileUtils(index_path) if index_path else None
        self.row_paths = set()

    def scan(self,folder):
        scanned = 0
        for root, folders, files in os.walk(folder):
            print(f"Scanning folder {root}")
            for file in files:
                filepath = os.path.join(root,file)
                if self.utils:
                    self.utils.put_path(file, filepath)
                row = path = None
                if filepath.endswith(".xml"):
                    with open(filepath,"r") as f:
                        for line in f.readlines():
                            line = line.strip()
                            m = re.match(SceneScanner.ROW_PATTERN,line)
                            if m:
                                row = int(m.group(1))
                            m = re.match(SceneScanner.PATH_PATTERN,line)
                            if m:
                                path = int(m.group(1))
                if row is not None and path is not None:
                    self.row_paths.add((row,path))
                scanned += 1
        return scanned

    def close(self):
        if self.utils:
            self.utils.close()

    def dump_index(self, to_csv_path):
        if self.utils:
            self.utils.dump(to_csv_path)

    def __iter__(self):
        return self.utils.__iter__() if self.utils else None

    def dump_rowpaths(self, to_path):
        with open(to_path, "w") as f:
            f.write("row,path")
            for (row,path) in self.row_paths:
                f.write(f"\n{row},{path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-folder", nargs="+", help="supply a folder to scan", default=[])
    parser.add_argument("--index-path", help="read or update an index file allowing scene files to be quickly located", default=None)
    parser.add_argument("--dump-csv", type=str, help="dump index contents to CSV")
    parser.add_argument("--collect-rowpath-csv", type=str, help="collect rows and paths encountered to a CSV file")
    parser.add_argument("--search-index", type=str, help="search for a file in the index")

    args = parser.parse_args()
    scanner = SceneScanner(args.index_path)

    for folder in args.scan_folder:
        folder_scanned = scanner.scan(folder)
        print(f"scanned {folder_scanned} files from {folder}")

    if args.dump_csv:
        scanner.dump_index(args.dump_csv)

    if args.collect_rowpath_csv:
        scanner.dump_rowpaths(args.collect_rowpath_csv)

    if args.index_path:
        if args.search_index:
            print(scanner.utils.get_path(args.search_index))
        else:
            print(scanner.utils.summary())

    scanner.close()

if __name__ == '__main__':
    main()
