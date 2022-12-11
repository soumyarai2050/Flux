#!/bin/bash
set -e

# while inside scripts folder , run:
mkdir -p static
mkdir -p templates
mkdir -p ../output
mkdir -p ../web-ui/src/widgets
python gen_beanie_model.py
python gen_beanie_fastapi.py
python gen_js_layouts.py
python gen_json_schema.py

cd ../../
"$PWD"/gen_web_project.sh addressbook
