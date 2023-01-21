#!/bin/bash
set -e
how_to_use()
{
  echo "Usage: $0 {New-Project-Name} <Existing-Project-Name> <with_model>"
  echo "Creates new project and sets up same as existing project; if 'with_model' is supplied, model form existing project is copied as-is, just package name is changed to new project name"
  exit 1
}

if [ $# -lt 1 ] ; then
  how_to_use
elif [ -d "$1" ] ; then
  echo "Can't create new project with name: $1, Directory: $1 already exists!"
  how_to_use
fi
if [  "$2" == "" ] ; then
  echo "Creating new project with CodeGenProjectsCore - no template project provided as second param!"
  $2 = "CodeGenProjectsCore"
else
  ORIG_GEN_PRJ=$2
fi
if [  "$3" == "with_model" ] ; then
  COPY_MODEL=true
else
  COPY_MODEL=false
fi

if ! command -v gsed &> /dev/null
then
    echo "gsed could not be found, defaulting to sed"
    shopt -s expand_aliases
    alias gsed="sed"
fi

START_DIR=$PWD
mkdir "$1"
cd "$1" || (echo "cd $1 failed"; exit 1)
cp -pr "$PWD"/../"$ORIG_GEN_PRJ"/. . || (echo "cp failed!"; exit 1)
if [ "$COPY_MODEL" = false ] ; then
  rm -rf model/*
fi
rm -rf generated/*
rm -rf generated_scripts/*
rm -rf project/*
rm -rf web_ui
rm -rf temp/*
find . \( -name .DS_Store -o -name .git -o -name .svn \) -print0 | xargs -0 rm -rf
# replace any reference to old prj name with new prj name
echo "replacing any text occurrence of: $2 with: $1 in new project"
find . -type f -exec gsed -i -E "s#$2#$1#g" {} +
NewProjectCamelCaseName=$(echo "$1" | gsed -r 's/(^|_)([a-z])/\U\2/g' | xargs)
ExistingProjectCamelCaseName=$(echo "$2" | gsed -r 's/(^|_)([a-z])/\U\2/g' | xargs)
NewProjectTitleCaseName=$(echo "$1" |  gsed -E "s/(^|_)([a-z])/ \u\2/g" | xargs)  # xargs cleans up extra spaces
ExistingProjectTitleCaseName=$(echo "$2" |  gsed -E "s/(^|_)([a-z])/ \u\2/g" | xargs)  # xargs cleans up extra spaces
echo "replacing any CapitalizedCamelCase text occurrence of: $ExistingProjectCamelCaseName with: $NewProjectCamelCaseName in new project"
find . -type f -exec gsed -i -E "s#$ExistingProjectCamelCaseName#$NewProjectCamelCaseName#g" {} +
if [ "$ExistingProjectCamelCaseName" != "$ExistingProjectTitleCaseName" ]; then
  echo "replacing any Title Case Text occurrence of: $ExistingProjectTitleCaseName with: $NewProjectTitleCaseName in new project"
  find . -type f -exec gsed -i -E "s#$ExistingProjectTitleCaseName#$NewProjectTitleCaseName#g" {} +
fi
cd "$START_DIR" || (echo "cd $START_DIR failed"; exit 1)
echo "Created Project $1 from $ORIG_GEN_PRJ"
