#!/bin/bash
set -e
if ! command -v gsed &> /dev/null
then
    echo "gsed could not be found, defaulting to sed"
    shopt -s expand_aliases
    alias gsed="sed"
fi


cd ..
PROJECT_NAME=${PWD##*/}          # to assign to a variable
PROJECT_NAME=${PROJECT_NAME:-/}        # to correct for the case where PWD=/
cd -
cd ../model
SERVICE_NAME=$(ls | grep service.proto | cut -d . -f 1)
cd -
echo "replacing any text occurrence of: template_project_name with: $PROJECT_NAME in template scripts"
find . -type f -exec gsed -i -E "s#template_project_name#$PROJECT_NAME#g" {} +
echo "replacing any text occurrence of: template_model_service with: $SERVICE_NAME in template scripts"
find . -type f -exec gsed -i -E "s#template_model_service#$SERVICE_NAME#g" {} +
# reverse this file replacements
gsed -i -E "s#$PROJECT_NAME#template_project_name#g" gen_scripts.sh
gsed -i -E "s#$SERVICE_NAME#template_model_service#g" gen_scripts.sh
