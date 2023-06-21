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
	PY_CODE_GEN_ENGINE_DIR=$PWD
	SAMPLE_PLUGIN_DIR="PluginTemp"
	PLUGIN_FILE_NAME="$2.py"
  mkdir "$1"
	cd "$1" || (echo "cd $1 failed"; exit 1)
	cp -pr "$PY_CODE_GEN_ENGINE_DIR"/$SAMPLE_PLUGIN_DIR/. .
	mv "template_plugin.py" "$PLUGIN_FILE_NAME"
	PLUGIN_CLASS_NAME=$(gsed -r 's/(^|_)(\w)/\U\2/g' <<< "$2")
  gsed -i -e "s/TemplatePlugin/$PLUGIN_CLASS_NAME/g" "$PLUGIN_FILE_NAME"
  gsed -i -e "s/temp_plugin/$2/g" "$PLUGIN_FILE_NAME"
  cd - || (echo "cd - failed from dir $PWD"; exit 1)
	echo "Created Plugin $2 in /$1"
	cd ../"CodeGenProjects/template_scripts" || (echo "cd ../CodeGenProjects/template_scripts from $PWD failed"; exit 1)
	cp "gen_template_plugin.py" "gen_$2.py"
  gsed -i -e "s/template_plugin/$2/g" "gen_$2.py"
  gsed -i -e "s/temp_plugin_dir/$1/g" "gen_$2.py"
  echo "Created plugin output generator template for $2 in $PWD"
	cd "$PY_CODE_GEN_ENGINE_DIR" || (echo "cd $PY_CODE_GEN_ENGINE_DIR failed"; exit 1)
else
    usage
fi