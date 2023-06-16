#!/usr/bin/env python
import os
from typing import List, Callable
import time
from pathlib import PurePath
import logging

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case


class JsxLayoutGenPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to convert proto schema to required jsx layout script
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_imports(self, file: protogen.File) -> str:
        output_str = ""
        for message in self.layout_msg_list:
            output_str += f"import {message.proto.name} from '../widgets/{message.proto.name}';\n"
        return output_str

    def handle_widget_list(self, file: protogen.File) -> str:
        output_str = ""
        for message in self.layout_msg_list:
            message_name_case_styled = self.case_style_convert_method(message.proto.name)
            if message != self.layout_msg_list[-1]:
                output_str += f"{message_name_case_styled}: true,\n"
            else:
                output_str += f"{message_name_case_styled}: true\n"
        return output_str

    def handle_update_data(self, file: protogen.File) -> str:
        output_str = ""
        if self.simple_abbreviated_filter_layout_msg_list:
            temp_str = ""
            for message in self.simple_abbreviated_filter_layout_msg_list:
                message_name_camel_cased = convert_camel_case_to_specific_case(message.proto.name)
                temp_str += f"name === '{message_name_camel_cased}' "
                if message != self.simple_abbreviated_filter_layout_msg_list[-1]:
                    temp_str += "|| "
            output_str += f"if ({temp_str}&& show[name]) " + "{\n"
            for message in self.layout_msg_list:
                if message not in self.root_msg_list and message not in self.simple_abbreviated_filter_layout_msg_list:
                    message_name_camel_cased = convert_camel_case_to_specific_case(message.proto.name)
                    output_str += f"    updatedData['{message_name_camel_cased}'] = false;\n"
                # else not required: avoiding other than dependent type layout messages
            output_str += "}\n"

        return output_str

    def handle_root_msg_addition_to_layout_templ(self, file: protogen.File):
        output_str = ""
        for index, message in enumerate(self.layout_msg_list):
            message_name = message.proto.name
            message_name_space_sep = convert_camel_case_to_specific_case(message_name, " ", False)
            message_name_case_styled = self.case_style_convert_method(message_name)
            output_str += f"<ToggleIcon title='{message_name_space_sep}' name='{message_name_case_styled}' selected=" + \
                          "{show."+f"{message_name_case_styled}"+"} onClick={onToggleWidget}>\n"
            output_str += "    {getIconText('"+f"{message_name_case_styled}"+"')}\n"
            output_str += "</ToggleIcon>\n"
        return output_str

    def handle_show_widget(self, file: protogen.File) -> str:
        output_str = ""
        for index, message in enumerate(self.layout_msg_list):
            message_name = message.proto.name
            message_name_case_styled = self.case_style_convert_method(message_name)
            output_str += "{"+f"show.{message_name_case_styled} &&\n"
            output_str += "    <Paper key='"+f"{message_name_case_styled}' id='{message_name_case_styled}'" + \
                          " className={classes.widget} data-grid={getLayoutById("+f"'{message_name_case_styled}'"+")}>\n"
            output_str += f'        <{message.proto.name}\n'
            output_str += f'            name="{message_name_case_styled}"\n'
            output_str += "            layout={"+f"getLayoutById('{message_name_case_styled}').layout"+"}\n"
            output_str += "            onChangeLayout={onWidgetLayoutChange}\n"
            output_str += "            enableOverride={getLayoutById('"+f"{message_name_case_styled}"+"')." \
                          "enable_override}\n"
            output_str += "            disableOverride={getLayoutById('"+f"{message_name_case_styled}"+"')." \
                          "disable_override}\n"
            output_str += '            onOverrideChange={onWidgetOverrideChange}\n'
            output_str += f'        />\n'
            output_str += f'    </Paper>\n'
            output_str += '}\n'
        return output_str

    def output_file_generate_handler(self, file: protogen.File):
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)

        output_file_name = "Layout.jsx"
        py_code_gen_engine_path = None
        if (template_file_name := os.getenv("TEMPLATE_FILE_NAME")) is not None and \
                (py_code_gen_engine_path := os.getenv("PY_CODE_GEN_ENGINE_PATH")) is not None:
            template_file_path = PurePath(py_code_gen_engine_path) / PurePath(__file__).parent / template_file_name
        else:
            err_str = f"Env var 'TEMPLATE_FILE_NAME' and 'PY_CODE_GEN_ENGINE_PATH'" \
                      f"received as {template_file_name} and {py_code_gen_engine_path}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.output_file_name_to_template_file_path_dict[output_file_name] = str(template_file_path)
        return {
            output_file_name: {
                "add_imports": self.handle_imports(file),
                "add_widget_list": self.handle_widget_list(file),
                "handle_update_data": self.handle_update_data(file),
                "add_root_in_jsx_layout": self.handle_root_msg_addition_to_layout_templ(file),
                "add_show_widget": self.handle_show_widget(file)
            }
        }

if __name__ == "__main__":
    main(JsxLayoutGenPlugin)
