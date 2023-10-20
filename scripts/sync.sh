#!/bin/bash

rootfolder=`dirname $0`/..

rsync -avr $rootfolder/src niallmcc@login2.jasmin.ac.uk:/home/users/niallmcc/github/usgs
rsync -avr $rootfolder/pyproject.toml niallmcc@login2.jasmin.ac.uk:/home/users/niallmcc/github/usgs
rsync -avr $rootfolder/setup.cfg niallmcc@login2.jasmin.ac.uk:/home/users/niallmcc/github/usgs
rsync -avr $rootfolder/environment.yml niallmcc@login2.jasmin.ac.uk:/home/users/niallmcc/github/usgs