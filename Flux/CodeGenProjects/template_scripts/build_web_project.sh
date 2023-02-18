#!/bin/bash
set -e

# we are in scripts folder
# test if web-ui present - if not present - generate gen_web_ui.sh
cd ..
PROJECT_NAME=${PWD##*/}          # assign project name to a variable
PROJECT_NAME=${PROJECT_NAME:-/}  # correct project name for case where PWD=/
if [ -d "web-ui" ] ; then
  echo "Can't create web-ui project, Directory already exists, updating instead"
  cd -  # back in script folder
  "$PWD"/gen_web_ui.sh "update"
  cd -  # restore PWD state to pre if state
else
  cd -  # back in script folder
  "$PWD"/gen_web_ui.sh
  cd -  # restore PWD state to pre if state
fi
cd - # back in script folder

cd ../../../PyCodeGenEngine/FluxCodeGenCore
python gen_core_proto_pb2.py
cd - # back in script folder
mkdir -p static
mkdir -p templates
mkdir -p  ../log
mkdir -p ../generated
mkdir -p ../web-ui/src/widgets
python gen_json_sample.py
python gen_cached_pydantic_model.py
python gen_cached_fastapi.py
python gen_beanie_model.py
python gen_beanie_fastapi.py
python gen_js_layouts.py
python gen_json_schema.py

cd ../../
"$PWD"/gen_web_project.sh "$PROJECT_NAME"
