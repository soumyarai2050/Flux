import json
import logging
from pathlib import PurePath
from typing import Dict, Tuple
import re

from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager

root_dir: PurePath = PurePath(__file__).parent.parent.parent


class UpdateWebUIConfiguration:
    def __init__(self):
        self.project_dir: PurePath = PurePath(__file__).parent.parent
        self.root_dir: PurePath = self.project_dir.parent
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

        self._update_constants_js()
        self._update_schema_json()

    def _update_constants_js(self):
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

    def _update_schema_json(self):
        with open(str(self.project_schema_path), 'r') as f:
            schema_dict: Dict[str, any] = json.loads(f.read())

        for widget_name, widget_schema in schema_dict.items():
            connection_details: Dict | None = widget_schema.get("connection_details")
            if connection_details is not None:
                dynamic_url: bool = connection_details["dynamic_url"]
                if not dynamic_url:
                    project_name: str = connection_details["project_name"]
                    host_and_port: Tuple[str, int] = (
                        self.__get_host_and_port_from_specific_project_config(project_name=project_name))
                    connection_details["host"], connection_details["port"] = host_and_port

        with open(str(self.project_schema_path), 'w') as f:
            json.dump(schema_dict, f, indent=2)

        logging.debug(f"schema.json updated successfully for {self.project_name}")

    def __get_host_and_port_from_specific_project_config(self, project_name: str) -> Tuple[str, int]:
        project_dir: PurePath = self.root_dir / project_name
        config_path: PurePath = project_dir / "Data" / "config.yaml"
        config_yaml_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(str(config_path))
        host: str = config_yaml_dict.get("server_host")
        beanie_port: int = int(config_yaml_dict.get("main_server_beanie_port"))
        return host, beanie_port


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    UpdateWebUIConfiguration()
