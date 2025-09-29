#!/bin/bash

function usage {
    echo "usage: ./add_plugin <plugin_dir_name> <plugin_name>"
    echo "  <plugin_dir_name>: Name of directory to be generated in /PyCodeGenEngine directory to hold new plugin."
    echo "                     plugin_dir_name must be in Capitalised Camel Case, e.g., 'CamelCase'"
    echo "  <plugin_name>: Plugin name to be used in new plugin script as generated plugin file name and plugin class name."
    echo "                     plugin_name must be in Snake Case, e.g., 'snake_case'"
    exit 1
    }

if [ "$1" != "" ] && [ "$2" != "" ] ; then
    SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
    PY_CODE_GEN_ENGINE_DIR=$SCRIPT_DIR
    SAMPLE_PLUGIN_DIR="PluginTemp"
    PLUGIN_FILE_NAME="$2.py"
    mkdir -p "$PY_CODE_GEN_ENGINE_DIR/$1"
    cd "$PY_CODE_GEN_ENGINE_DIR/$1" || (echo "cd $PY_CODE_GEN_ENGINE_DIR/$1 failed"; exit 1)
    cp -pr "$PY_CODE_GEN_ENGINE_DIR"/$SAMPLE_PLUGIN_DIR/. .
    mv "template_plugin.py" "$PLUGIN_FILE_NAME"
    PLUGIN_CLASS_NAME=$(sed -r 's/(^|_)(\w)/\U\2/g' <<< "$2")
    sed -i -e "s/TemplatePlugin/$PLUGIN_CLASS_NAME/g" "$PLUGIN_FILE_NAME"
    sed -i -e "s/temp_plugin/$2/g" "$PLUGIN_FILE_NAME"
    chmod +x "$PLUGIN_FILE_NAME"
    echo "Created Plugin $2 in $PY_CODE_GEN_ENGINE_DIR/$1"
    TEMPLATE_SCRIPTS_DIR=$(dirname "$PY_CODE_GEN_ENGINE_DIR")/CodeGenProjects/template_scripts
    cd "$TEMPLATE_SCRIPTS_DIR" || (echo "cd $TEMPLATE_SCRIPTS_DIR from $PWD failed"; exit 1)
    cp "gen_template_plugin.py" "gen_$2.py"
    sed -i -e "s/template_plugin/$2/g" "gen_$2.py"
    sed -i -e "s/temp_plugin_dir/$1/g" "gen_$2.py"
    echo "Created plugin output generator template for $2 in $PWD"
else
    usage
fi
