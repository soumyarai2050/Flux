#!/bin/bash
set -e

DEFAULT_API_PUBLIC_URL="http://127.0.0.1:3000"
DEFAULT_MONGO_DB_URI="mongodb://localhost:27017"

while [ $# -gt 0 ]; do
  case "$1" in
    DEPLOY=*)
      DEPLOY="${1#*=}"
      ;;
    INSTALL=*)
      INSTALL="${1#*=}"
      ;;
    PUBLIC_URL=*)
      PUBLIC_URL="${1#*=}"
      ;;
    MONGO_DB_URL=*)
      MONGO_DB_URL="${1#*=}"
      ;;
    *)
      echo "Invalid argument: $1"
      how_to_use
      exit 1
  esac
  shift
done

[ -z "$DEPLOY" ] && DEPLOY="dev"
DEPLOY=$( tr '[:upper:]' '[:lower:]' <<<"$DEPLOY" )

[ -z "$PUBLIC_URL" ] && PUBLIC_URL="default"
PUBLIC_URL=$( tr '[:upper:]' '[:lower:]' <<<"$PUBLIC_URL" )

[ -z "$MONGO_DB_URL" ] && MONGO_DB_URL="default"
MONGO_DB_URL=$( tr '[:upper:]' '[:lower:]' <<<"$MONGO_DB_URL" )

[ -z "$INSTALL" ] && INSTALL=0

how_to_use() {
  echo 'Usage: env <DEPLOY="Dev"|"Prod"> PUBLIC_URL="default"|"user-intended-url"> <INSTALL="any-non-0-value"> <MONGO_DB_URL="default"|"user-intended-mongodb-url"> $0 <any-value>'
  echo 'default values if any of pairs not provided: DEPLOY="Dev", PUBLIC_URL="default", INSTALL="0", MONGO_DB_URL="default"'
  echo 'Note: escape any @ symbols with \ ; PUBLIC_URL if supplied other than with keyword "default" must have "http://" prefix'
  echo 'the single param accepted by script: place holder to enable trigger of this help if called without any arg'
  exit 1
}

update_db_in_beanie() {
  cd ../generated || (echo "cd ../generated failed from dir: $PWD"; exit 1)
  BEANIE_DB_FILE=$(find . -name "*_beanie_database.py")
  LC_ALL=C perl -pi -e "s#$DEFAULT_MONGO_DB_URI#$MONGO_DB_URL#g" "$BEANIE_DB_FILE"
  #sed -i "s/$DEFAULT_MONGO_DB_URI/$MONGO_DB_URL/g" "$BEANIE_DB_FILE"
  cd - || (echo "cd - failed from dir: $PWD"; exit 1)
  echo "Updated default mongo-db uri: $DEFAULT_MONGO_DB_URI to: $MONGO_DB_URL"
}

