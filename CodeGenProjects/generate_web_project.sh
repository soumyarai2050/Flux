#!/bin/bash
set -e
how_to_use()
{
  echo "Usage: $0 {Project-Name} <existing-web-project-name>"
  echo "Create/Update web-ui for any existing MDD project or update UI files in current project"
  exit 1
}

if [ $# -lt 1 ] ; then
  echo 1
  how_to_use
elif [ ! -d "$1" ] ; then
  echo "Can't continue no project dir with name: $1 found!"
  how_to_use
fi

OLD_PROJECT_NAME=$2

START_DIR=$PWD
cd "$1" || (echo "cd $1 failed"; exit 1)
if [ $# -eq 2 ] ; then
  if [ ! -d "$2" ] ; then
    echo "Can't continue - existing project dir with name: $2 not found!"
    how_to_use
  else
    CODE_GEN_PROJECT_WEB_UI_HOME="$2"
    cp -pr "$PWD"/../"$CODE_GEN_PROJECT_WEB_UI_HOME" . || (echo "cp failed!"; exit 1)
  fi
fi

# 1. rename strat_manager_service_json_schema.json to schema.json ; then copy to web-ui/public/.
FILES_TO_COPY=$(ls "$PWD"/output/*_json_schema.json)
cp -p "$FILES_TO_COPY" "$PWD"/web-ui/public/schema.json
# 2.cp Layout.jsx to web-ui/src/components/.
cp -p "$PWD"/output/Layout.jsx "$PWD"/web-ui/src/components/.
# 3. cp *.jsx to web-ui/src/widgets/.   # excluding Layout -
find "$PWD"/output/ -type f -name "*.jsx" -exec cp {} "$PWD"/web-ui/src/widgets/. \;
rm -f "$PWD"/web-ui/src/widgets/Layout.jsx
# 4. cp store.js web-ui/src/.
cp -p "$PWD"/output/store.js "$PWD"/web-ui/src/.
# 5. cp *.js web-ui/src/features/.   # excluding store.js
find "$PWD"/output/ -type f -name "*.js" -exec cp {} "$PWD"/web-ui/src/features/. \;
rm -f "$PWD"/web-ui/src/features/store.js
# 6. replace old project name with new project name
# replace any reference to old prj name with new prj name
if [ $# -eq 2 ] ; then
  if [ ! -d "$2" ] ; then
    echo "Can't continue - existing project dir with name: $2 not found!"
    how_to_use
  else
    echo "replacing any text occurrence of: $OLD_PROJECT_NAME with: $1 - new project name in all new project files"
    find . -type f -print0 | xargs -0 perl -pi -e "s/$OLD_PROJECT_NAME/$1/g"
  fi
fi
cd "$START_DIR" || (echo "cd $START_DIR failed"; exit 1)
echo "Updated/Created web-ui Project of $1"

# usage notes:
# 1. To start web in Dev / Debug mode (schema is serviced via react dev server):
# - set API_PUBLIC_URL in file in web-ui/src/constants.js to : 'http://127.0.0.1:3000'  # 3K is default react port - upon startup confirm exact port
# 2. To start web in Prod mode (schema is serviced via fast-api server):
# - set API_PUBLIC_URL in file in web-ui/src/constants.js to "static" URL of Fast API server

# packaging notes (automated in this script)
# 1. rename strat_manager_service_json_schema.json to schema.json ; then copy to web-ui/public/.
# 2.cp Layout.jsx to web-ui/src/components/.
# 3. cp *.jsx to web-ui/src/widgets/.   # excluding Layout -
# 4. cp store.js web-ui/src/.
# 5. cp *.js web-ui/src/features/.   # excluding store.js
# 6. replace old project name with new project name


# install notes (execute on execution server - carry output folder to deploy)
# update mongo DB URL in *_beanie_database.py
# go to web-ui folder and run following to install all required dependencies
# npm install
# some dependencies are not supported by react-18 and thus we need to force install them:
# npm install @mui/styles react-json-view  -f
# go inside scripts folder and run:
# mkdir static
# mkdir templates

# additional install for prod mode, run following:
# - export PUBLIC_URL=http://127.0.0.1:8000/static
# - npm run build  # creates a build folder inside the Web-UI
# - copy content generated in the build folder form above step to "static" folder of fast-api , move index.html to templates folder
# - for dev and prod both the fastapi url is configured in variable API_ROOT_URL of file web-ui/src/constants.js

# run notes All:
# - run mongo
# - launch fast api server using launcher

# additional run notes when running UI in Dev/Debug mode Only
# go inside web-ui directory and run:
# - npm start
