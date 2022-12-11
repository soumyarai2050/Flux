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
