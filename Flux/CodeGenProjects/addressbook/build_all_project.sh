#!/bin/bash
set -e

file_paths=(
    "ProjectGroup/dept_book"
    "ProjectGroup/mobile_book"
    "ProjectGroup/post_book"
    "ProjectGroup/log_book"
    "ProjectGroup/street_book"
    "ProjectGroup/photo_book"
    "ProjectGroup/basket_book"
    "ProjectGroup/phone_book"    # phone_book is parent project importing some other projects' generated files so must be generated at last
)

for file_path in "${file_paths[@]}"; do
    # Checking and creating generated directory if doesn't exist already in project directories
    generated_dir="$file_path/generated"
    if [ ! -d "$generated_dir" ]; then
        mkdir -p "$generated_dir"
        echo "Directory $generated_dir created."
    else
        echo "Directory $generated_dir already exists."
    fi
done

for file_path in "${file_paths[@]}"; do
    cd "$file_path/scripts/"
    if [ -e "build_web_project.sh" ]; then
        ./build_web_project.sh
        echo "triggered $PWD/build_web_project.sh"
        cd -
    else
        echo "$PWD/build_web_project.sh does not exist."
        cd -
    fi
done
