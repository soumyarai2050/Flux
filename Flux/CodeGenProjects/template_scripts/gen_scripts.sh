#!/bin/bash
set -e
# 1. copy scripts from template_scripts folder
# 2. execute helper script to prepare project scripts:
#    - search_replace pair_strat_engine with project_name inferring project name from project directory name
#    - search and replace strat_manager_service with inferring actual model service name form model
# 4. revert script prepare_project by copying over again this specific script from template folder

cp -p ../../template_scripts/* .
source helper_gen_script.sh
# its dirty (self replacements) next run will get it fresh from templates (all subsequent runs) - delete
rm -f helper_gen_script.sh
