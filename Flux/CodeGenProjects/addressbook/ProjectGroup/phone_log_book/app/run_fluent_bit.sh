#!/usr/bin/env bash

# Get the directory in which this script resides
cd ../..
SCRIPT_DIR="$(pwd)"
export FLUX_CODEGEN_BASE_DIR="$SCRIPT_DIR"
export HOST="127.0.0.1"
cd - || exit

# ensuring db state dir exists
mkdir -p "${HOME}/fluent-bit/state/"

DEBUG_MODE="1"    # make it 1 to enable debug mode, any other value for normal run
if [ $DEBUG_MODE -eq "1" ]
then
  export FILTER_LOG_LVL="^(DEBUG|INFO|DB|WARNING|ERROR|CRITICAL|TIMING|Error|Exception)$"
else
  export FILTER_LOG_LVL="^(DB|WARNING|ERROR|CRITICAL|TIMING|Error|Exception)$"
fi

echo "FLUX_CODEGEN_BASE_DIR=$FLUX_CODEGEN_BASE_DIR"
echo "FILTER_LOG_LVL=$FILTER_LOG_LVL"
/opt/fluent-bit/bin/fluent-bit -c ./../data/fluent-bit.conf
