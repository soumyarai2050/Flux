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
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.generate
        ]
        if (output_file_name := os.getenv("OUTPUT_FILE_NAME")) is not None:
            self.output_file_name = output_file_name
        else:
            err_str = f"Env var 'OUTPUT_FILE_NAME' " \
                      f"received as {output_file_name}"
            logging.exception(err_str)
            raise Exception(err_str)

    def generate(self, file: protogen.File) -> str:
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)

        output_str = "export function getLayout() {\n"
        output_str += "    const layout = [\n"
        for index, message in enumerate(self.layout_msg_list):
            if JsProjectSpecificUtilsPlugin.flux_msg_widget_ui_data in str(message.proto.options):
                widget_ui_data_options_value_list_of_dict = \
                    self.get_complex_option_values_as_list_of_dict(message,
                                                                   JsProjectSpecificUtilsPlugin.flux_msg_widget_ui_data)
                # since widget_ui_data option is non-repeated type
                widget_ui_data_options_value = widget_ui_data_options_value_list_of_dict[0]

                title_val = widget_ui_data_options_value["i"] \
                    if "i" in widget_ui_data_options_value else convert_camel_case_to_specific_case(message.proto.name)
                output_str += '        {' + f' i: "{title_val}", ' \
                                            f'x: {widget_ui_data_options_value["x"].strip()}, ' \
                                            f'y: {widget_ui_data_options_value["y"].strip()}, ' \
                                            f'w: {widget_ui_data_options_value["w"].strip()}, ' \
                                            f'h: {widget_ui_data_options_value["h"].strip()}, ' \
                                            f'layout: "{widget_ui_data_options_value["layout"].strip()}", ' \
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

        return output_str


if __name__ == "__main__":
    main(JsProjectSpecificUtilsPlugin)
