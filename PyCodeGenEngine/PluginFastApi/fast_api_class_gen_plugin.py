#!/usr/bin/env python
import os
from typing import List, Callable, Dict
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin

# Required for accessing custom options from schema
import insertion_imports


class FastApiClassGenPlugin(BaseProtoPlugin):
    """
    Plugin script to convert proto schema to json schema
    """

    flux_msg_json_root: str = "FluxMsgJsonRoot"
    flux_json_root_create_field: str = "CreateDesc"
    flux_json_root_read_field: str = "ReadDesc"
    flux_json_root_update_field: str = "UpdateDesc"
    flux_json_root_delete_field: str = "DeleteDesc"
    flux_fld_is_required: str = "FluxFldIsRequired"
    flx_fld_attribute_options: List[str] = [
        "FluxFldHelp",
        "FluxFldValMax",
        "FluxFldHide",
        "FluxFldValSortWeight",
        "FluxFldAbbreviated",
        "FluxFldSticky",
        "FluxFldSizeMax"
    ]
    flux_fld_cmnt: str = "FluxFldCmnt"
    flux_msg_cmnt: str = "FluxMsgCmnt"
    flux_fld_index: str = "FluxFldIndex"
    default_id_field_name: str = "id"

    def __init__(self, base_dir_path: str, config_path: str | None = None):
        super().__init__(base_dir_path, config_path)
        self.proto_type_to_py_type_dict = self.config_yaml["proto_type_to_py_type_dict"]
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.handle_fastapi_class_gen
        ]
        self.output_file_name_suffix = self.config_yaml["output_file_name_suffix"]
        self.root_message_list: List[protogen.Message] = []
        self.non_root_message_list: List[protogen.Message] = []
        self.enum_list: List[protogen.Enum] = []
        self.fastapi_app_name: str = ""
        self.proto_file_name: str = ""
        self.proto_file_package: str = ""
        self.api_router_app_name: str = ""
        self.database_file_name: str = ""
        self.main_file_name: str = ""
        self.model_file_name: str = ""
        self.routes_file_name: str = ""
        self.int_id_message_list: List[protogen.Message] = []

    def load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        for field in message.fields:
            if field.kind.name.lower() == "enum":
                if field.enum not in self.enum_list:
                    self.enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if FastApiClassGenPlugin.flux_msg_json_root in str(field.message.proto.options):
                    if field.message not in self.root_message_list:
                        self.root_message_list.append(field.message)
                    # else not required: avoiding repetition
                else:
                    if field.message not in self.non_root_message_list:
                        self.non_root_message_list.append(field.message)
                    # else not required: avoiding repetition
                self.load_dependency_messages_and_enums_in_dicts(field.message)
            # else not required: avoiding other kinds than message or enum

    def load_root_and_non_root_messages_in_dicts(self, message_list: List[protogen.Message]):
        for message in message_list:
            option_str = str(message.proto.options)
            if FastApiClassGenPlugin.flux_msg_json_root in str(message.proto.options):
                if message not in self.root_message_list:
                    self.root_message_list.append(message)
                # else not required: avoiding repetition

                for field in message.fields:
                    if field.proto.name == FastApiClassGenPlugin.default_id_field_name and \
                            "int" == self.proto_to_py_datatype(field):
                        self.int_id_message_list.append(message)
                    # else enot required: If field is not id or is not type int then avoiding append
                    # in int_id_message_list
            else:
                if message not in self.non_root_message_list:
                    self.non_root_message_list.append(message)
                # else not required: avoiding repetition

            self.load_dependency_messages_and_enums_in_dicts(message)

    def handle_empty_dict_creation(self) -> str:
        output_str = ""
        for message in self.root_message_list:
            message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
            output_str += f"{message_name_snake_cased}_dict = dict()\n\n"
        return output_str

    def proto_to_py_datatype(self, field: protogen.Field) -> str:
        match field.kind.name.lower():
            case "message":
                return field.message.proto.name
            case "enum":
                return field.enum.proto.name
            case other:
                return self.proto_type_to_py_type_dict[field.kind.name.lower()]

    def handle_POST_gen(self, message: protogen.Message, method_desc: str | None = None,
                        field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.post("/create-{message_name_snake_cased}/' + f'", response_model={message_name}, status_code=201)\n'
        output_str += f"def create_{message_name_snake_cased}({message_name_snake_cased}: {message_name}) -> {message_name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    try:\n"
        output_str += f"        {message_name}.add_data_in_cache({message_name_snake_cased}.id, " \
                      f"{message_name_snake_cased})\n"
        output_str += f"        return {message_name}.get_data_from_cache({message_name_snake_cased}.id)\n"
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        raise HTTPException(status_code=404, detail=str(e))\n'
        return output_str

    def handle_GET_gen(self, message: protogen.Message, method_desc: str | None = None,
                       field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}/' + '{' + \
                     f'{message_name_snake_cased}_id' + '}' + \
                     f'", response_model={message.proto.name}, status_code=200)\n'
        if field_type is None:
            output_str += f"def read_{message_name_snake_cased}({message_name_snake_cased}_id: int) ->" \
                          f" {message_name}:\n"
        else:
            output_str += f"def read_{message_name_snake_cased}({message_name_snake_cased}_id: {field_type}) -> " \
                          f"{message_name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    try:\n"
        output_str += f"        {message_name_snake_cased}_fetched = " \
                      f"{message_name}.get_data_from_cache({message_name_snake_cased}_id)\n"
        output_str += f"        if {message_name_snake_cased}_fetched is None:\n"
        output_str += '            logging.exception(id_not_found.brief)\n'
        output_str += '            raise HTTPException(status_code=404, detail=id_not_found.brief)\n'
        output_str += f"        else:\n"
        output_str += f"            return {message_name_snake_cased}_fetched\n"
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        raise HTTPException(status_code=404, detail=str(e))\n'
        return output_str

    def handle_PUT_gen(self, message: protogen.Message, method_desc: str | None = None,
                       field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.put("/put-{message_name_snake_cased}/' + f'", response_model={message_name}, status_code=200)\n'
        output_str += f"def update_{message_name_snake_cased}({message_name_snake_cased}: {message_name}) -> {message_name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    try:\n"
        output_str += f"        replace_success = {message_name}.replace_data_in_cache({message_name_snake_cased}.id, {message_name_snake_cased})\n"
        output_str += f"        if not replace_success:\n"
        output_str += '            logging.exception(id_not_found.brief)\n'
        output_str += '            raise HTTPException(status_code=404, detail=id_not_found.brief)\n'
        output_str += f"        else:\n"
        output_str += f"            return {message_name}.get_data_from_cache({message_name_snake_cased}.id)\n"
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        raise HTTPException(status_code=404, detail=str(e))\n'
        return output_str

    def handle_DELETE_gen(self, message: protogen.Message, method_desc: str | None = None,
                          field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.delete("/delete-{message_name_snake_cased}/' + '{' + \
                     f'{message_name_snake_cased}_id' + '}' + f'", response_model=DefaultWebResponse, status_code=200)\n'
        if field_type is None:
            output_str += f"def delete_{message_name_snake_cased}({message_name_snake_cased}_id: int) -> " \
                          f"DefaultWebResponse:\n"
        else:
            output_str += f"def delete_{message_name_snake_cased}({message_name_snake_cased}_id: {field_type}) -> " \
                          f"DefaultWebResponse:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    try:\n"
        output_str += f"        delete_success = {message_name}.delete_data_in_cache({message_name_snake_cased}_id)\n"
        output_str += f"        if not delete_success:\n"
        output_str += '            logging.exception(id_not_found.brief)\n'
        output_str += '            raise HTTPException(status_code=404, detail=id_not_found.brief)\n'
        output_str += f"        else:\n"
        output_str += '            return del_success\n'
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        raise HTTPException(status_code=404, detail=str(e))\n'
        return output_str

    def handle_index_req_gen(self, message: protogen.Message, field: protogen.Field) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        field_name = field.proto.name
        field_type = self.proto_to_py_datatype(field)
        output_str = f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}-from-{field_name}/' + '{' + f'{field_name}' + '}' + f'", response_model=List[{message_name}], status_code=200)\n'
        output_str += f"async def get_{message_name_snake_cased}_from_{field_name}({field_name}: {field_type}) -> List[{message_name}]:\n"
        output_str += f"    try:\n"
        output_str += f"        fetched_{message_name_snake_cased}_list = []\n"
        output_str += f"        {message_name_snake_cased}_dict = {message_name}.get_all_cached_obj()\n"
        output_str += f"        for {message_name_snake_cased} in {message_name_snake_cased}_dict.values():\n"
        output_str += f"            if {field_name} == {message_name_snake_cased}.{field_name}:\n"
        output_str += f"                fetched_{message_name_snake_cased}_list.append({message_name_snake_cased})\n"
        output_str += f'        if not fetched_{message_name_snake_cased}_list:\n'
        output_str += '            logging.exception(no_match_found.brief)\n'
        output_str += '            raise HTTPException(status_code=404, detail=no_match_found.brief)\n'
        output_str += f"        else:\n"
        output_str += f'            return fetched_{message_name_snake_cased}_list\n'
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        raise HTTPException(status_code=404, detail=str(e))\n'
        return output_str

    def handle_get_all_message_request(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.get("/get-all-{message_name_snake_cased}/' + f'", response_model=List[{message_name}], status_code=200)\n'
        output_str += f"async def get_all_{message_name_snake_cased}() -> List[{message_name}]:\n"
        output_str += f'    """\n'
        output_str += f'    Get All {message_name}\n'
        output_str += f'    """\n'
        output_str += f"    try:\n"
        output_str += f"        {message_name_snake_cased}_list = list({message_name}.get_all_cached_obj().values())\n"
        output_str += f'        return {message_name_snake_cased}_list\n'
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        raise HTTPException(status_code=404, detail=str(e))\n\n\n'
        return output_str

    def handle_CRUD_for_message(self, message: protogen.Message) -> str:
        options_list_of_dict = self.get_complex_msg_option_values_as_list_of_dict(message, FastApiClassGenPlugin.flux_msg_json_root)

        # Since json_root option is of non-repeated type
        option_dict = options_list_of_dict[0]

        crud_field_name_to_method_call_dict = {
            FastApiClassGenPlugin.flux_json_root_create_field: self.handle_POST_gen,
            FastApiClassGenPlugin.flux_json_root_read_field: self.handle_GET_gen,
            FastApiClassGenPlugin.flux_json_root_update_field: self.handle_PUT_gen,
            FastApiClassGenPlugin.flux_json_root_delete_field: self.handle_DELETE_gen
        }

        output_str = self.handle_get_all_message_request(message)

        id_field_type: str | None = None
        if message in self.int_id_message_list:
            for field in message.fields:
                if field.proto.name == FastApiClassGenPlugin.default_id_field_name and\
                        "int" != (field_type := self.proto_to_py_datatype(field)):
                    id_field_type = field_type
                    break
                # else not required: Avoiding field if not id
        # else not required: Avoid if message does not have custom id field

        for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
            if crud_option_field_name in option_dict:
                method_disc = option_dict[crud_option_field_name]
                output_str += crud_operation_method(message, method_disc, id_field_type)
                output_str += "\n\n"
            # else not required: Avoiding method creation if desc not provided in option

        for field in message.fields:
            if FastApiClassGenPlugin.flux_fld_index in str(field.proto.options):
                output_str += self.handle_index_req_gen(message, field)
            # else not required: Avoiding field if index option is not enabled

        return output_str

    def handle_CRUD_task(self) -> str:
        output_str = ""
        for message in self.root_message_list:
            output_str += self.handle_CRUD_for_message(message)

        return output_str

    def handle_execution_code(self, py_file_name: str | None = None) -> str:
        output_str = 'if __name__ == "__main__":\n'
        output_str += f'    # uvicorn.run("{self.fastapi_app_name}", host="0.0.0.0", port=int(os.getenv("APP_PORT")))\n'
        py_output_file_name_suffix:str = self.config_yaml["output_file_name_suffix"]
        run_prefix = "" if py_file_name is None else (py_file_name + "_" + py_output_file_name_suffix.rstrip(".py") + ":")
        output_str += f'    uvicorn.run("{run_prefix}{self.fastapi_app_name}")\n'
        return output_str

    def handle_web_response_inits(self) -> str:
        output_str = 'id_not_found = DefaultWebResponse(brief="Id not Found")\n'
        output_str += 'del_success = DefaultWebResponse(brief="Deletion Successful")\n'
        output_str += 'no_match_found = DefaultWebResponse(brief="No Match Found")\n'
        return output_str

    def handle_main_file_gen(self):
        output_str = "from fastapi import FastAPI\n"
        output_str += f"from {self.routes_file_name} import {self.api_router_app_name}\n"
        output_str += f"from {self.model_file_name} import "
        for message in self.int_id_message_list:
            output_str += message.proto.name
            if message != self.int_id_message_list[-1]:
                output_str += ", "
            else:
                output_str += "\n\n\n"
        output_str += f"{self.fastapi_app_name} = FastAPI(title='CRUD API of {self.proto_file_name}')\n\n\n"
        output_str += f"async def init_max_id_handler(root_base_model):\n"
        output_str += f'    root_base_model.init_max_id(0)\n\n\n'
        output_str += f'@{self.fastapi_app_name}.on_event("startup")\n'
        output_str += f'async def connect():\n'
        for message in self.int_id_message_list:
            message_name = message.proto.name
            output_str += f"    await init_max_id_handler({message_name})\n"
        output_str += "\n"
        output_str += f'{self.fastapi_app_name}.include_router({self.api_router_app_name}, ' \
                      f'prefix="/{self.proto_file_package}")\n'

        return output_str

    def handle_routes_file_gen(self):
        output_str = "from fastapi import APIRouter, HTTPException\n"
        output_str += "import logging\n"
        output_str += "from typing import List\n"
        output_str += f"from {self.model_file_name} import "
        for message in self.root_message_list:
            output_str += message.proto.name
            if message != self.root_message_list[-1]:
                output_str += ", "
            else:
                output_str += "\n"
        default_web_response_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "default_web_response")
        output_str += f'from {default_web_response_file_path} import DefaultWebResponse\n\n\n'
        output_str += self.handle_web_response_inits() + "\n"
        output_str += f"{self.api_router_app_name} = APIRouter()\n\n\n"
        output_str += self.handle_CRUD_task()
        return output_str

    def handle_run_fie_gen(self) -> str:
        output_str = "import os\n"
        output_str += "import uvicorn\n\n\n"
        output_str += 'if __name__ == "__main__":\n'
        output_str += f'    if reload_env := os.getenv("RELOAD"):\n'
        output_str += f'        reload_status: bool = True if reload_env.lower() == "true" else False\n'
        output_str += f'    else:\n'
        output_str += f'        reload_status: bool = False\n'
        output_str += f'    uvicorn.run(reload=reload_status, app="{self.main_file_name}:{self.fastapi_app_name}")\n'
        return output_str

    def handle_fastapi_class_gen(self, file: protogen.File) -> Dict[str, str]:
        # Pre-code generation initializations
        self.load_root_and_non_root_messages_in_dicts(file.messages)
        self.proto_file_name = str(file.proto.name).split('.')[0]
        self.proto_file_package = str(file.proto.package)
        self.fastapi_app_name = f"{self.proto_file_name}_app"
        self.api_router_app_name = f"{self.proto_file_name}_API_router"
        self.database_file_name = f"{self.proto_file_name}_cache_database"
        self.main_file_name = f"{self.proto_file_name}_cache_main"
        self.model_file_name = f'{self.proto_file_name}_cache_model'
        self.routes_file_name = f'{self.proto_file_name}_cache_routes'

        output_dict: Dict[str, str] = {

            # Adding project´s main.py
            self.main_file_name + ".py": self.handle_main_file_gen(),

            # Adding project's routes.py
            self.routes_file_name + ".py": self.handle_routes_file_gen(),

            # Adding project's run file
            self.proto_file_name + "_" + self.config_yaml["output_file_name_suffix"]: self.handle_run_fie_gen()
        }

        return output_dict


if __name__ == "__main__":
    def main():
        project_dir_path = os.getenv("PROJECT_PATH")
        config_path = os.getenv("CONFIG_PATH")
        pydantic_class_gen_plugin = FastApiClassGenPlugin(project_dir_path, config_path)
        pydantic_class_gen_plugin.process()

    main()
