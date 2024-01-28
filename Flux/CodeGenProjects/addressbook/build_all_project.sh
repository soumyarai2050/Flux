#!/bin/bash
set -e

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
    if [ -e "build_web_project.sh" ]; then
        ./build_web_project.sh
        echo "triggered $PWD/build_web_project.sh"
        cd -
    else
        echo "$PWD/build_web_project.sh does not exist."
    fi
done
