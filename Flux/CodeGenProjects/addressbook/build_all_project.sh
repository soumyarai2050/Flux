#!/bin/bash
set -e

file_paths=(
    "ProjectGroup/dept_book/scripts/"
    "ProjectGroup/mobile_book/scripts/"
    "ProjectGroup/post_book/scripts/"
    "ProjectGroup/log_book/scripts/"
    "ProjectGroup/basket_book/scripts/"
    "ProjectGroup/street_book/scripts/"
    "ProjectGroup/photo_book/scripts/"
    "ProjectGroup/phone_book/scripts/"     # phone_book is parent project importing some other projects' generated files so must be generated at last
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
