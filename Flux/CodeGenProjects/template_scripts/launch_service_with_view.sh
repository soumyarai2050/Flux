#!/bin/bash

# Run both scripts in the background
export IS_VIEW_SERVER=    # Unset or reset for subsequent processes
python launch_msgspec_fastapi.py &     # sees CONFIG_FILE_NAME as empty
pid1=$!

sleep 2

export IS_VIEW_SERVER=1
python launch_msgspec_fastapi.py &     # sees CONFIG_FILE_NAME=config1.yaml
pid2=$!

trap "kill $pid1 $pid2 2>/dev/null; exit" SIGINT

wait
