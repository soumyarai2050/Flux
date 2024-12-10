#!/bin/bash
set -e

# we are in scripts folder
# test if web-ui present - if not present - generate gen_web_ui.sh
cd ..
PROJECT_NAME=${PWD##*/}          # assign project name to a variable
PROJECT_NAME=${PROJECT_NAME:-/}  # correct project name for case where PWD=/
if [ -d "web-ui" ] ; then
  echo "Can't create web-ui project, Directory already exists, updating instead"
  cd -  # back in script folder
  "$PWD"/gen_web_ui.sh "update"
  cd -  # restore PWD state to pre if state
else
  cd -  # back in script folder
  "$PWD"/gen_web_ui.sh
  cd -  # restore PWD state to pre if state
fi
cd - # back in script folder

# compiling root core proto files
cd ../../../../../PyCodeGenEngine/FluxCodeGenCore
python gen_core_proto_compile.py
cd - # back in script folder

# compiling project group core proto files
cd ../../../
python gen_core_proto_compile.py
cd - # back in script folder

mkdir -p  ../log
mkdir -p ../generated
mkdir -p ../web-ui/src/widgets
python gen_json_sample.py
python gen_msgspec_model.py
python gen_msgspec_fastapi.py
python gen_js_layouts.py
python gen_json_schema.py
python gen_executor_files.py

# cpp plugins
python gen_cpp_db_codec.py
python gen_cpp_constants.py
python gen_cpp_key_handler.py
python gen_cpp_project_includes.py
python gen_cpp_web_socket_server.py
python gen_cpp_shared_data_structure.py
python gen_cpp_json_to_object_plugin.py
python gen_cpp_object_to_json_plugin.py
python gen_cpp_data_structure_plugin.py
# NOTE: these plugins are not required. When needed - uncomment:
#python gen_web_socket_server_util.py
#python gen_cpp_web_socket_test.py
#python gen_cpp_get_str_from_enum_plugin.py
#python gen_cpp_proto2_model.py
#python gen_populate_random_values.py
#python gen_cpp_db_test.py
#python gen_cpp_web_client_test.py
#python gen_cpp_example_comments.py
#python gen_cpp_codec_test.py
#python gen_proto2_to_proto3.py
#python gen_cpp_build_and_run_test.py
#python gen_cpp_max_id_handler.py
#python gen_cpp_db_test_cpp_plugin.py
cd ../../
"$PWD"/gen_web_project.sh "$PROJECT_NAME"
