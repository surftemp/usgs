
import argparse
import os
import rioxarray

parser = argparse.ArgumentParser()
parser.add_argument("folder",help="folder to search under")
parser.add_argument("--remove", action="store_true", help="remove each zero sized file")
parser.add_argument("--verbose", action="store_true", help="print progress messages")

args = parser.parse_args()

total_files = 0
bad_files = 0

def check_download(download_path):
    if not os.path.isfile(download_path):
        print(f"{download_path} does not exist or is not a file")
        return False
    if os.lstat(download_path).st_size == 0:
        print(f"{download_path} is empty")
        return False
    if download_path.lower().endswith(".tif"):
        # check that the TIF file can be loaded
        da = None
        try:
            da = rioxarray.open_rasterio(download_path).squeeze()
            d1 = da[0,0].item()
            d2 = da[0,-1].item()
            d3 = da[-1,0].item()
            d4 = da[-1,-1].item()
        except:
            print(f"{download_path} is corrupt")
            return False
        finally:
            if da is not None:
                da.close()
    return True

def safe_remove(path):
    try:
        os.remove(path)
        print(f"Removed {path}")
    except Exception as ex:
        print(f"Unable to remove {path}: {ex}")

for folder, dirs, files in os.walk(args.folder):
    for file in files:
        path = os.path.join(folder,file)
        total_files += 1
        if os.path.islink(path):
            check_path = os.readlink(path)
        else:
            check_path = path
        if not check_download(check_path):
            bad_files += 1
            if args.remove:
                safe_remove(path)
            if path != check_path:
                safe_remove(check_path)
        else:
            if args.verbose:
                print("OK: "+path)

print(f"Scanned {total_files}, found {bad_files} bad files")