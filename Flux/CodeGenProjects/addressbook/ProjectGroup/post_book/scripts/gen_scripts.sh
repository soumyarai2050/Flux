#!/bin/bash
set -e
# 1. copy scripts from root template_scripts folder avoiding 'gen_scripts.sh' file
# 2. copy scripts from project_group's template_scripts folder
# 3. execute helper script to prepare project scripts:
#    - search_replace template project name with actual project name inferring project name from project directory name
#    - search and replace template project model service name with inferring actual model service name form project model
# 4. remove helper_gen_script.sh, subsequent iterations getting it again while copying all scripts from template folder

find ../../../../template_scripts/* -type f ! -name 'gen_scripts.sh' ! -name 'build_web_project.sh' ! -name 'helper_gen_script.sh'  -exec cp -p {} . \;
cp -p ../../../template_scripts/* .
source helper_gen_script.sh
# its dirty (self replacements) next run will get it fresh from templates (all subsequent runs) - delete
rm -f helper_gen_script.sh