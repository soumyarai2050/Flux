#!/bin/bash
set -e
how_to_use()
{
  echo "Usage: $0 -p|--project {New-Project-Name} [-ep|--existing_project <Existing-Project-Name>] [with_model] [-epg|--existing_project_group <Project-Group-Name>] [-pg|--project_group <Project-Group-Name>] "
  echo "Creates new project and sets up same as existing project; if 'with_model' is supplied, model form existing project is copied as-is, just package name is changed to new project name"
  echo "if 'existing_project_group' is supplied only, it creates new project in the same project group"
  echo "if both 'existing_project_group' and 'project_group' is supplied, it creates the new project group and creates the project in new project_group"
  exit 1
}

find_rename_regex() (
  set -eu
  find_and_replace="$1"
  PATH="$(echo "$PATH" | gsed -E 's/(^|:)[^\/][^:]*//g')" \
  LC_ALL=C find . -depth -execdir rename "${2:--n}" "s/${find_and_replace}" '{}' \;
)

if [ "$#" -lt 1 ] ; then
  how_to_use
fi

COPY_MODEL=false
# Parse command line options
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -p|--project)
            PRJ="$2"
            shift  # Consume the next argument as well
            ;;
        -ep|--existing_project)
            ORIG_GEN_PRJ="$2"
            shift  # Consume the next argument as well
            ;;
        -pg|--project_group)
            PRJ_GRP="$2"
            shift
            ;;
        -epg|--existing_project_group)
            ORIG_PRJ_GRP="$2"
            shift
            ;;
        with_model)
            COPY_MODEL=true
            ;;
        -h|--help)
            how_to_use
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            how_to_use
            exit 1
            ;;
    esac
    shift
done

START_DIR=$PWD
TESTS_DIR="$START_DIR/../../tests/CodeGenProjects"
if [  "$ORIG_GEN_PRJ" == "" ] ; then
  echo "Creating new project with CodeGenProjectsCore - no template project provided as second param!"
  ORIG_GEN_PRJ="CodeGenProjectsCore"
fi
PRJ_DIR=$PRJ
ORIG_GEN_PRJ_DIR=$ORIG_GEN_PRJ
ORIG_PRJ_TEST_DIR=$TESTS_DIR
PRJ_TEST_DIR=$TESTS_DIR
if [ -n "$ORIG_PRJ_GRP" ]; then
  ORIG_GEN_PRJ_DIR="$ORIG_PRJ_GRP/ProjectGroup/$ORIG_GEN_PRJ"
  ORIG_PRJ_TEST_DIR="$TESTS_DIR/$ORIG_PRJ_GRP/ProjectGroup"
  PRJ_DIR="$ORIG_PRJ_GRP/ProjectGroup/$PRJ"
  PRJ_TEST_DIR="$TESTS_DIR/$ORIG_PRJ_GRP/ProjectGroup"
fi
if [ -n "$PRJ_GRP" ]; then
  PRJ_DIR="$PRJ_GRP/ProjectGroup/$PRJ"
  PRJ_TEST_DIR="$TESTS_DIR/$PRJ_GRP/ProjectGroup"
  if [ -d "$PRJ_GRP" ]; then
    echo "Project Group: $PRJ_GRP already exists. Ignoring copying plugins"
  else
    mkdir -p "$PRJ_GRP"
    cd "$PRJ_GRP"
    rsync -av --exclude="ProjectGroup" "$START_DIR"/"$ORIG_PRJ_GRP"/. . || (echo "rsync failed!"; exit 1)
    mkdir -p ProjectGroup
    cp -pr "$START_DIR/$ORIG_PRJ_GRP/ProjectGroup/gen_web_project.sh" ProjectGroup/.
    echo "replacing any text occurrence of: $ORIG_PRJ_GRP with: $PRJ_GRP in new project"
    find . -type f -exec gsed -i -E "s#$ORIG_PRJ_GRP#$PRJ_GRP#g" {} +
    cd -
  fi
  if [ ! -d "$PRJ_TEST_DIR" ]; then
    mkdir -p "$PRJ_TEST_DIR"
    cp -pr "$ORIG_PRJ_TEST_DIR/conftest.py" $PRJ_TEST_DIR/.
  fi
