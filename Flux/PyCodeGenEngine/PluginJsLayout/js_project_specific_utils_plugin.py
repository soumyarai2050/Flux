#!/usr/bin/env python
import os
from typing import List, Callable
import time
import logging

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case


class JsProjectSpecificUtilsPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to generate projectSpecificUtils.js file from proto schema.
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def output_file_generate_handler(self, file: protogen.File):
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)

        output_str = "export const defaultLayouts = [\n"
        for index, message in enumerate(self.layout_msg_list):
            if self.is_option_enabled(message, JsProjectSpecificUtilsPlugin.flux_msg_widget_ui_data_element):
                widget_ui_data_option_value_dict = \
                    self.get_complex_option_set_values(message,
                                                       JsProjectSpecificUtilsPlugin.flux_msg_widget_ui_data_element)

                title_val = widget_ui_data_option_value_dict["i"] if "i" in widget_ui_data_option_value_dict \
                    else convert_camel_case_to_specific_case(message.proto.name)
                output_str += '    { ' + \
                              f'i: "{title_val}", ' + \
                              f'x: {widget_ui_data_option_value_dict["x"]}, ' + \
                              f'y: {widget_ui_data_option_value_dict["y"]}, ' + \
                              f'w: {widget_ui_data_option_value_dict["w"]}, ' + \
                              f'h: {widget_ui_data_option_value_dict["h"]}, ' + \
                              f'widget_ui_data: {widget_ui_data_option_value_dict["widget_ui_data"]}' + \
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
