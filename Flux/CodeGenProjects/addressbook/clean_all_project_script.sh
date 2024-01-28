#!/bin/bash
#set -e

file_paths=(
    "ProjectGroup/dashboards/scripts/"
    "ProjectGroup/market_data/scripts/"
    "ProjectGroup/post_trade_engine/scripts/"
    "ProjectGroup/log_analyzer/scripts/"
    "ProjectGroup/strat_executor/scripts/"
    "ProjectGroup/pair_strat_engine/scripts/"
)

for file_path in "${file_paths[@]}"; do
    cd "$file_path"
    if [ -e "clean_scripts.sh" ]; then
        ./clean_scripts.sh
        echo "triggered $PWD/clean_scripts.sh"
        cd -
    else
        echo "$PWD/clean_scripts.sh does not exist."
    fi
done
