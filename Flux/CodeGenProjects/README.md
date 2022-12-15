# Scripts Document

## First Step: 
In order to run below scripts, you need the required python modules
to be installed in your environment. To install them go to
root directory and run below cmd:

`
pip install -r requirements.txt
`

Also, Flux used protoc compiler to make use of proto models.
Please install that as well. Test is done in version *libprotoc 3.12.4*

Note: Any Generated file when needs to be moved to other directory,
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
*Usage*: 

#### 10. PORT:
*Usage*: 
