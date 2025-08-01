#!/bin/bash
#set -e

file_paths=(
    "ProjectGroup/address_data_manager/scripts"
    "ProjectGroup/dept_book/scripts/"
    "ProjectGroup/mobile_book/scripts/"
    "ProjectGroup/post_book/scripts/"
    "ProjectGroup/log_book/scripts/"
    "ProjectGroup/street_book/scripts/"
    "ProjectGroup/photo_book/scripts/"
    "ProjectGroup/basket_book/scripts/"
    "ProjectGroup/phone_book/scripts/"
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
