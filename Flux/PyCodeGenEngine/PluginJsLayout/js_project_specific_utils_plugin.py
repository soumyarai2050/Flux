#!/usr/bin/env python
import os
from typing import List, Callable
import time
import logging

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
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

        output_str = "export function getLayout() {\n"
        output_str += "    const layout = [\n"
        for index, message in enumerate(self.layout_msg_list):
            if self.is_option_enabled(message, JsProjectSpecificUtilsPlugin.flux_msg_widget_ui_data):
                widget_ui_data_option_value_dict = \
                    self.get_complex_option_set_values(message,
                                                       JsProjectSpecificUtilsPlugin.flux_msg_widget_ui_data)

                title_val = widget_ui_data_option_value_dict["i"] \
                    if "i" in widget_ui_data_option_value_dict else convert_camel_case_to_specific_case(message.proto.name)
                output_str += '        {' + f' i: "{title_val}", ' \
                                            f'x: {widget_ui_data_option_value_dict["x"].strip()}, ' \
                                            f'y: {widget_ui_data_option_value_dict["y"].strip()}, ' \
                                            f'w: {widget_ui_data_option_value_dict["w"].strip()}, ' \
                                            f'h: {widget_ui_data_option_value_dict["h"].strip()}, ' \
                                            f'layout: "{widget_ui_data_option_value_dict["layout"].strip()}", ' \
                                            f'enable_override: [], disable_override: [] ' + '},\n'
        output_str += "    ]\n"
        output_str += "    return layout;\n"
        output_str += "}\n\n"
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
