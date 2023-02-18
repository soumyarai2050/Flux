#!/bin/bash
set -e
# we are in script DIR
./clean-web-project.sh
if [ -d "../web-ui" ] ; then
  rm -rf ../web-ui  # deep clean removes complete web-ui including the installed npm inside
fi
if [ -d "../log" ] ; then
  rm -rf ../log  # deep clean removes complete log directory
fi