#!/bin/bash
set -e
# we are in script DIR
START_DIR=$PWD
cd ../../../PyCodeGenEngine/FluxCodeGenCore
rm -f flux_options_pb2.py ui_core_pb2.py flux_utils_pb2.py trade_core_pb2.py ui_option_utils_pb2.py
rm -f flux_options.pb.cc flux_options.pb.h
rm -f flux_utils.pb.cc flux_utils.pb.h
rm -f ui_core.pb.cc ui_core.pb.h
rm -f trade_core.pb.cc trade_core.pb.h
rm -f ui_option_utils.pb.cc ui_option_utils.pb.h
cd -  # back in script dir
cd .. # parent of script dir
# clean generated
cd generated
find . -type f ! \( -name "data.py" -o -name "forward_notification_ws_server.py" -o -name "get_all_from_ws_client.py" -o -name "get_from_ws_client.py" \) -print0 | xargs -0 -n1 rm
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
