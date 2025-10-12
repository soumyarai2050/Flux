#!/usr/bin/env python
import json
import os
from typing import List, Callable, Dict, Final
import time
import logging
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case, YAMLConfigurationManager


class JsProjectSpecificUtilsPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to generate projectSpecificUtils.js file from proto schema.
    """
    indentation_space: Final[str] = "    "

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def output_file_generate_handler(self, file: protogen.File | List[protogen.File]):
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)

        project_dir = os.getenv("PROJECT_DIR")
        if project_dir is None or not project_dir:
            err_str = f"env var 'PROJECT_DIR' received as {project_dir}"
            logging.exception(err_str)
            raise Exception(err_str)

        ui_config_file_path = PurePath(project_dir) / "data" / "ui_config.yaml"
        ui_coordinates_override_msg_dict: Dict[str, Dict[str, str]] = {}
        if os.path.exists(ui_config_file_path):
            ui_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(ui_config_file_path))
            ui_coordinates_override_msg_dict = ui_config_yaml_dict.get("ui_coordinates")

        # sorting created message lists
        self.layout_msg_list.sort(key=lambda message_: message_.proto.name)

        # Add imports for dynamic layout utilities
        output_str = "import { addDynamicLayouts, getAllLayouts as getCombinedLayouts } from './utils/dynamicSchemaUtils/layoutUtils';\n\n"
        output_str += "export const staticLayouts = [\n"
        for index, message in enumerate(self.layout_msg_list):
            if self.is_option_enabled(message, JsProjectSpecificUtilsPlugin.flux_msg_widget_ui_data_element):
                widget_ui_data_option_value_dict = \
                    self.handle_n_get_ui_widget_data_option_values_having_msg_name(message,
                                                                                   self.message_name_to_message_dict)


                title_val = widget_ui_data_option_value_dict["i"] if "i" in widget_ui_data_option_value_dict \
                    else convert_camel_case_to_specific_case(message.proto.name)

                # converting python bool values to js bools
                widget_ui_data_list = widget_ui_data_option_value_dict["widget_ui_data"]
                if widget_ui_data_list:
                    # since we will always have single obj in list
                    widget_ui_data_dict = widget_ui_data_list[0]
                    for key, value in widget_ui_data_dict.items():
                        if value is not None:
                            widget_ui_data_dict[key] = value
                    # highlight_update = widget_ui_data.get("highlight_update")
                    # if highlight_update is not None:
                    #     widget_ui_data["highlight_update"] = f"{highlight_update}".lower()
                    # truncate_date_time = widget_ui_data.get("truncate_date_time")
                    # if truncate_date_time is not None:
                    #     widget_ui_data["truncate_date_time"] = f"{truncate_date_time}".lower()
                # widget_ui_data_list_str = json.dumps(widget_ui_data_list)
                # for old_item, new_item in [('"true"', 'true'), ('"false"', 'false'), ('"True"', 'true'), ('"False"', 'false')]:
                #     widget_ui_data_list_str = widget_ui_data_list_str.replace(old_item, new_item)

                # output_str += '    { ' + f'i: "{title_val}", '

                widget_ui_option_dict = {
                    "i": title_val,
                    "widget_ui_data": widget_ui_data_list
                }

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
                    widget_ui_option_dict[coordinate] = val

                    # output_str += f'{coordinate}: {val}, '

                for key, value in widget_ui_data_option_value_dict.items():
                    if key in ["i", "x", "y", "w", "h", "widget_ui_data"]:
                        continue
                    if value is not None:
                        widget_ui_option_dict[key] = value

                widget_ui_option_dict_str = json.dumps(widget_ui_option_dict)
                for old_item, new_item in [('"true"', 'true'), ('"false"', 'false'), ('"True"', 'true'), ('"False"', 'false')]:
                    widget_ui_option_dict_str = widget_ui_option_dict_str.replace(old_item, new_item)

                # output_str += f'widget_ui_data: {widget_ui_data_list_str}' + \
                #               ' },\n'
                output_str += f"{widget_ui_option_dict_str}, \n"

        output_str += "];\n"

        # Add dynamic layout exports
        output_str += "// Export static layouts separately for reference\n"
        output_str += "export const getStaticLayouts = () => staticLayouts;\n\n"
        output_str += "// Export function to get only dynamic layouts\n"
        output_str += "export const getDynamicLayouts = (schemaFromStore = null) => addDynamicLayouts(schemaFromStore, staticLayouts);\n\n"
        output_str += "// Export function to get combined layouts at runtime\n"
        output_str += "export const getAllLayouts = (schemaFromStore = null) => getCombinedLayouts(staticLayouts, schemaFromStore);\n\n"

        output_str += "export function flux_toggle(value) {\n"
        output_str += JsProjectSpecificUtilsPlugin.indentation_space + "return !value;\n"
        output_str += "}\n\n"
        output_str += "export function flux_trigger_strat(value) {\n"
        output_str += JsProjectSpecificUtilsPlugin.indentation_space + "if (['StratState_READY', 'StratState_PAUSED', 'StratState_ERROR'].includes(value)) {\n"
        output_str += JsProjectSpecificUtilsPlugin.indentation_space*2 + "return 'StratState_ACTIVE';\n"
        output_str += JsProjectSpecificUtilsPlugin.indentation_space + "} else if ('StratState_ACTIVE' === value) {\n"
        output_str += JsProjectSpecificUtilsPlugin.indentation_space*2 + "return 'StratState_PAUSED';\n"
        output_str += JsProjectSpecificUtilsPlugin.indentation_space + "}\n"
        output_str += "}\n"

        output_file_name = "projectSpecificUtils.js"
        return {output_file_name: output_str}


if __name__ == "__main__":
    main(JsProjectSpecificUtilsPlugin)
