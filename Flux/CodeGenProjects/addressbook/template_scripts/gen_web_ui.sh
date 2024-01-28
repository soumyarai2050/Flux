#!/bin/bash
set -e
# 1. copy web-ui from template_web-ui folder
# 2. copy and execute template_scripts helper script in web-ui folder to prepare web-ui for project
#    - search_replace template default project name with actual project name inferring project name from project directory name
#    - search and replace template default model service with inferring actual model service name form project model
# 4. remove  helper_gen_script.sh
if [ $# -lt 1 ] ; then
  cp -pr ../../../../template_web-ui ../.
  mv ../template_web-ui ../web-ui
  cd ../web-ui
  cp -p ../../../template_scripts/helper_gen_script.sh .
  source helper_gen_script.sh
  # its dirty (self replacements) next run will get it fresh from templates (all subsequent runs) - delete
  rm -f helper_gen_script.sh
  cd -  # back to script folder
else
  cp -pr ../../../../template_web-ui ../temp_web-ui
  cd ../temp_web-ui
  cp -p ../../../template_scripts/helper_gen_script.sh .
  source helper_gen_script.sh
  # its dirty (self replacements) next run will get it fresh from templates (all subsequent runs) - delete
  rm -f helper_gen_script.sh
  # overwrite new acquired files
  cd - # back to script folder
  cd ..
  rsync -a -v temp_web-ui/ web-ui/
  rm -rf temp_web-ui
  cd -  # back to script folder
fi
