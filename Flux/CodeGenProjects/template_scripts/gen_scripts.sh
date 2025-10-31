#!/bin/bash
set -e
# 1. copy scripts from template_scripts folder
# 2. execute helper script to prepare project scripts:
#    - search_replace template project name with actual project name inferring project name from project directory name
#    - search and replace template project model service name with inferring actual model service name form project model
# 4. remove helper_gen_script.sh, subsequent iterations getting it again while copying all scripts from template folder

cp -p ../../template_scripts/* .
source helper_gen_script.sh
# its dirty (self replacements) next run will get it fresh from templates (all subsequent runs) - delete
rm -f helper_gen_script.sh
cd ..
PROJECT_NAME=${PWD##*/}          # assign project name to a variable
cd - > /dev/null
# Create project-specific symlinks for launch scripts
ln -sf launch_msgspec_fastapi.py "${PROJECT_NAME}_launch_msgspec_fastapi.py"
ln -sf launch_msgspec_fastapi.py "${PROJECT_NAME}_launch_msgspec_fastapi_view.py"