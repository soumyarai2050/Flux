# Scripts Document

## Windows build / execute Requirements:
1. Install WSL2 if using windows with ubuntu distribution
2. Install protoc-compiler using below command in ubuntu<br>
    `sudo apt install protobuf-compiler` <br>
Note: Test is done in version *libprotoc 3.12.4*
3. Install mongodb, steps available in 
https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/#install-mongodb-community-edition-on-ubuntu <br>
If you face - Depends on libssl1.1 but it is not installable, please follow first answer 
on this link: https://askubuntu.com/questions/1403619/mongodb-install-fails-on-ubuntu-22-04-depends-on-libssl1-1-but-it-is-not-insta <br>
- To run mongo first create mongo-dir directory(with any name) 
somewhere and 2 more directories in mongo-dir, data and logs. 
Add mongo.logs file in logs dir (with any name). Now run this cmd 
in dir where mongo-dir exists, `mongod --logpath=mongo-dir/logs/mongo.log --dbpath=mongo-dir/data &`
4. Check if python is installed in wsl. If python3 is present and python is not working then run:
    `sudo ln -s /usr/bin/pyhton3.x /usr/bin/python`
5. Clone FluxCodeGenEngine and PythonCore parallely.
6. If you are in windows you need to run below commands in your
FluxCodeGenEngine/Flux dir, <br>
    `find . -name "*.py" | xargs dos2unix` <br>
    `find . -name "*.sh" | xargs dos2unix` <br>
Note: If dos2unix is not installed, use `sudo apt install dos2unix` 
to install it.
7. Now install required python modules by runnig below cmd in 
FluxCodeGenEngine/Flux dir, <br>
    `pip install -r requirements.txt` <br>
Note: If pip is not installed, run `sudo apt install python3-pip`
8. Now go to FluxCodeGenEngine/Flux/CodeGenProjects/pair_strat_engine/scripts
dir and run `./build_web_project.sh` to generate server and UI files.
9. To launch fastapi server, run `python launch_beanie_fastapi.py`

### Key Note: 
1. Any Generated file when needs to be moved to other directory,
if contains fully qualified import path of any other file, needs to 
be changed according to new location.

## JSON Generators
### 1. gen_json_schema.py
Generates JSON schema file using proto schema.
#### run: `python gen_json_schema.py`

### 2. gen_json_sample.py
Generates JSON sample with random data using proto schema.
#### run: `python gen_json_sample.py`

## Js Generators
### 3. gen_js_layout.py
Generates JS-React layout using proto schema.
#### run: `python gen_js_layout.py`

## Pydantic Model Generators
### 4. gen_cached_pydentic_model.py
Generates cached pydantic models using proto schema.
#### run: `python gen_cached_pydantic_model.py`

### 5. gen_beanie_model.py
Generates beanie models using proto schema.
#### run: `python gen_beanie_model.py`

## FastApi Generators
### 6. gen_cached_fastapi.py
Generates cached-fastapi app script dependent in models 
generated using [gen_cache_pydentic_model.py](#4-gen_cache_pydentic_modelpy)
#### run: `python gen_cached_fastapi.py`

### 7. gen_beanie_fastapi.py
Generates beanie-fastapi app script dependent in models 
generated using [gen_beanie_model.py](#5-gen_beanie_modelpy)
#### run: `python gen_beanie_fastapi.py`

### 8. gen_cached_beanie_fastapi.py
Generates beanie-fastapi app script dependent in models 
generated using [gen_cache_beanie_model.py](#8-gen_cached_beanie_fastapipy)
#### run: `python gen_cached_beanie_fastapi.py`

## Launchers
### 9. launch_cache_fastapi.py
Launches generated cached-fastapi api
#### run: `python launch_cache_fastapi.py`

### 10. launch_beanie_fastapi.py
Launches generated beanie-fastapi api
#### run: `python launch_beanie_fastapi.py`

### 11. launch_cached_beanie_fastapi.py
Launches generated cached-beanie-fastapi api
#### run: `python launch_cached_beanie_fastapi.py`

## Environment variable
#### 1. ENUM_TYPE: 
Supported types: "str_enum" and "int_enum" <br>
*Usage*: Use to set which type of enums should be generated
in pydantic model by plugin

#### 2. OUTPUT_FILE_NAME_SUFFIX:
*Usage*: Suffix to be added in generated files of plugins.
Input proto file's name is suffixed with the value of this
variable as default approach in plugins

#### 3. PLUGIN_FILE_NAME:
*Usage*: Name of the plugin to be used to generate output

#### 4. INSERTION_IMPORT_FILE_NAME:
*Usage*: Name of the file having insertion point for imports
required in plugin to generate output

#### 5. PB2_IMPORT_GENERATOR_PATH:
*Usage*: Name of the sub-plugin used to add required imports 
in insertion import file used to generate output using plugin

#### 6. RESPONSE_FIELD_CASE_STYLE
snake or camel supported
*Usage*: Used by pydantic model generator to set model depending 
on the required response case style of the model, snake case
or camel case

#### 7. DEBUG_SLEEP_TIME:
takes number of seconds
*Usage*: Required to set timer of sleep before running plugin
to attach debugger to the plugin process

#### 8. RELOAD:
*Usage*: bool to add reload attribute to uvicorn fastapi launch

#### 9. HOST: 
*Usage*: Host will be used across the server and client for 
CRUD operations

#### 10. PORT:
*Usage*: Like Host, Port will also be used across the 
server and client for CRUD operations


## Common Errors
1. If flux_options.proto file or it's pb2 file raises some
option pertaining error, regenerating pb2 file of 
flux_option.proto can solve it.
2. Endpoint should end with /
3. If behind proxy, set no proxy to make request to APIs