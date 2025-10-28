

import argparse
import glob
import os.path
import shutil

parser=argparse.ArgumentParser()

parser.add_argument("input_path")
parser.add_argument("output_path")
parser.add_argument("--dry-run",action="store_true")

args = parser.parse_args()

for input_path in glob.glob(args.input_path):
    components = input_path.split("_")

    product = components[1]
    adate = components[3]
    year = adate[0:4]
    month = adate[4:6]
    day = adate[6:8]

    output_folder = os.path.join(args.output_path, year, month, day)
    os.makedirs(output_folder, exist_ok=True)
    if not args.dry_run:
        shutil.move(input_path, output_folder)
    print(f"{input_path} => {output_folder}")