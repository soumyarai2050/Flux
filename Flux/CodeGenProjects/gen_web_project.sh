#!/bin/bash

# packaging notes (automated in this script)
# 0. cp package.json to web-ui/.
# 1. rename strat_manager_service_json_schema.json to schema.json ; then copy to web-ui/public/.
# 2. cp *.jsx to web-ui/src/widgets/.
# 3. cp store.js, selectors.js, projectSpecificUtils.js and config.js to web-ui/src/.
# 3.5. cp modelComponentLoader.js to web-ui/src/utils/.
# 4. cp *.js web-ui/src/features/.   # excluding store.js, projectSpecificUtils.js, config.js, selectors.js, modelComponentLoader.js
# 5. If second parameter was supplied:
# - 5.1 optionally replace old project name with new project name
# - 5.2 optionally search for capitalized space case of old project name in file web-ui/public/index.html and replace with capitalized space case of new project name


set -e
how_to_use()
{
  echo "Usage: $0 {Project-Name} <existing-web-project-name>"
  echo "Create/Update web-ui for any existing MDD project or update UI files in current project"
  exit 1
}

if [ $# -lt 1 ] ; then
  how_to_use
elif [ ! -d "$1" ] ; then
  echo "Can't continue no project dir with name: $1 found!"
  how_to_use
fi

OLD_PROJECT_NAME=""

START_DIR=$PWD
if [ $# -eq 2 ] ; then
  if [ ! -d "$2" ] ; then
    OLD_PROJECT_NAME=$2
    echo "Can't continue - existing project dir with name: $2 not found!"
    how_to_use
  else
    cd "$1" || (echo "cd $1 failed from dir: $PWD"; exit 1)
    CODE_GEN_PROJECT_WEB_UI_HOME="$2"
    cp -pr "$PWD"/../"$CODE_GEN_PROJECT_WEB_UI_HOME" . || (echo "cp failed!"; exit 1)
    cd - || (echo "cd - failed from dir: $PWD"; exit 1)
  fi
else  # test WebUi exist in the current project
  cd "$1" || (echo "cd $1 failed from dir: $PWD"; exit 1)
  if [ ! -d "web-ui" ] ; then
    echo "Can't continue - no source project supplied to copy web-ui and target project does not have web-ui either!"
    exit 1
  # else  # else not required, all good - continue
  fi
fi

# 0. cp package.json to web-ui/.
cp -p "$PWD"/generated/JsLayout/package.json "$PWD"/web-ui/.
# 1. rename strat_manager_service_json_schema.json to schema.json ; then copy to web-ui/public/.
FILES_TO_COPY=$(ls "$PWD"/generated/JSONSchema/*_json_schema.json)
cp -p "$FILES_TO_COPY" "$PWD"/web-ui/public/schema.json
# 2. cp *.jsx to web-ui/src/widgets/.
find "$PWD"/generated/JsLayout/ -type f -name "*.jsx" -exec cp {} "$PWD"/web-ui/src/widgets/. \;
# 3. cp store.js, selectors.js, projectSpecificUtils.js and config.js to web-ui/src/.
cp -p "$PWD"/generated/JsLayout/store.js "$PWD"/web-ui/src/.
cp -p "$PWD"/generated/JsLayout/config.js "$PWD"/web-ui/src/.
cp -p "$PWD"/generated/JsLayout/selectors.js "$PWD"/web-ui/src/.
cp -p "$PWD"/generated/JsLayout/projectSpecificUtils.js "$PWD"/web-ui/src/.
# 3.5. cp modelComponentLoader.js to web-ui/src/utils/.
cp -p "$PWD"/generated/JsLayout/modelComponentLoader.js "$PWD"/web-ui/src/utils/.
# 4. cp *.js web-ui/src/features/.   # excluding store.js, projectSpecificUtils.js, config.js, selectors.js, modelComponentLoader.js
find "$PWD"/generated/JsLayout/ -type f -name "*.js" -exec cp {} "$PWD"/web-ui/src/features/. \;
rm -f "$PWD"/web-ui/src/features/store.js
rm -f "$PWD"/web-ui/src/features/projectSpecificUtils.js
rm -f "$PWD"/web-ui/src/features/config.js
rm -f "$PWD"/web-ui/src/features/selectors.js
rm -f "$PWD"/web-ui/src/features/modelComponentLoader.js
# 5. replace old project name with new project name
# replace any reference to old prj name with new prj name
if [ $# -eq 2 ] ; then
  if [ ! -d "$2" ] ; then
    echo "Can't continue - existing project dir with name: $2 not found!"
    how_to_use
  else
    echo "replacing any text occurrence of: $OLD_PROJECT_NAME with: $1 - new project name in all new project files"
    find . -type f -print0 | xargs -0 perl -pi -e "s#$OLD_PROJECT_NAME#$1#g"
  fi
fi
cd "$START_DIR" || (echo "cd $START_DIR failed from dir: $PWD"; exit 1)
echo "Updated/Created web-ui Project of $1"

