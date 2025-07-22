#!/bin/bash

# Run both scripts in the background

# Running View Server
export IS_VIEW_SERVER=1
python launch_msgspec_fastapi.py &
pid2=$!

sleep 2

# Running Main Server
unset IS_VIEW_SERVER    # Unset or reset for subsequent processes
python launch_msgspec_fastapi.py &
pid1=$!

trap "kill $pid1 $pid2 2>/dev/null; exit" SIGINT

wait
