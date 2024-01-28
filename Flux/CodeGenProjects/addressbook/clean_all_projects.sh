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
    if [ -e "clean-web-project.sh" ]; then
        ./clean-web-project.sh
        echo "triggered $PWD/clean-web-project.sh"
    else
        echo "$PWD/clean-web-project.sh does not exist."
    fi
    cd -
done
