import json
import logging
from pathlib import PurePath
from typing import Dict, Tuple
import re

from FluxPythonUtils.scripts.file_n_general_utility_functions import YAMLConfigurationManager

root_dir: PurePath = PurePath(__file__).parent.parent.parent


class UpdateWebUIConfiguration:
    def __init__(self):
        self.project_dir: PurePath = PurePath(__file__).parent.parent
        self.root_dir: PurePath = self.project_dir.parent
        self.proxy_project_dir: PurePath = self.root_dir.parent.parent / "ws_mux_demux_proxy"
        self.project_name: str = str(self.project_dir).split("/")[-1]
        self.project_config_file_path: PurePath = self.project_dir / "data" / "config.yaml"
        self.proxy_config_file_path: PurePath = self.proxy_project_dir / "data" / "config.yaml"
        self.web_ui_path: PurePath = self.project_dir / "web-ui"
        self.project_constants_path: PurePath = self.web_ui_path / "src" / "constants.js"
        self.project_package_json_path: PurePath = self.web_ui_path / "package.json"
        self.project_schema_path: PurePath = self.web_ui_path / "public" / "schema.json"

        self.project_config_yaml_dict: Dict = (YAMLConfigurationManager.load_yaml_configurations
                                               (str(self.project_config_file_path)))
        self.proxy_config_yaml_dict: Dict = (YAMLConfigurationManager.load_yaml_configurations
                                             (str(self.proxy_config_file_path)))

        self.server_host: str = self.project_config_yaml_dict.get("server_host")
        self.proxy_server_host: str = self.proxy_config_yaml_dict.get("server_host")
        self.proxy_server_port: str = self.proxy_config_yaml_dict.get("server_port")
        self.is_proxy_server: str = self.project_config_yaml_dict.get("is_proxy_server")
        if self.is_proxy_server is None:
            self.is_proxy_server = str(False).lower()
        else:
            self.is_proxy_server = str(self.is_proxy_server).lower()
        self.main_server_beanie_port: str = self.project_config_yaml_dict.get("main_server_beanie_port")
        self.main_server_cache_port: str = self.project_config_yaml_dict.get("main_server_cache_port")
        self.ui_port: str = self.project_config_yaml_dict.get("ui_port")

        self._update_constants_js()
        self._update_schema_json()
        self._update_package_json()

    def _update_constants_js(self):
        with open(self.project_constants_path, 'r') as f:
            content = f.read()

        content = re.sub(r'export const PROXY_SERVER = [^;]+;',
                         f'export const PROXY_SERVER = {self.is_proxy_server};', content)

        content = re.sub(r'export const PROXY_SERVER_URL = [^;]+;',
                         f"export const PROXY_SERVER_URL = "
                         f"'http://{self.proxy_server_host}:{self.proxy_server_port}/ui_proxy';", content)

        content = re.sub(
            r'export const API_ROOT_URL = [^;]+;',
            f'export const API_ROOT_URL = PROXY_SERVER ? PROXY_SERVER_URL : '
            f'\'http://{self.server_host}:{self.main_server_beanie_port}/{self.project_name}\';', content)

        content = re.sub(
            r'export const API_ROOT_CACHE_URL = [^;]+;',
            f'export const API_ROOT_CACHE_URL = \'http://{self.server_host}:{self.main_server_cache_port}/'
            f'{self.project_name}\';', content)

        content = re.sub(
            r'export const API_PUBLIC_URL = [^;]+;',
            f'export const API_PUBLIC_URL = \'http://{self.server_host}:{self.ui_port}\';', content)

        with open(self.project_constants_path, 'w') as f:
            f.write(content)

        logging.debug(f"constants.js updated successfully for {self.project_name}")

    def _update_schema_connection_details(self, widget_schema):
        connection_details: Dict | None = widget_schema.get("connection_details")
        if connection_details is not None:
            dynamic_url: bool = connection_details["dynamic_url"]
            if not dynamic_url:
                project_name: str = connection_details["project_name"]
                host_and_port: Tuple[str, int] = (
                    self.__get_host_and_port_from_specific_project_config(project_name=project_name))
                connection_details["host"], connection_details["port"] = host_and_port

    def _update_schema_json(self):
        with open(str(self.project_schema_path), 'r') as f:
            schema_dict: Dict[str, any] = json.loads(f.read())

        for widget_name, widget_schema in schema_dict.items():
            self._update_schema_connection_details(widget_schema)

        for widget_name, widget_schema in schema_dict["definitions"].items():
            self._update_schema_connection_details(widget_schema)

        with open(str(self.project_schema_path), 'w') as f:
            json.dump(schema_dict, f, indent=2)

        logging.debug(f"schema.json updated successfully for {self.project_name}")

    def __get_host_and_port_from_specific_project_config(self, project_name: str) -> Tuple[str, int]:
        project_dir: PurePath = self.root_dir / project_name
        config_path: PurePath = project_dir / "data" / "config.yaml"
        config_yaml_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(str(config_path))
        host: str = config_yaml_dict.get("server_host")
        beanie_port: int = int(config_yaml_dict.get("main_server_beanie_port"))
        return host, beanie_port

    def _update_package_json(self):
        with open(str(self.project_package_json_path), 'r') as file:
            package_json = json.load(file)

        # Update UI_PORT in package.json
        package_json['scripts']['start'] = f'cross-env PORT={self.ui_port} react-scripts start'

        # Write the updated package.json back to the file
        with open(str(self.project_package_json_path), 'w', encoding='utf-8') as file:
            json.dump(package_json, file, indent=2)

        print(f'"package.json" updated with port {self.ui_port}')


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    UpdateWebUIConfiguration()