fi
if [ -d "$PRJ_DIR" ] ; then
  echo "Can't create new project with name: $PRJ, Directory: $PRJ_DIR already exists!"
  how_to_use
fi

if ! command -v gsed &> /dev/null
then
    echo "gsed could not be found, defaulting to sed"
    shopt -s expand_aliases
    alias gsed="sed"
fi

mkdir -p "$PRJ_DIR"
cd "$PRJ_DIR" || (echo "cd $PRJ_DIR failed"; exit 1)
rsync -av --exclude="node_modules" "$START_DIR"/"$ORIG_GEN_PRJ_DIR"/. . || (echo "rsync failed!"; exit 1)
# copy the old prj tests inside new prj
if [ -d "$ORIG_PRJ_TEST_DIR/$ORIG_GEN_PRJ" ]; then
  cp -pr "$ORIG_PRJ_TEST_DIR/$ORIG_GEN_PRJ" . || (echo "cp failed!"; exit 1)
fi
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
echo "replacing any text occurrence of: $ORIG_GEN_PRJ with: $PRJ in new project"
find_rename_regex "$ORIG_GEN_PRJ/$PRJ/g" -v
find . -type f -exec gsed -i -E "s#$ORIG_GEN_PRJ#$PRJ#g" {} +
NewProjectCamelCaseName=$(echo "$PRJ" | gsed -r 's/(^|_)([a-z])/\U\2/g' | xargs)
ExistingProjectCamelCaseName=$(echo "$ORIG_GEN_PRJ" | gsed -r 's/(^|_)([a-z])/\U\2/g' | xargs)
NewProjectTitleCaseName=$(echo "$PRJ" |  gsed -E "s/(^|_)([a-z])/ \u\2/g" | xargs)  # xargs cleans up extra spaces
ExistingProjectTitleCaseName=$(echo "$ORIG_GEN_PRJ" |  gsed -E "s/(^|_)([a-z])/ \u\2/g" | xargs)  # xargs cleans up extra spaces
echo "replacing any CapitalizedCamelCase text occurrence of: $ExistingProjectCamelCaseName with: $NewProjectCamelCaseName in new project"
find_rename_regex "$ExistingProjectCamelCaseName/$NewProjectCamelCaseName/g" -v
find . -type f -exec gsed -i -E "s#$ExistingProjectCamelCaseName#$NewProjectCamelCaseName#g" {} +
if [ "$ExistingProjectCamelCaseName" != "$ExistingProjectTitleCaseName" ]; then
  echo "replacing any Title Case Text occurrence of: $ExistingProjectTitleCaseName with: $NewProjectTitleCaseName in new project"
  find_rename_regex "$ExistingProjectTitleCaseName/$NewProjectTitleCaseName/g" -v
  find . -type f -exec gsed -i -E "s#$ExistingProjectTitleCaseName#$NewProjectTitleCaseName#g" {} +
fi
if [ -n "$ORIG_PRJ_GRP" ] && [ -n "$PRJ_GRP" ]; then
  echo "replacing any text occurrence of: $ORIG_PRJ_GRP with: $PRJ_GRP in new project"
  find . -type f -exec gsed -i -E "s#$ORIG_PRJ_GRP#$PRJ_GRP#g" {} +
fi
if [ -d "$PRJ" ]; then
  mv "$PRJ" "$PRJ_TEST_DIR/." || (echo "mv failed!"; exit 1)
fi
cd "$START_DIR" || (echo "cd $START_DIR failed"; exit 1)
echo "Created Project $PRJ from $ORIG_GEN_PRJ"
