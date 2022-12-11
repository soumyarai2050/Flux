#!/bin/bash
set -e

START_DIR=$PWD
cd ..
# clean output
cd output
find . -type f ! \( -name "data.py" -o -name "forward_notification_ws_server.py" -o -name "get_all_from_ws_client.py" -o -name "get_from_ws_client.py" \) -print0 | xargs -0 -n1 rm
cd -

rm -f web-ui/public/schema.json
rm -rf web-ui/src/components/Layout.jsx
rm -f web-ui/src/widgets/*
rm -f web-ui/src/projectSpecificUtils.js web-ui/src/store.js
# delete web-ui/src/features/* except schemaSlice.js
cd web-ui/src/features/
find . ! -name 'schemaSlice.js' -type f -exec rm -f {} +
cd -
rm -rf scripts/static and scripts/templates

# rollback web-ui/package.json (discard local changes)
cd web-ui
git checkout package.json
cd -

# rollback web-ui/src/constants.js (discard local changes)
cd web-ui/src
git checkout constants.js
cd -

rm -f web-ui/package-lock.json
rm -rf web-ui/build
rm -rf web-ui/node_modules

#Back to dir where we started
cd "$START_DIR"