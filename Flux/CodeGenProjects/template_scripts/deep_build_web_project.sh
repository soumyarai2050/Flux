#!/bin/bash
set -e

# we are in scripts folder
# 1. run build_web_project.sh
# 2. go to generated web-ui dir
# 3. run npm install
# 4. npm install react-json-view  -f
./build_web_project.sh
cd ..
if [ -d "web-ui" ] ; then
  cd web-ui
  npm install
  npm install react-json-view  -f
else
  echo "Error web-ui folder not found even after running build_web_project.sh - unable to proceed"
  exit 1
fi
cd - # back in script folder
