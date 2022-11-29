# Scripts Document

## JSON Generators
### 1. gen_json_schema.py
Generates JSON schema file using proto schema.

### 2. gen_json_sample.py
Generates JSON sample with random data using proto schema.

## Js Generators
### 3. gen_js_layout.py
Generates JS-React layout using proto schema.

## Pydantic Model Generators
### 4. gen_cache_pydentic_model.py
Generates cached pydantic models using proto schema.

### 5. gen_beanie_model.py
Generates beanie models using proto schema.

### 6. gen_cache_beanie_model.py
Generates cached beanie models using proto schema.

## FastApi Generators
### 7. gen_cached_fastapi.py
Generates cached-fastapi app script dependent in models 
generated using [gen_cache_pydentic_model.py](#4-gen_cache_pydentic_modelpy)

### 8. gen_beanie_fastapi.py
Generates beanie-fastapi app script dependent in models 
generated using [gen_beanie_model.py](#5-gen_beanie_modelpy)

### 8. gen_cached_beanie_fastapi.py
Generates beanie-fastapi app script dependent in models 
generated using [gen_cache_beanie_model.py](#8-gen_cached_beanie_fastapipy)

## Launchers
### 9. launch_cache_fastapi.py
Launches generated cached-fastapi api

### 10. launch_beanie_fastapi.py
Launches generated beanie-fastapi api

### 11. launch_cache_beanie_fastapi.py
Launches generated cached-beanie-fastapi api