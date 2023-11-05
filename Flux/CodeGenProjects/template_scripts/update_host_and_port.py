import json
import logging
from pathlib import PurePath
from typing import Dict
import re

from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager

root_dir: PurePath = PurePath(__file__).parent.parent.parent


class UpdateHostAndPort:
    def __init__(self):
        self.project_dir: PurePath = PurePath(__file__).parent.parent
        self.project_name: str = str(self.project_dir).split("/")[-1]
        self.project_config_file_path: PurePath = self.project_dir / "data" / "config.yaml"
        self.web_ui_path: PurePath = self.project_dir / "web-ui"
        self.project_constants_path: PurePath = self.web_ui_path / "src" / "constants.js"
        self.project_schema_path: PurePath = self.web_ui_path / "public" / "schema.json"

        self.project_config_yaml_dict: Dict = (YAMLConfigurationManager.load_yaml_configurations
                                               (str(self.project_config_file_path)))

        self.server_host: str = self.project_config_yaml_dict.get("server_host")
        self.main_server_beanie_port: str = self.project_config_yaml_dict.get("main_server_beanie_port")
        self.main_server_cache_port: str = self.project_config_yaml_dict.get("main_server_cache_port")
        self.ui_port: str = self.project_config_yaml_dict.get("ui_port")

        self.update_constants_js()
        self.update_schema_json()

    def update_constants_js(self):
        with open(self.project_constants_path, 'r') as f:
            content = f.read()

        content = re.sub(
            r'export const API_ROOT_URL = [^;]+;',
            f'export const API_ROOT_URL = \'http://{self.server_host}:{self.main_server_beanie_port}/'
            f'{self.project_name}\';', content)

        content = re.sub(
            r'export const API_ROOT_CACHE_URL = [^;]+;',
            f'export const API_ROOT_CACHE_URL = \'http://{self.server_host}:{self.main_server_cache_port}/'
            f'{self.project_name}\';', content)

        content = re.sub(
            r'export const API_PUBLIC_URL = [^;]+;',
            f'export const API_PUBLIC_URL = \'http://{self.server_host}:{self.ui_port}/\';', content)

        with open(self.project_constants_path, 'w') as f:
            f.write(content)

        logging.debug(f"constants.js updated successfully for {self.project_name}")

    def update_schema_json(self):
        with open(str(self.project_schema_path), 'r') as f:
            schema_dict: Dict[str, any] = json.loads(f.read())

        for widget_name, widget_schema in schema_dict.items():
            connection_details: Dict | None = widget_schema.get("connection_details")
            if connection_details is not None:
                dynamic_url: bool = connection_details["dynamic_url"]
                if not dynamic_url:
                    connection_details["host"] = self.server_host
                    connection_details["port"] = int(self.main_server_cache_port)

        with open(str(self.project_schema_path), 'w') as f:
            json.dump(schema_dict, f, indent=2)

        logging.debug(f"schema.json updated successfully for {self.project_name}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    UpdateHostAndPort()
