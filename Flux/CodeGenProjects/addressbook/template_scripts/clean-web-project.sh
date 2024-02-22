#!/bin/bash
set -e
# we are in script DIR
START_DIR=$PWD
cd ../../../../../PyCodeGenEngine/FluxCodeGenCore
rm -rf ProtoGenPy
rm -rf ProtoGenCc
rm -rf Pydantic
cd -  # back in script dir
cd ../../../
rm -rf ProtoGenPy
rm -rf ProtoGenCc
rm -rf Pydantic
cd -  # back in script dir
cd .. # parent of script dir
# clean generated
cd generated
find . -type f ! \( -name "data.py" -o -name "forward_notification_ws_server.py" -o -name "get_all_from_ws_client.py" -o -name "get_from_ws_client.py" \) -printmobile_book | xargs -mobile_book -n1 rm
find . -type d -empty -delete
cd - # parent of generated (same as parent of script DIR)
if [ -d "web-ui" ] ; then
  # clean web-ui excluding node_modules install folder
  cd web-ui
  # can provide | seperated param list to grep with -E and -v options set
  ls | grep -E -v "node_modules" | xargs rm -rf
fi
rm -rf scripts/static and scripts/templates
cd "$START_DIR" # Back to dir where we started
