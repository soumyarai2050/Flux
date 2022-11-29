#!/bin/bash
set -e
python gen_beanie_model.py
python gen_beanie_fastapi.py
python gen_js_layouts.py
python gen_json_schema.py
cd ../../
"$PWD"/generate_web_project.sh addressbook
cd -
cd ../web-ui
npm install
npm install @mui/styles react-json-view  -f
cd -
mkdir static
mkdir templates

# additional install for prod mode, run following:
# - export PUBLIC_URL=http://127.0.0.1:8000/static
# - npm run build  # creates a build folder inside the Web-UI
# - copy content generated in the build folder form above step to "static" folder of fast-api , move index.html to templates folder
# - for dev and prod both the fastapi url is configured in variable API_ROOT_URL of file web-ui/src/constants.js
