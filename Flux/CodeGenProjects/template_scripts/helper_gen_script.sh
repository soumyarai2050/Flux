#!/bin/bash
set -e
if ! command -v gsed &> /dev/null
then
    echo "gsed could not be found, defaulting to sed"
    shopt -s expand_aliases
    alias gsed="sed"
fi


cd ..
NEW_PROJECT_NAME=${PWD##*/}          # to assign to a variable
NEW_PROJECT_NAME=${NEW_PROJECT_NAME:-/}        # to correct for the case where PWD=/
cd -
cd ../model
NEW_SERVICE_NAME=$(ls | grep service.proto | cut -d . -f 1)
cd -
EXISTING_PROJECT_NAME=template_project_name
EXISTING_SERVICE_NAME=template_model_service

NewProjectCamelCaseName=$(echo "$NEW_PROJECT_NAME" | gsed -r 's/(^|_)([a-z])/\U\2/g' | xargs)
ExistingProjectCamelCaseName=$(echo "$EXISTING_PROJECT_NAME" | gsed -r 's/(^|_)([a-z])/\U\2/g' | xargs)
NewProjectTitleCaseName=$(echo "$NEW_PROJECT_NAME" |  gsed -E "s/(^|_)([a-z])/ \u\2/g" | xargs)  # xargs cleans up extra spaces
ExistingProjectTitleCaseName=$(echo "$EXISTING_PROJECT_NAME" |  gsed -E "s/(^|_)([a-z])/ \u\2/g" | xargs)  # xargs cleans up extra spaces



echo "replacing any text occurrence of: $EXISTING_PROJECT_NAME with: $NEW_PROJECT_NAME in $PWD recursively"
find . -type f -exec gsed -i -E "s#$EXISTING_PROJECT_NAME#$NEW_PROJECT_NAME#g" {} +
echo "replacing any text occurrence of: $EXISTING_SERVICE_NAME with: $NEW_SERVICE_NAME in $PWD recursively"
find . -type f -exec gsed -i -E "s#$EXISTING_SERVICE_NAME#$NEW_SERVICE_NAME#g" {} +
echo "replacing any CapitalizedCamelCase text occurrence of: $ExistingProjectCamelCaseName with: $NewProjectCamelCaseName in $PWD recursively"
find . -type f -exec gsed -i -E "s#$ExistingProjectCamelCaseName#$NewProjectCamelCaseName#g" {} +
if [ "$ExistingProjectCamelCaseName" != "$ExistingProjectTitleCaseName" ]; then
  echo "replacing any Title Case Text occurrence of: $ExistingProjectTitleCaseName with: $NewProjectTitleCaseName in $PWD recursively"
  find . -type f -exec gsed -i -E "s#$ExistingProjectTitleCaseName#$NewProjectTitleCaseName#g" {} +
fi
