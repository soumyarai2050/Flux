#!/bin/bash
set -e
# 1. copy web-ui from template_web-ui folder
# 2. copy and execute template_scripts helper script in web-ui folder to prepare web-ui for project
#    - search_replace template default project name with actual project name inferring project name from project directory name
#    - search and replace template default model service with inferring actual model service name form project model
# 4. remove  helper_gen_script.sh

cp -pr ../../template_web-ui ../.
mv ../template_web-ui ../web-ui
cd ../web-ui
cp -p ../../template_scripts/helper_gen_script.sh .
source helper_gen_script.sh
# its dirty (self replacements) next run will get it fresh from templates (all subsequent runs) - delete
rm -f helper_gen_script.sh
cd -  # back to script folder
