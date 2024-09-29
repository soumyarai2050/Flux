#!/bin/bash
set -e

# Generates ui generated files for all projects and also copies them in web-ui dir of each project

project_names=(
    "dept_book"
    "mobile_book"
    "post_book"
    "log_book"
    "street_book"
    "photo_book"
    "basket_book"
    "phone_book"    # phone_book is parent project importing some other projects' generated files so must be generated at last
)

for project_name in "${project_names[@]}"; do
    cd "ProjectGroup/${project_name}/scripts/"
    if [ -e "gen_js_layouts.py" ]; then
        python gen_js_layouts.py
        echo "triggered $PWD/gen_js_layouts.py"
        cd -
        cd "ProjectGroup"
        ./gen_web_project.sh "${project_name}"
        cd -
    else
        echo "$PWD/gen_js_layouts.py does not exist."
        cd -
    fi
done
