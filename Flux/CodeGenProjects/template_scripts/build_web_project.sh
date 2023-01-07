#!/bin/bash
set -e

# while inside scripts folder , run:
cd ../../../PyCodeGenEngine/FluxCodeGenCore
python gen_core_proto_pb2.py
cd -
mkdir -p static
mkdir -p templates
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
"$PWD"/gen_web_project.sh template_project_name
