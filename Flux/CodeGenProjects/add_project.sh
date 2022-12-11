#!/bin/bash
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

START_DIR=$PWD
mkdir "$1"
cd "$1" || (echo "cd $1 failed"; exit 1)
cp -pr "$PWD"/../"$ORIG_GEN_PRJ"/. . || (echo "cp failed!"; exit 1)
if [ "$COPY_MODEL" = false ] ; then
  rm -rf model/*
fi
rm -rf output/*
rm -rf generated_scripts/*
rm -rf project/*
rm -rf web_static/*
rm -rf temp/*
find . \( -name .DS_Store -o -name .git -o -name .svn \) -print0 | xargs -0 rm -rf
# replace any reference to old prj name with new prj name
echo "replacing any text occurrence of: $2 with: $1 in new project"
find . -type f -print0 | xargs -0 perl -pi -e "s#$2#$1#g"
cd "$START_DIR" || (echo "cd $START_DIR failed"; exit 1)
echo "Created Project $1 from $ORIG_GEN_PRJ"
