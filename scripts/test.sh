#!/bin/bash

cd `dirname $0`

usgs_download --filename test.csv --username niallmcc --token LZ@bnNivSpsVlG4vgJlXEUB6baJsNsscomnd2HLbQCzOZlgCnaRkKnOMLAdA8cfe --output-folder outputs --download-folder downloads --file-suffixes B4.TIF B5.TIF