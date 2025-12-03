#!/bin/bash

# copy relevant files to JASMIN

rootfolder=`dirname $0`/..
hostname=$1
username=$2
destfolder=$3

if [ -z ${hostname} ] || [ -z ${username} ] || [ -z ${destfolder} ];
then
  echo provide the hostname username and destination folder on JASMIN as arguments
else
  rsync -avr --delete $rootfolder/src $username@$hostname:$destfolder/usgs
  rsync -avr $rootfolder/pyproject.toml $username@$hostname:$destfolder/usgs
  rsync -avr $rootfolder/setup.cfg $username@$hostname:$destfolder/usgs
fi
