#!/bin/bash

# Define the log file
pair_start_engine_log_file="$1"

# Loop through the passed arguments (log entries) and append them to the log file
for log_entry in "${@:2}"; do
    # Print log entry to console
    echo "$log_entry"

    # Append log entry to the log file in append mode
    echo "$log_entry" >> "$pair_start_engine_log_file"
done
