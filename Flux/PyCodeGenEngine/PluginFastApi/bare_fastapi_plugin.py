#!/usr/bin/env python
from typing import Dict

# third-party modules
import protogen

# Project imports
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import main
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_file_handler import FastapiCallbackFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_client_file_handler import FastapiClientFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_launcher_file_handler import FastapiLauncherFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_routes_file_handler import FastapiRoutesFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_override_file_handler import FastapiCallbackOverrideFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_override_set_instance_handler import \
    FastapiCallbackOverrideSetInstanceHandler


class BareFastapiPlugin(FastapiCallbackFileHandler,
                        FastapiCallbackOverrideSetInstanceHandler,
                        FastapiClientFileHandler,
                        FastapiRoutesFileHandler,
                        FastapiLauncherFileHandler,
                        FastapiCallbackOverrideFileHandler):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_fastapi_initialize_file_gen(self):
        output_str = "from fastapi import FastAPI\n"
        routes_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.routes_file_name)
        output_str += f"from {routes_file_path} import {self.api_router_app_name}\n"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str += f"from {model_file_path} import "
        if self.int_id_message_list:
            for message in self.int_id_message_list:
                output_str += message.proto.name
                if message != self.int_id_message_list[-1]:
                    output_str += ", "
                else:
                    output_str += "\n\n\n"
        else:
            output_str += "\n\n\n"
        output_str += f"{self.fastapi_app_name} = FastAPI(title='CRUD API of {self.proto_file_name}')\n\n"
        output_str += f'{self.fastapi_app_name}.include_router({self.api_router_app_name}, ' \
                      f'prefix="/{self.proto_file_package}")\n'

        return output_str

    def set_req_data_members(self, file: protogen.File):
        super().set_req_data_members(file)
        self.fastapi_file_name = f"{self.proto_file_name}_bare_fastapi"

    def handle_fastapi_class_gen(self, file: protogen.File) -> Dict[str, str]:
        # Pre-code generation initializations
        self.load_root_and_non_root_messages_in_dicts(file.messages)
        self.set_req_data_members(file)

        output_dict: Dict[str, str] = {
            # Adding project´s main.py
            self.fastapi_file_name + ".py": self.handle_fastapi_initialize_file_gen(),

            # Adding route's callback class
            self.routes_callback_class_name + ".py": self.handle_callback_class_file_gen(),

            # Adding callback override set_instance file
            self.callback_override_set_instance_file_name + ".py":
                self.handle_callback_override_set_instance_file_gen(),

            # Adding callback override class file
            self.routes_callback_class_name_override + ".py": self.handle_callback_override_file_gen(),

            # Adding project's routes.py
            self.routes_file_name + ".py": self.handle_routes_file_gen(),

            # Adding project's run file
            self.launch_file_name + ".py": self.handle_launch_file_gen(),

            # Adding client file
            self.client_file_name + ".py": self.handle_client_file_gen()
        }

        return output_dict


if __name__ == "__main__":
    main(BareFastapiPlugin)