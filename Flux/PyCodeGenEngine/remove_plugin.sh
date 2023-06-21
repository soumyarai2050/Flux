#!/bin/bash

function usage {
    echo "usage: ./remove_plugin <plugin_dir_name> <plugin_name>"
    echo "  <plugin_dir_name>: Name of directory to be deleted in /PyCodeGenEngine directory that holds plugins."
    echo "                     plugin_dir_name must be in Capitalised Camel Case, e.g., 'CamelCase'"
    echo "  <plugin_name>: Plugin name to be used in deleting generated plugin file and plugin output generator file."
    echo "                     plugin_name must be in Snake Case, e.g., 'snake_case'"
    exit 1
    }

if [ "$1" != "" ] && [ "$2" != "" ] ; then
	PY_CODE_GEN_ENGINE_DIR=$PWD
	SAMPLE_PLUGIN_DIR="PluginTemp"
	PLUGIN_FILE_NAME="$2.py"
  rm -r "$1"
	echo "Deleted Plugin Dir /$1"
	cd ../"CodeGenProjects/template_scripts" || (echo "cd ../CodeGenProjects/template_scripts from $PWD failed"; exit 1)
	rm "gen_$2.py"
  echo "Deleted plugin output generator template for $2 in $PWD"
	cd "$PY_CODE_GEN_ENGINE_DIR" || (echo "cd $PY_CODE_GEN_ENGINE_DIR failed"; exit 1)
else
    usage
fi