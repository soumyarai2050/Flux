#!/usr/bin/env bash

# Get the directory in which this script resides
cd ../..
SCRIPT_DIR="$(pwd)"
export FLUX_CODEGEN_BASE_DIR="$SCRIPT_DIR"
cd - || exit

DEBUG_MODE="1"    # make it 1 ot enable debug mode
if [ $DEBUG_MODE -eq "1" ]
then
  export FILTER_LOG_LVL="^(DEBUG|INFO|DB|WARNING|ERROR|CRITICAL|TIMING)$"
else
  export FILTER_LOG_LVL="^(DB|WARNING|ERROR|CRITICAL|TIMING)$"
fi

echo "FLUX_CODEGEN_BASE_DIR=$FLUX_CODEGEN_BASE_DIR"
echo "FILTER_LOG_LVL=$FILTER_LOG_LVL"
sudo -E /opt/fluent-bit/bin/fluent-bit -c ./../data/fluent-bit.conf
