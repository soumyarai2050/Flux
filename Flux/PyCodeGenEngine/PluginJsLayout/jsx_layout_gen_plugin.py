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


class JsxLayoutGenPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to convert proto schema to required jsx layout script
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.insertion_point_key_list: List[str] = [
            "add_imports",
            "add_widget_list",
            "add_root_in_jsx_layout",
            "add_show_widget"
        ]
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.handle_imports,
            self.handle_widget_list,
            self.handle_root_msg_addition_to_layout_templ,
            self.handle_show_widget
        ]
        template_file_name = None
        if (output_file_name := os.getenv("OUTPUT_FILE_NAME")) is not None and \
                (template_file_name := os.getenv("TEMPLATE_FILE_NAME")) is not None:
            self.output_file_name = output_file_name
            self.template_file_path = os.path.join(self.base_dir_path, "misc", template_file_name)
        else:
            err_str = f"Env var 'OUTPUT_FILE_NAME' and 'TEMPLATE_FILE_NAME' " \
                      f"received as {output_file_name} and {template_file_name}"
            logging.exception(err_str)
            raise Exception(err_str)

    def handle_imports(self, file: protogen.File) -> str:
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)
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

    def handle_root_msg_addition_to_layout_templ(self, file: protogen.File):
        output_str = ""
        for index, message in enumerate(self.layout_msg_list):
            message_name = message.proto.name
            message_name_space_sep = self.convert_camel_case_to_specific_case(message_name, " ", False)
            message_name_case_styled = self.case_style_convert_method(message_name)
            output_str += f"<ToggleIcon title='{message_name_space_sep}' name='{message_name_case_styled}' selected=" + \
                          "{show."+f"{message_name_case_styled}"+"} onClick={onToggleWidget}>\n"
            output_str += "    {getIconText('"+f"{message_name_case_styled}"+"')}\n"
            output_str += "    {/* <Widgets className={classes.icon} fontSize='large' /> */}\n"
            output_str += "</ToggleIcon>\n"
        return output_str

    def handle_show_widget(self, file: protogen.File) -> str:
        output_str = ""
        for index, message in enumerate(self.layout_msg_list):
            message_name = message.proto.name
            message_name_case_styled = self.case_style_convert_method(message_name)
            output_str += "{"+f"show.{message_name_case_styled} &&\n"
            output_str += "    <Paper key='"+f"{message_name_case_styled}'" + \
                          " className={classes.widget} data-grid={getLayoutById("+f"'{message_name_case_styled}'"+")}>\n"
            output_str += f'        <{message.proto.name} name="{message_name_case_styled}"\n'
            output_str += f'        />\n'
            output_str += f'   </Paper>\n'
            output_str += '}\n'
        return output_str


if __name__ == "__main__":
    main(JsxLayoutGenPlugin)
