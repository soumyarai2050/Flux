#!/bin/bash
set -e
# we are in script DIR
START_DIR=$PWD
cd ../../../PyCodeGenEngine/FluxCodeGenCore
rm -f flux_options_pb2.py ui_core_pb2.py flux_utils_pb2.py
cd -
cd ..
# clean generated
cd generated
find . -type f ! \( -name "data.py" -o -name "forward_notification_ws_server.py" -o -name "get_all_from_ws_client.py" -o -name "get_from_ws_client.py" \) -print0 | xargs -0 -n1 rm
cd -
rm -rf web-ui
rm -rf scripts/static and scripts/templates
#Back to dir where we started
cd "$START_DIR"