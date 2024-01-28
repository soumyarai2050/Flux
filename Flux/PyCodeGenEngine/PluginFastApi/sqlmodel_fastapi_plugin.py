#!/usr/bin/env python
import logging
import os
from typing import List, Dict
import time

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginFastApi.cache_fastapi_plugin import CacheFastApiPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case


class SQLModelFastApiPlugin(CacheFastApiPlugin):
    """
    Plugin script to generate SqlModel enabled fastapi app
    """
    flux_fld_primary: str = "FluxFldPk"

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.db_file_name: str | None = None
        self.proto_file_name: str = ""
        self.gen_db_script_name: str = ""
        self.sqlmodel_fastapi_file_name: str = ""

    def load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        for field in message.fields:
            if field.kind.name.lower() == "enum":
                if field.enum not in self.enum_list:
                    self.enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if self.is_option_enabled(field.message, SQLModelFastApiPlugin.flux_msg_json_root):
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
        message_list.sort(key=lambda message_: message_.proto.name)     # sorting by name
        for message in message_list:
            if self.is_option_enabled(message, SQLModelFastApiPlugin.flux_msg_json_root):
                if message not in self.root_message_list:
                    self.root_message_list.append(message)
                # else not required: avoiding repetition
            else:
                if message not in self.non_root_message_list:
                    self.non_root_message_list.append(message)
                # else not required: avoiding repetition

            self.load_dependency_messages_and_enums_in_dicts(message)

    def handle_POST_gen(self, message: protogen.Message, aggregation_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.fastapi_app_name}.post("/create-{message_name_snake_cased}' + f'", response_model={message.proto.name} | DefaultWebResponse)\n'
        output_str += f"async def create_{message_name_snake_cased}({message_name_snake_cased}: {message.proto.name}, session: AsyncSession = Depends(get_session)):\n"
        if aggregation_type:
            output_str += f'    """\n'
            output_str += f'    {aggregation_type}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    try:\n"
        output_str += f"        session.add({message_name_snake_cased})\n"
        output_str += f"        await session.commit()\n"
        output_str += f"        await session.refresh({message_name_snake_cased})\n"
        output_str += f"        return {message_name_snake_cased}\n"
        output_str += '    except ValidationError as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        return something_went_wrong\n'
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        return something_went_wrong\n'
        return output_str

    def handle_GET_gen(self, message: protogen.Message, aggregate_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.fastapi_app_name}.get("/get-{message_name_snake_cased}/' + '{'+f'{message_name_snake_cased}'+'_id}' + f'", response_model={message.proto.name} | DefaultWebResponse)\n'
        output_str += f"async def read_{message_name_snake_cased}({message_name_snake_cased}_id: int, session: AsyncSession = Depends(get_session)):\n"
        if aggregate_type:
            output_str += f'    """\n'
            output_str += f'    {aggregate_type}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    try:\n"
        output_str += f"        fetched_{message_name_snake_cased} = await session.get({message.proto.name}, {message_name_snake_cased}_id)\n"
        output_str += f'        if not fetched_{message_name_snake_cased}:\n'
        output_str += f'            return id_not_found\n'
        output_str += f"        else:\n"
        output_str += f"            return fetched_{message_name_snake_cased}\n"
        output_str += '    except ValidationError as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        return something_went_wrong\n'
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        return something_went_wrong\n'
        return output_str

    def handle_PUT_gen(self, message: protogen.Message, method_desc: str | None = None) -> str:
        for field in message.fields:
            if self.is_option_enabled(field, SQLModelFastApiPlugin.flux_fld_primary):
                primary_key_field_name: str = field.proto.name
                break
        else:
            err_str = f"Could not find any primary key in {message.proto.name} table"
            logging.exception(err_str)
            raise Exception(err_str)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.fastapi_app_name}.put("/put-{message_name_snake_cased}/' + f'", response_model={message.proto.name} | DefaultWebResponse)\n'
        output_str += f"async def update_{message_name_snake_cased}({message_name_snake_cased}: {message.proto.name}, session: AsyncSession = Depends(get_session)):\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    try:\n"
        output_str += f"        fetched_{message_name_snake_cased} = await session.get({message.proto.name}, {message_name_snake_cased}.{primary_key_field_name})\n"
        output_str += f'        if not fetched_{message_name_snake_cased}:\n'
        output_str += f'            return id_not_found\n'
        output_str += f"        else:\n"
        output_str += f"            {message_name_snake_cased}_data = {message_name_snake_cased}.dict(exclude_unset=True)\n"
        output_str += f"            for key, value in {message_name_snake_cased}_data.items():\n"
        output_str += f"                setattr(fetched_{message_name_snake_cased}, key, value)\n"
        output_str += f"            session.add(fetched_{message_name_snake_cased})\n"
        output_str += f"            await session.commit()\n"
        output_str += f"            await session.refresh(fetched_{message_name_snake_cased})\n"
        output_str += f"            return {message_name_snake_cased}\n"
        output_str += '    except ValidationError as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        return output_str

    def handle_DELETE_gen(self, message: protogen.Message, method_desc: str | None = None) -> str:
        for field in message.fields:
            if self.is_option_enabled(field, SQLModelFastApiPlugin.flux_fld_primary):
                primary_key_field_type: str = \
                    self.proto_to_py_datatype(field)
                break
        else:
            err_str = f"Could not find any primary key in {message.proto.name} table"
            logging.exception(err_str)
            raise Exception(err_str)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.fastapi_app_name}.delete("/delete-{message_name_snake_cased}/' + f'", response_model=DefaultWebResponse)\n'
        output_str += f"async def delete_{message_name_snake_cased}({message_name_snake_cased}_id: {primary_key_field_type}, session: AsyncSession = Depends(get_session)):\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    try:\n"
        output_str += f"        fetched_{message_name_snake_cased} = await session.get({message.proto.name}, {message_name_snake_cased}_id)\n"
        output_str += f'        if not fetched_{message_name_snake_cased}:\n'
        output_str += f'            return id_not_found\n'
        output_str += f"        else:\n"
        output_str += f"            await session.delete(fetched_{message_name_snake_cased})\n"
        output_str += f"            await session.commit()\n"
        output_str += f"            return delete_success\n"
        output_str += '    except ValidationError as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        return output_str

    def handle_index_req_gen(self, message: protogen.Message, field: protogen.Field) -> str:
        field_name = field.proto.name
        field_type = self.proto_to_py_datatype(field)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        # @@@ TODO: use response model in this case (throwing error for now)
        output_str = f'@{self.fastapi_app_name}.get("/get-{message_name_snake_cased}_from_{field_name}/' + '{' + f'{message_name_snake_cased}' + '_id}' + f'")\n'
        output_str += f"async def read_{message_name_snake_cased}_from_{field_name}({field_name}: {field_type}, session: AsyncSession = Depends(get_session)):\n"
        output_str += f'    """\n'
        output_str += f'    Get {message.proto.name} from {field_name}\n'
        output_str += f'    """\n'
        output_str += f"    try:\n"
        output_str += f"        statement = select({message.proto.name}).where({message.proto.name}.{field_name} == {field_name})\n"
        output_str += f"        results = await session.execute(statement)\n"
        output_str += f"        return results.all()\n"
        output_str += '    except ValidationError as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        return something_went_wrong\n'
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        return something_went_wrong\n\n\n'
        return output_str

    def handle_GET_ALL_gen(self, message: protogen.Message) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        # @@@ TODO: use response model in this case (throwing error for now)
        output_str = f'@{self.fastapi_app_name}.get("/get-all-{message_name_snake_cased}/' + f'")\n'
        output_str += f"async def read_all_{message_name_snake_cased}(session: AsyncSession = Depends(get_session)):\n"
        output_str += f'    """\n'
        output_str += f'    Get All {message.proto.name}\n'
        output_str += f'    """\n'
        output_str += f"    try:\n"
        output_str += f"        statement = select({message.proto.name})\n"
        output_str += f"        results = await session.execute(statement)\n"
        output_str += f"        return results.all()\n"
        output_str += '    except ValidationError as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        return something_went_wrong\n'
        output_str += '    except Exception as e:\n'
        output_str += '        logging.exception(e)\n'
        output_str += '        return something_went_wrong\n\n\n'
        return output_str

    def handle_CRUD_for_message(self, message: protogen.Message) -> str:
        option_value_dict = self.get_complex_option_value_from_proto(message, SQLModelFastApiPlugin.flux_msg_json_root)

        crud_field_name_to_method_call_dict = {
            SQLModelFastApiPlugin.flux_json_root_create_field: self.handle_POST_gen,
            SQLModelFastApiPlugin.flux_json_root_read_field: self.handle_GET_gen,
            SQLModelFastApiPlugin.flux_json_root_update_field: self.handle_PUT_gen,
            SQLModelFastApiPlugin.flux_json_root_delete_field: self.handle_DELETE_gen
        }

        output_str = self.handle_GET_ALL_gen(message)
        for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
            if crud_option_field_name in option_value_dict:
                method_disc = option_value_dict[crud_option_field_name]
                output_str += crud_operation_method(message, method_disc)
                output_str += "\n\n"
            # else not required: Avoiding method creation if desc not provided in option

        for field in message.fields:
            if self.is_option_enabled(field, SQLModelFastApiPlugin.flux_fld_index):
                output_str += self.handle_index_req_gen(message, field)
            # else not required: Avoiding field if index option is not enabled

        return output_str

    def handle_CRUD_task(self) -> str:
        output_str = ""
        for message in self.root_message_list:
            output_str += self.handle_CRUD_for_message(message)

        return output_str

    def handle_web_response_inits(self) -> str:
        output_str = 'something_went_wrong = DefaultWebResponse(brief="something went wrong")\n'
        output_str += f'id_not_found = DefaultWebResponse(brief="Id not found")\n'
        output_str += f'delete_success = DefaultWebResponse(brief="Deletion Successful")\n'
        return output_str

    def handle_start_event(self) -> str:
        output_str = f'@{self.fastapi_app_name}.on_event("startup")\n'
        output_str += 'async def on_startup():\n'
        output_str += '    await init_db()\n\n\n'
        return output_str

    def handle_db_configs_settings(self) -> str:
        output_str = f'DATABASE_URL = "sqlite+aiosqlite:///{self.db_file_name}"\n'
        output_str += "engine = create_async_engine(DATABASE_URL, echo=True, future=True)\n\n\n"
        output_str += "async def init_db():\n"
        output_str += "    async with engine.begin() as conn:\n"
        output_str += "        await conn.run_sync(SQLModel.metadata.create_all)\n\n\n"
        output_str += "async def get_session() -> AsyncSession:\n"
        output_str += "    async_session = sessionmaker(\n"
        output_str += "        engine, class_=AsyncSession, expire_on_commit=False\n"
        output_str += "    )\n"
        output_str += "    async with async_session() as session:\n"
        output_str += "        yield session\n"
        return output_str

    def handle_fastapi_app_gen(self) -> str:
        # Adding pydantic classes
        output_str = f'from {self.proto_file_name}_sqlmodel import '
        for message in self.root_message_list:
            output_str += message.proto.name
            if message != self.root_message_list[-1]:
                output_str += ", "
            else:
                output_str += "\n"

        output_str += f'from {self.gen_db_script_name} import '
        output_str += "init_db, get_session\n"

        default_web_response_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "default_web_response")
        output_str += f'from {default_web_response_file_path} import DefaultWebResponse\n'
        output_str += "import logging\n"
        output_str += "from fastapi import FastAPI, Depends\n"
        output_str += "from sqlalchemy.ext.asyncio import AsyncSession\n"
        output_str += "import uvicorn\n"
        output_str += "from sqlmodel import select\n"
        output_str += "from typing import List\n"
        output_str += "from pydantic import ValidationError\n\n\n"

        output_str += self.handle_web_response_inits()

        output_str += f"{self.fastapi_app_name} = FastAPI()\n\n\n"

        output_str += self.handle_start_event()

        output_str += self.handle_CRUD_task()

        output_str += self.handle_execution_code(self.proto_file_name)
        return output_str

    def handle_db_file_gen(self) -> str:
        output_str = "from sqlmodel import SQLModel\n"
        output_str += "from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine\n"
        output_str += "from sqlalchemy.orm import sessionmaker\n\n\n"
        output_str += self.handle_db_configs_settings()
        return output_str

    def handle_fastapi_class_gen(self, file: protogen.File) -> Dict[str, str]:
        self.load_root_and_non_root_messages_in_dicts(file.messages)
        self.proto_file_name = str(file.proto.name).split('.')[0]
        self.fastapi_app_name = f"{self.proto_file_name}_app"
        self.db_file_name = f"{self.proto_file_name}_sqlmodel_db.db"
        self.gen_db_script_name = self.proto_file_name + "_sqlmodel_db"
        if (output_file_name_suffix := os.getenv("OUTPUT_FILE_NAME_SUFFIX")) is not None and \
                len(output_file_name_suffix):
            self.sqlmodel_fastapi_file_name = self.proto_file_name + "_" + output_file_name_suffix
        else:
            err_str = f"Env var 'OUTPUT_FILE_NAME_SUFFIX' received as {output_file_name_suffix}"
            logging.exception(err_str)
            raise Exception(err_str)

        output_dict = {
            # Adding db script
            self.gen_db_script_name+".py": self.handle_db_file_gen(),

            # Adding fastapi app script
            self.sqlmodel_fastapi_file_name: self.handle_fastapi_app_gen()
        }

        return output_dict


if __name__ == "__main__":
    main(SQLModelFastApiPlugin)
