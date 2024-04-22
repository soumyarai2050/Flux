#!/usr/bin/env python
import os
from typing import List, Callable
import time
from pathlib import PurePath
import logging

from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
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

    def _load_abbreviated_widget_filter_list(self, abb_msg_name: str,
                                             dependent_or_linked_msg_name_list: List[str]) -> str:
        output_str = f"if (name === '{abb_msg_name}') " + "{\n"
        output_str += f"    filterList.push(...{dependent_or_linked_msg_name_list});\n"
        output_str += "}\n"
        return output_str

    def _get_dependent_layout_msg_name_list(self, dependent_msg_name: str) -> List[str]:
        dependent_msg_name_snake_cased = convert_camel_case_to_specific_case(dependent_msg_name)
        layout_msg_list = [layout_msg.proto.name for layout_msg in self.layout_msg_list]
        if dependent_msg_name in layout_msg_list:
            return [f'{dependent_msg_name_snake_cased}']
        else:
            # dependent_msg_name is not layout type then getting its field's layout type messages
            for root_msg in self.root_msg_list:
                if dependent_msg_name == root_msg.proto.name:
                    dependent_msg_name_list = []
                    for field in root_msg.fields:
                        if field.message is not None and field.message in self.layout_msg_list:
                            meg_name_snake_cased = convert_camel_case_to_specific_case(field.message.proto.name)
                            dependent_msg_name_list.append(f'{meg_name_snake_cased}')
                    if dependent_msg_name_list:
                        return dependent_msg_name_list
                    else:
                        err_str = f"Couldn't find any message type field in message {dependent_msg_name} " \
                                  f"having layout option enabled"
                        logging.exception(err_str)
                        raise Exception(err_str)
                # else handled by for loop's else
            else:
                err_str = f"Couldn't find message {dependent_msg_name} in " \
                          f"either layout_msg_list or root_msg_list"
                logging.exception(err_str)
                raise Exception(err_str)

    def load_abbreviated_widget_filter_list(self, file: protogen.File) -> str:
        output_str = ""
        # handling simple abbreviated types
        if self.simple_abbreviated_filter_layout_msg_list:
            for message in self.simple_abbreviated_filter_layout_msg_list:
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
                dependent_msg_name = self.abbreviated_msg_name_to_dependent_msg_name_dict[message_name]
                dependent_msg_name_list = self._get_dependent_layout_msg_name_list(dependent_msg_name)
                output_str += self._load_abbreviated_widget_filter_list(message_name_snake_cased,
                                                                        dependent_msg_name_list)

        # handling parent abbreviated types
        if self.parent_abbreviated_filter_layout_msg_list:
            for message in self.parent_abbreviated_filter_layout_msg_list:
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
                dependent_msg_name = self.abbreviated_msg_name_to_dependent_msg_name_dict[message_name]
                dependent_msg_name_list = self._get_dependent_layout_msg_name_list(dependent_msg_name)
                linked_msg_name = self.parent_abb_msg_name_to_linked_abb_msg_name_dict[message_name]
                linked_msg_name_snake_cased = convert_camel_case_to_specific_case(linked_msg_name)
                linked_msg_dependent_msg_name = \
                    self.abbreviated_msg_name_to_dependent_msg_name_dict[linked_msg_name]
                linked_msg_dependent_msg_name_list = \
                    self._get_dependent_layout_msg_name_list(linked_msg_dependent_msg_name)
                output_str += self._load_abbreviated_widget_filter_list(message_name_snake_cased,
                                                                        dependent_msg_name_list +
                                                                        [f'{linked_msg_name_snake_cased}'] +
                                                                        linked_msg_dependent_msg_name_list)

        return output_str

    def handle_root_msg_addition_to_layout_templ(self, file: protogen.File):
        output_str = ""
        for index, message in enumerate(self.layout_msg_list):
            message_name = message.proto.name
            message_name_space_sep = convert_camel_case_to_specific_case(message_name, " ", False)
            message_name_case_styled = self.case_style_convert_method(message_name)
            output_str += f"<ToggleIcon title='{message_name_space_sep}' name='{message_name_case_styled}' selected=" + \
                          "{layoutsById.current.hasOwnProperty('"+f"{message_name_case_styled}"+"')} onClick={onToggleWidget}>\n"
            output_str += "    {getIconText('"+f"{message_name_case_styled}"+"')}\n"
            output_str += "</ToggleIcon>\n"
        return output_str

    def handle_show_widget(self, file: protogen.File) -> str:
        output_str = ""
        for index, message in enumerate(self.layout_msg_list):
            message_name = message.proto.name
            message_name_case_styled = self.case_style_convert_method(message_name)
            output_str += "{"+f"layoutsById.current.hasOwnProperty('{message_name_case_styled}') &&\n"
            output_str += "    <Paper \n"
            output_str += "        key='" + f"{message_name_case_styled}'\n"
            output_str += "        id='" + f"{message_name_case_styled}'\n"
            output_str += "        className={`${classes.widget} ${scrollLock." + \
                          f"{message_name_case_styled} ? classes.no_scroll : ''" + "}`}\n"
            output_str += "        onClick={() => onWidgetClick('" + f"{message_name_case_styled}')" + "}\n"
            output_str += "        onDoubleClick={() => onWidgetDoubleClick('" + f"{message_name_case_styled}')" + "}\n"
            output_str += "        data-grid={layoutsById.current." + f"{message_name_case_styled}" + "}>\n"
            output_str += f'        <{message.proto.name}\n'
            output_str += f'            name="{message_name_case_styled}"\n'
            output_str += "            options={"+f"layoutsById.current.{message_name_case_styled}.widget_ui_data"+"}\n"
            output_str += "            chartData={"+ f"layoutsById.current.{message_name_case_styled}.chart_data"+"}\n"
            output_str += "            filters={" + f"layoutsById.current.{message_name_case_styled}.filters" + "}\n"
            output_str += "            onChartDataChange={onChartDataChange}\n"
            output_str += "            onChartDelete={onChartDelete}\n"
            output_str += "            onChangeLayout={onLayoutTypeChange}\n"
            output_str += '            onOverrideChange={onOverrideChange}\n'
            output_str += "            onFiltersChange={onFiltersChange}\n"
            output_str += "            onColumnOrdersChange={onColumnOrdersChange}\n"
            output_str += "            scrollLock={scrollLock." + f"{message_name_case_styled}" + "}\n"
            output_str += f'        />\n'
            output_str += f'    </Paper>\n'
            output_str += '}\n'
        return output_str

    def handle_widget_scroll_lock(self, file: protogen.File):
        output_str = "const [scrollLock, setScrollLock] = useState({\n"
        for index, message in enumerate(self.layout_msg_list):
            message_name = message.proto.name
            message_name_case_styled = self.case_style_convert_method(message_name)
            output_str += f"    {message_name_case_styled}: true,\n"
        output_str += "})\n"
        return output_str

    def output_file_generate_handler(self, file: protogen.File | List[protogen.File]):
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)

        output_file_name = "Layout.jsx"
        py_code_gen_engine_path = None
        if (template_file_name := os.getenv("TEMPLATE_FILE_NAME")) is not None and len(template_file_name) and \
                (py_code_gen_engine_path := os.getenv("PY_CODE_GEN_ENGINE_PATH")) is not None and \
                len(py_code_gen_engine_path):
            template_file_path = PurePath(py_code_gen_engine_path) / PurePath(__file__).parent / template_file_name
        else:
            err_str = f"Env var 'TEMPLATE_FILE_NAME' and 'PY_CODE_GEN_ENGINE_PATH'" \
                      f"received as {template_file_name} and {py_code_gen_engine_path}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.output_file_name_to_template_file_path_dict[output_file_name] = str(template_file_path)

        # sorting created message lists
        self.layout_msg_list.sort(key=lambda message_: message_.proto.name)
        self.simple_abbreviated_filter_layout_msg_list.sort(key=lambda message_: message_.proto.name)

        return {
            output_file_name: {
                "add_imports": self.handle_imports(file),
                "add_widget_scroll_lock": self.handle_widget_scroll_lock(file),
                "load_abbreviated_widget_filter_list": self.load_abbreviated_widget_filter_list(file),
                "add_root_in_jsx_layout": self.handle_root_msg_addition_to_layout_templ(file),
                "add_show_widget": self.handle_show_widget(file),
            }
        }


if __name__ == "__main__":
    main(JsxLayoutGenPlugin)
