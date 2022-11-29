#!/usr/bin/env python
import os
import logging
import time
from typing import List, Dict

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginFastApi.beanie_fast_api_class_gen_plugin import BeanieFastApiClassGenPlugin


class HybridBeanieFastApiClassGenPlugin(BeanieFastApiClassGenPlugin):
    """
    Plugin script to generate Hybrid-Beanie enabled fastapi app
    """

    def __init__(self, base_dir_path: str, config_path: str | None = None):
        super().__init__(base_dir_path, config_path)

    def load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        for field in message.fields:
            if field.kind.name.lower() == "enum":
                if field.enum not in self.enum_list:
                    self.enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if HybridBeanieFastApiClassGenPlugin.flux_msg_json_root in str(field.message.proto.options):
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
            if HybridBeanieFastApiClassGenPlugin.flux_msg_json_root in str(message.proto.options):
                if message not in self.root_message_list:
                    self.root_message_list.append(message)
                # else not required: avoiding repetition

                if HybridBeanieFastApiClassGenPlugin.default_id_field_name in [field.proto.name for field in message.fields]:
                    self.custom_id_primary_key_messages.append(message)
            else:
                if message not in self.non_root_message_list:
                    self.non_root_message_list.append(message)
                # else not required: avoiding repetition

            self.load_dependency_messages_and_enums_in_dicts(message)

    def handle_POST_gen(self, message: protogen.Message, method_desc: str | None = None, id_field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.post("/create-{message_name_snake_cased}' + f'", response_model={message_name}, status_code=201)\n'
        output_str += f"async def create_{message_name_snake_cased}({message_name_snake_cased}: {message_name}) -> {message_name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    try:\n"
        output_str += f"        await {message_name_snake_cased}.create()\n"
        output_str += f"        success = {message_name}.add_data_in_cache({message_name_snake_cased}.id, " \
                      f"{message_name_snake_cased})\n"
        output_str += f'        if not success:\n'
        output_str += '            err_str = f"{' + f'{message_name_snake_cased}.id'+'} already exists in ' + \
                      f'{message_name} cache dict"\n'
        output_str += f'            logging.exception(err_str)\n'
        output_str += f'            raise HTTPException(status_code=404, detail=err_str)\n'
        output_str += f"        return {message_name_snake_cased}\n"
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        raise HTTPException(status_code=404, detail=str(e))\n'
        return output_str

    def handle_GET_gen(self, message: protogen.Message, method_desc: str | None = None,
                       id_field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}/' + \
                     '{' + f'{message_name_snake_cased}_id' + '}' + \
                     f'", response_model={message_name}, status_code=200)\n'
        if id_field_type is not None:
            output_str += f"async def read_{message_name_snake_cased}({message_name_snake_cased}_id: " \
                          f"{id_field_type}) -> {message_name}:\n"
        else:
            output_str += f"async def read_{message_name_snake_cased}({message_name_snake_cased}_id: " \
                          f"PydanticObjectId) -> {message_name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    try:\n"
        output_str += f"        cached_{message_name_snake_cased}_dict = {message_name}.get_all_cached_obj()\n"
        output_str += f"        if {message_name_snake_cased}_id in cached_{message_name_snake_cased}_dict:\n"
        output_str += f"            fetched_{message_name_snake_cased} = " \
                      f"cached_{message_name_snake_cased}_dict[{message_name_snake_cased}_id]\n"
        output_str += f"        else:\n"
        output_str += f"            fetched_{message_name_snake_cased} = await {message_name}.get(" \
                      f"{message_name_snake_cased}_id)\n"
        output_str += f'        if not fetched_{message_name_snake_cased}:\n'
        output_str += '            logging.exception(id_not_found.brief)\n'
        output_str += '            raise HTTPException(status_code=404, detail=id_not_found.brief)\n'
        output_str += f"        else:\n"
        output_str += f"            if {message_name_snake_cased}_id not in cached_{message_name_snake_cased}_dict:\n"
        output_str += f"                {message_name}.add_data_in_cache({message_name_snake_cased}_id, " \
                      f"fetched_{message_name_snake_cased})\n"
        output_str += f'            return fetched_{message_name_snake_cased}\n'
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        raise HTTPException(status_code=404, detail=str(e))\n'
        return output_str

    def handle_PUT_gen(self, message: protogen.Message, method_desc: str | None = None, id_field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.put("/put-{message_name_snake_cased}' + \
                     f'", response_model={message_name}, status_code=200)\n'
        output_str += f"async def update_{message_name_snake_cased}({message_name_snake_cased}_updated: " \
                      f"{message_name}) -> {message_name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    try:\n"
        if self.response_type.lower() == "snake":
            output_str += "        req_dict_without_none_val = {" + \
                          f"k: v for k, v in {message_name_snake_cased}_updated.dict().items() " + \
                          "if v is not None}\n"
        elif self.response_type.lower() == "camel":
            output_str += "        req_dict_without_none_val = {" + \
                          f"to_camel(k): v for k, v in {message_name_snake_cased}_updated.dict().items() " + \
                          "if v is not None}\n"
        else:
            err_str = f"{self.response_type} is not supported response type"
            logging.exception(err_str)
            raise Exception(err_str)
        output_str += '        update_query = {"$set": req_dict_without_none_val.items()}\n'
        output_str += f'        review = await {message_name}.get({message_name_snake_cased}_updated.id)\n'
        output_str += f'        if not review:\n'
        output_str += '            logging.exception(id_not_found.brief)\n'
        output_str += '            raise HTTPException(status_code=404, detail=id_not_found.brief)\n'
        output_str += f"        else:\n"
        output_str += f"            await review.update(update_query)\n"
        output_str += f"            success = {message_name}.replace_data_in_cache(review.id, review)\n"
        output_str += f'            if not success:\n'
        output_str += '                err_str = f"{' + f'review.id' + '} not exists in ' + \
                      f'{message_name} cache dict"\n'
        output_str += f'                logging.exception(err_str)\n'
        output_str += f'                raise HTTPException(status_code=404, detail=err_str)\n'
        output_str += f"            return review\n"
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        raise HTTPException(status_code=404, detail=str(e))\n'
        return output_str

    def handle_DELETE_gen(self, message: protogen.Message, method_desc: str | None = None, id_field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.delete("/delete-{message_name_snake_cased}/' + \
                     '{'+f'{message_name_snake_cased}_id'+'}' + \
                     f'", response_model=DefaultWebResponse, status_code=200)\n'
        if id_field_type is not None:
            output_str += f"async def delete_{message_name_snake_cased}({message_name_snake_cased}_id: " \
                          f"{id_field_type}) -> DefaultWebResponse:\n"
        else:
            output_str += f"async def delete_{message_name_snake_cased}({message_name_snake_cased}_id: " \
                          f"PydanticObjectId) -> DefaultWebResponse:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    try:\n"
        output_str += f"        record = await {message_name}.get({message_name_snake_cased}_id)\n"
        output_str += '        if not record:\n'
        output_str += '            logging.exception(id_not_found.brief)\n'
        output_str += '            raise HTTPException(status_code=404, detail=id_not_found.brief)\n'
        output_str += f"        else:\n"
        output_str += f"            await record.delete()\n"
        output_str += f"            success = {message_name}.delete_data_in_cache({message_name_snake_cased}_id)\n"
        output_str += f"            if not success:\n"
        output_str += '                err_str = f"{' + f'{message_name_snake_cased}' + '_id} not exists in ' + \
                      f'{message_name} cache dict"\n'
        output_str += f'                logging.exception(err_str)\n'
        output_str += f'                raise HTTPException(status_code=404, detail=err_str)\n'
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
        output_str = f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}-from-{field_name}/' + \
                     '{' + f'{field_name}' + '}' + f'", response_model=List[{message_name}], status_code=200)\n'
        output_str += f"async def get_{message_name_snake_cased}_from_{field_name}({field_name}: {field_type}) -> " \
                      f"List[{message_name}]:\n"
        output_str += f"    try:\n"
        output_str += f"        fetched_{message_name_snake_cased}_list = [obj for obj in list(" \
                      f"{message_name}.get_all_cached_obj().values()) if obj.{field_name} == {field_name}]\n"
        output_str += f'        if not fetched_{message_name_snake_cased}_list:\n'
        output_str += '            logging.exception(no_match_found.brief)\n'
        output_str += '            raise HTTPException(status_code=404, detail=no_match_found.brief)\n'
        output_str += f"        else:\n"
        output_str += f'            return fetched_{message_name_snake_cased}_list\n'
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        raise HTTPException(status_code=404, detail=str(e))\n'
        return output_str

    def handle_get_all_message_request(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.get("/get-all-{message_name_snake_cased}/' + \
                     f'", response_model=List[{message_name}], status_code=200)\n'
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
        options_list_of_dict = self.get_complex_msg_option_values_as_list_of_dict(message, HybridBeanieFastApiClassGenPlugin.flux_msg_json_root)

        # Since json_root option is of non-repeated type
        option_dict = options_list_of_dict[0]

        crud_field_name_to_method_call_dict = {
            HybridBeanieFastApiClassGenPlugin.flux_json_root_create_field: self.handle_POST_gen,
            HybridBeanieFastApiClassGenPlugin.flux_json_root_read_field: self.handle_GET_gen,
            HybridBeanieFastApiClassGenPlugin.flux_json_root_update_field: self.handle_PUT_gen,
            HybridBeanieFastApiClassGenPlugin.flux_json_root_delete_field: self.handle_DELETE_gen
        }

        output_str = self.handle_get_all_message_request(message)

        id_field_type: str | None = None
        if message in self.custom_id_primary_key_messages:
            for field in message.fields:
                if field.proto.name == HybridBeanieFastApiClassGenPlugin.default_id_field_name:
                    id_field_type = self.proto_to_py_datatype(field)
                    break
                # else not required: Avoiding field if not id
        # else not required: Avoid if message does not have custom id field

        for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
            if crud_option_field_name in option_dict:
                method_desc: str = option_dict[crud_option_field_name]
                output_str += crud_operation_method(message, method_desc, id_field_type)
                output_str += "\n\n"
            # else not required: Avoiding method creation if desc not provided in option

        for field in message.fields:
            if HybridBeanieFastApiClassGenPlugin.flux_fld_index in str(field.proto.options):
                output_str += self.handle_index_req_gen(message, field)
            # else not required: Avoiding field if index option is not enabled

        return output_str

    def handle_CRUD_task(self) -> str:
        output_str = ""
        for message in self.root_message_list:
            output_str += self.handle_CRUD_for_message(message)

        return output_str

    def handle_web_response_inits(self) -> str:
        output_str = 'id_not_found = DefaultWebResponse(brief="Id not Found")\n'
        output_str += 'del_success = DefaultWebResponse(brief="Deletion Successful")\n'
        output_str += 'no_match_found = DefaultWebResponse(brief="No Match Found")\n'
        return output_str

    def handle_init_db(self) -> str:
        root_msg_list = [message.proto.name for message in self.root_message_list]
        model_names = ", ".join(root_msg_list)
        output_str = "async def init_db():\n"
        output_str += f'    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")\n'
        output_str += f'    await init_beanie(\n'
        output_str += f'              database=client.{self.proto_file_package},\n'
        output_str += f'              document_models=[{model_names}]\n'
        output_str += f'              )\n'
        return output_str

    def handle_main_file_gen(self) -> str:
        output_str = "import logging\n"
        output_str += "from fastapi import FastAPI\n"
        output_str += f"from {self.routes_file_name} import {self.api_router_app_name}\n"
        output_str += f"from {self.model_file_name} import "
        for message in self.custom_id_primary_key_messages:
            output_str += message.proto.name
            if message != self.custom_id_primary_key_messages[-1]:
                output_str += ", "
            else:
                output_str += "\n"
        output_str += f"from {self.database_file_name} import init_db\n\n\n"
        output_str += f"{self.fastapi_app_name} = FastAPI(title='CRUD API of {self.proto_file_name}')\n\n\n"
        output_str += f"async def init_max_id_handler(document):\n"
        output_str += f'    max_val = await document.find_all().max("_id")\n'
        output_str += f'    document.init_max_id(int(max_val) if max_val is not None else 0)\n'
        output_str += f'    all_objs = await document.find_all().to_list()\n'
        output_str += f'    for obj in all_objs:\n'
        output_str += f'        success = document.add_data_in_cache(obj.id, obj)\n'
        output_str += f'        if not success:\n'
        output_str += '            err_str = f"{obj.id} already found in cache dict while loading ' \
                      'in cache before connect"\n'
        output_str += f'            logging.exception(err_str)\n'
        output_str += f'            raise Exception(err_str)\n\n\n'
        output_str += f'@{self.fastapi_app_name}.on_event("startup")\n'
        output_str += f'async def connect():\n'
        output_str += f'    await init_db()\n'
        for message in self.custom_id_primary_key_messages:
            message_name = message.proto.name
            output_str += f"    await init_max_id_handler({message_name})\n"
        output_str += "\n"
        output_str += f'{self.fastapi_app_name}.include_router({self.api_router_app_name}, ' \
                      f'prefix="/{self.proto_file_package}")\n'

        return output_str

    def handle_fastapi_class_gen(self, file: protogen.File) -> Dict[str, str]:
        # Pre-code generation initializations
        self.load_root_and_non_root_messages_in_dicts(file.messages)
        self.proto_file_name = str(file.proto.name).split('.')[0]
        self.proto_file_package = str(file.proto.package)
        self.fastapi_app_name = f"{self.proto_file_name}_app"
        self.api_router_app_name = f"{self.proto_file_name}_API_router"
        self.database_file_name = f"{self.proto_file_name}_hybrid_beanie_database"
        self.main_file_name = f"{self.proto_file_name}_hybrid_beanie_main"
        self.model_file_name = f'{self.proto_file_name}_beanie_model'
        self.routes_file_name = f'{self.proto_file_name}_hybrid_beanie_routes'

        output_dict: Dict[str, str] = {
            # Adding project´s database.py
            self.database_file_name+".py": self.handle_database_file_gen(),

            # Adding project´s main.py
            self.main_file_name+".py": self.handle_main_file_gen(),

            # Adding project's routes.py
            self.routes_file_name+".py": self.handle_routes_file_gen(),

            # Adding project's run file
            self.proto_file_name+"_"+self.config_yaml["output_file_name_suffix"]: self.handle_run_fie_gen()
        }

        return output_dict


if __name__ == "__main__":
    def main():
        project_dir_path = os.getenv("PROJECT_PATH")
        config_path = os.getenv("CONFIG_PATH")
        pydantic_class_gen_plugin = HybridBeanieFastApiClassGenPlugin(project_dir_path, config_path)
        pydantic_class_gen_plugin.process()

    main()
