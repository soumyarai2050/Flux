#!/usr/bin/env python
import json
import os
from typing import List, Callable, Dict
import time
import logging
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, YAMLConfigurationManager


class JsProjectSpecificUtilsPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to generate projectSpecificUtils.js file from proto schema.
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def output_file_generate_handler(self, file: protogen.File | List[protogen.File]):
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)

        ui_config_file_path = (
                PurePath(__file__).parent.parent.parent / "CodeGenProjects" /
                self.project_name / "data" / "ui_config.yaml")
        ui_coordinates_override_msg_dict: Dict[str, Dict[str, str]] = {}
        if os.path.exists(ui_config_file_path):
            ui_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(ui_config_file_path))
            ui_coordinates_override_msg_dict = ui_config_yaml_dict.get("ui_coordinates")

        output_str = "export const defaultLayouts = [\n"
        for index, message in enumerate(self.layout_msg_list):
            if self.is_option_enabled(message, JsProjectSpecificUtilsPlugin.flux_msg_widget_ui_data_element):
                widget_ui_data_option_value_dict = \
                    self.get_complex_option_value_from_proto(message,
                                                             JsProjectSpecificUtilsPlugin.flux_msg_widget_ui_data_element)

                title_val = widget_ui_data_option_value_dict["i"] if "i" in widget_ui_data_option_value_dict \
                    else convert_camel_case_to_specific_case(message.proto.name)

                # converting python bool values to js bools
                widget_ui_data_list = widget_ui_data_option_value_dict["widget_ui_data"]
                if widget_ui_data_list:
                    # since we will always have single obj in list
                    widget_ui_data = widget_ui_data_list[0]
                    highlight_update = widget_ui_data.get("highlight_update")
                    if highlight_update is not None:
                        widget_ui_data["highlight_update"] = f"{highlight_update}".lower()
                    truncate_date_time = widget_ui_data.get("truncate_date_time")
                    if truncate_date_time is not None:
                        widget_ui_data["truncate_date_time"] = f"{truncate_date_time}".lower()
                widget_ui_data_list_str = json.dumps(widget_ui_data_list)
                for old_item, new_item in [('"true"', 'true'), ('"false"', 'false')]:
                    widget_ui_data_list_str = widget_ui_data_list_str.replace(old_item, new_item)

                output_str += '    { ' + f'i: "{title_val}", '

                msg_coordinates_override = ui_coordinates_override_msg_dict.get(message.proto.name)

                for coordinate in ["x", "y", "w", "h"]:
                    if msg_coordinates_override is None:
                        val: str = widget_ui_data_option_value_dict[coordinate]
                    else:
                        val: str = msg_coordinates_override.get(coordinate)
                        if val is None:
                            err_str = (f"key '{message.proto.name}' in ui_coordinates dict in data/ui_config.yaml "
                                       f"of current project has no key '{coordinate}'")
                            logging.error(err_str)
                            raise Exception(err_str)
                    output_str += f'{coordinate}: {val}, '

                output_str += f'widget_ui_data: {widget_ui_data_list_str}' + \
                              ' },\n'
        output_str += "]\n\n"
        output_str += "export function flux_toggle(value) {\n"
        output_str += "    return !value;\n"
        output_str += "}\n\n"
        output_str += "export function flux_trigger_strat(value) {\n"
        output_str += "    if (['StratState_READY', 'StratState_PAUSED', 'StratState_ERROR'].includes(value)) {\n"
        output_str += "        return 'StratState_ACTIVE';\n"
        output_str += "    } else if ('StratState_ACTIVE' === value) {\n"
        output_str += "        return 'StratState_PAUSED';\n"
        output_str += "    }\n"
        output_str += "}\n"

        output_file_name = "projectSpecificUtils.js"
        return {output_file_name: output_str}


if __name__ == "__main__":
    main(JsProjectSpecificUtilsPlugin)