validate_and_update_uri() {
  if [[ $( tr '[:upper:]' '[:lower:]' <<<"$PUBLIC_URL" ) != http://* ]]; then
    echo "incorrectly formatted uri passed, expected uri prefixed with http:// got: $PUBLIC_URL"
    exit 1
  else
    # set API_PUBLIC_URL in file in web-ui/src/constants.js to "static" URL of Fast API server
    cd ../web-ui/src || (echo "cd ../web-ui/src failed from dir: $PWD"; exit 1)
    CONSTANT_JS_FILE="constants.js"
    if test -f "$CONSTANT_JS_FILE"; then
      echo "$CONSTANT_JS_FILE found, updating file with provided URI: $PUBLIC_URL"
      LC_ALL=C perl -pi -e "s#$DEFAULT_API_PUBLIC_URL#$PUBLIC_URL#g" $CONSTANT_JS_FILE
    fi
    cd - || (echo "cd - failed from dir: $PWD"; exit 1)
    echo "Updated default uri: $DEFAULT_URI to: $PUBLIC_URL"
  fi
}

install_dev() {
  if [ ! -d "../web-ui" ]; then
    echo "Web project does not exist. Run 'build_web_project' to build the web project"
    exit 1
  fi
  cd ../web-ui
  npm install
  npm install react-json-view -f
  cd - || (echo "cd - failed from dir: $PWD"; exit 1)
  echo "Installed npm packages."
}

install_prod() {
  install_dev
  if [[ $PUBLIC_URL == "default" ]]; then
    PUBLIC_URL=$DEFAULT_API_PUBLIC_URL
  fi
  # set PUBLIC_URL to "static" URL of Fast API server
  export PUBLIC_URL=$PUBLIC_URL/static
  npm run build
  cd - || (echo "cd - failed from dir: $PWD"; exit 1)
  # cleanup the previous builds and copy the build distribution to static and templates directory
  rm -rf static/* templates/*
  cp -pr ../web-ui/build/* static/.
  mv static/index.html templates/index.html
  echo "Build distribution created and copied to static and templates directory"
}

launch_dev() {
  export DEBUG=1
  python launch_beanie_fastapi.py &
  echo "FastAPI project starting in background."
  if [ ! -d "../web-ui" ]; then
    echo "Web project does not exist. Run 'build_web_project' to build the web project"
    exit 1
  fi
  cd ../web-ui
  if [ ! -d "node_modules" ]; then
    echo "node_modules does not exist. Run launch_web_project with INSTALL=<non-zero> to install the project first"
    exit 1
  fi
  npm start &
  echo "React project starting in background"
  cd - || (echo "cd - failed from dir: $PWD"; exit 1)
}

launch_prod() {
  python launch_beanie_fastapi.py &
  echo "FastAPI project starting in background."
}

run() {
  if [[ "$MONGO_DB_URL" != "default" ]] ; then
    update_db_in_beanie
  fi
  if [[ $PUBLIC_URL != "default" ]] ; then
    validate_and_update_uri
  fi

  if [[ $DEPLOY == "dev" ]]; then
    if [[ $INSTALL != "0" ]] ; then
      echo "Script mode: install & launch Dev"
      install_dev
    else
      echo "Script mode: launch Dev"
    fi
    launch_dev
  elif [[ $DEPLOY == "prod" ]]; then
    if [[ $INSTALL != "0" ]] ; then
      echo "Script mode: install & launch Prod"
      install_prod
    else
      echo "Script mode: launch Prod"
    fi
    launch_prod
  else
    echo "unexpected parameter values found in DEPLOY: $DEPLOY, unable to proceed"
    how_to_use
    exit 1
  fi
}

#if [ "$#" -lt 1 ] ; then
#  how_to_use
#else
#  run
#fi

run

# install notes (execute on execution server - external packaging TBD)
# configure fastapi url in variable API_ROOT_URL of file web-ui/src/constants.js (used for dev and prod both)
# update mongo DB URL in *_beanie_database.py
# go to web-ui folder and install npm dependencies
#cd web-ui
#npm install  # everytime any project file changes - this can be simplified TBD
# some dependencies are not supported by react-18 and thus we need to force install them:
#npm install react-json-view  -f

# usage notes:
# 1. In web in Dev / Debug mode (schema is serviced via react dev server):
# - API_PUBLIC_URL in file in web-ui/src/constants.js is already set to : 'http://127.0.0.1:3000'
#   - 3K is default react port - upon startup confirm exact port

# additional install for prod mode:
# To start web in Prod mode (schema is serviced via fast-api server):
# - set API_PUBLIC_URL in file in web-ui/src/constants.js to "static" URL of Fast API server
# - export PUBLIC_URL=http://127.0.0.1:8000/static
# - from web-ui dir , npm run build  # creates a build folder inside the Web-UI
# - copy content generated in the build folder from above step to "static" folder of fast-api
# cp -r build/* ../scripts/static/.
# move index.html to templates folder
# mv ../scripts/static/index.html ../scripts/templates/.

# run notes All:
# - run mongo
# - export DEBUG=1   # only in debug mode (Windows: set DEBUG=1)
# - run launch fast api script

# prod only:
# visit : http://127.0.0.1:8000/template_project_name

# additional run notes when running UI in Dev/Debug mode Only
# go inside web-ui directory and run:
# - npm start


# gotchas :
# 1. proto file with comment containing ' will break UI (generator needs fix)
# 2. only for dependent widget , the field name should be direct snake case of type name (UI depends on that)
# 3. don't forget export DEBUG=1 if starting via NPM