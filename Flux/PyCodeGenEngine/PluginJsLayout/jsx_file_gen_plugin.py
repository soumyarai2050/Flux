#!/usr/bin/env python
import logging
import os
from typing import List, Callable, Dict, Final, ClassVar
import time

# project imports
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main
from FluxPythonUtils.scripts.general_utility_functions import convert_to_camel_case
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case


class JsxFileGenPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to generate jsx file for ORM root messages
    -- Types:
    1. AbbreviationMerge Type - widget_ui option enabled models with abbreviated option
    2. Root - widget_ui option enabled models with JsonRoot(DB model) option + widget_ui option with is_repeated as False or None
    3. Repeated root - widget_ui option enabled models with JsonRoot(DB model) option + widget_ui option with is_repeated as True
    4. Non-Root - widget_ui option enabled models without JsonRoot(DB model) option

    """
    indentation_space: Final[str] = "    "
    root_model: str = 'RootModel'
    repeated_root_model: str = 'RepeatedRootModel'
    non_root_model: str = 'NonRootModel'
    abbreviated_merge_model: str = 'AbbreviationMergeModel'
    chart_model: str = 'ChartModel'

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.abbreviated_dependent_message_name: str | None = None

    def get_model_type_str_for_model_type(self, model_type: str):
        match model_type:
            case JsxFileGenPlugin.root_type:
                model_type_str = JsxFileGenPlugin.root_model
            case JsxFileGenPlugin.repeated_root_type:
                model_type_str = JsxFileGenPlugin.repeated_root_model
            case JsxFileGenPlugin.non_root_type:
                model_type_str = JsxFileGenPlugin.non_root_model
            case JsxFileGenPlugin.abbreviated_merge_type:
                model_type_str = JsxFileGenPlugin.abbreviated_merge_model
            case JsxFileGenPlugin.chart_type:
                model_type_str = JsxFileGenPlugin.chart_model
            case other:
                raise RuntimeError(f"Unknown model type: {other}")
        return model_type_str

    def get_root_msg_for_non_root_type(self, non_root_msg: protogen.Message):
        for msg in self.root_msg_list:
            if non_root_msg.proto.name in [fld.message.proto.name for fld in msg.fields if
                                      fld.message is not None]:
                root_message = msg
                return root_message
            # else not required: Avoiding msg not having any field of type message
        else:
            err_str = f"Could not find {non_root_msg.proto.name} as datatype of field in any root " \
                      f"message in proto"
            logging.exception(err_str)
            raise Exception(err_str)

    def handle_import_output(self, message: protogen.Message, model_type: str) -> str:
        output_str = "import { withModelData } from '../hoc/withModelData';\n"
        model_type_str = self.get_model_type_str_for_model_type(model_type)
        output_str += f"import {model_type_str} from '../containers/{model_type_str}';\n\n"
        return output_str

    def handle_model_doc_str(self, message_name: str, model_type: str):
        output_str = "/**\n"
        output_str += f" * {message_name} component acts as a wrapper for managing data source(s).\n"
        output_str += " * @returns {JSX.Element} The "+f"{message_name} component.\n"
        output_str += " */\n\n"
        return output_str

    def handle_model_declaration(self, message: protogen.Message, model_type: str):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        model_type_str = self.get_model_type_str_for_model_type(model_type)
        is_abbreviation_source: bool = False
        root_message_name_snake_cased: str | None = None
        for abb_msg in self.abbreviated_merge_layout_msg_list:
            dependent_msg_list = self.msg_name_to_dependent_msg_name_list_dict.get(abb_msg.proto.name)
            if model_type == JsxFileGenPlugin.root_type:
                if message_name in dependent_msg_list:
                    # if some abbreviated message is dependent on this message
                    is_abbreviation_source = True
            elif model_type == JsxFileGenPlugin.non_root_type:
                root_msg = self.get_root_msg_for_non_root_type(message)
                root_message_name = root_msg.proto.name
                root_message_name_snake_cased = convert_camel_case_to_specific_case(root_message_name)
                if root_message_name in dependent_msg_list:
                    # if some abbreviated message is dependent on this message
                    is_abbreviation_source = True
            # else not required: ignore if this message itself is abbreviated type
        dependent_msg_name_list: List[str] = self.msg_name_to_dependent_msg_name_list_dict.get(message_name)
        output_str = f"const {message_name} = withModelData({model_type_str}, " + "{\n"
        output_str += JsxFileGenPlugin.indentation_space + f"modelName: '{message_name_snake_cased}',\n"
        if dependent_msg_name_list:
            output_str += JsxFileGenPlugin.indentation_space + f"dataSources: [\n"
            for dependent_msg_name in dependent_msg_name_list:
                dependent_msg_name_snake_cased = convert_camel_case_to_specific_case(dependent_msg_name)
                output_str += JsxFileGenPlugin.indentation_space*2 + f"'{dependent_msg_name_snake_cased}',\n"
            output_str += JsxFileGenPlugin.indentation_space + "],\n"
        else:
            output_str += JsxFileGenPlugin.indentation_space + f"dataSources: null,\n"
        if is_abbreviation_source:
            output_str += JsxFileGenPlugin.indentation_space + f"isAbbreviationSource: true,\n"
        if root_message_name_snake_cased is not None:
            output_str += JsxFileGenPlugin.indentation_space + f"modelRootName: '{root_message_name_snake_cased}',\n"
        output_str += "})\n\n"
        return output_str

    def handle_jsx_file_output(self, message: protogen.Message, model_type: str) -> str:
        message_name = message.proto.name
        output_str = self.handle_import_output(message, model_type)
        output_str += self.handle_model_doc_str(message_name, model_type)
        output_str += self.handle_model_declaration(message, model_type)
        output_str += f"export default {message_name};\n"

        return output_str

    def get_model_type_from_widget_ui_data(self, message: protogen.Message) -> str | None:
        """Extract model_type from widget_ui_data_element option"""
        if self.is_option_enabled(message, self.flux_msg_widget_ui_data_element):
            widget_ui_data_dict = self.get_complex_option_value_from_proto(
                message, self.flux_msg_widget_ui_data_element)
            return widget_ui_data_dict.get("model_type")
        return None

    def output_file_generate_handler(self, file: protogen.File | List[protogen.File]):
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)
        output_dict: Dict[str, str] = {}

        # sorting created message lists
        self.layout_msg_list.sort(key=lambda message_: message_.proto.name)
        self.root_msg_list.sort(key=lambda message_: message_.proto.name)

        for message in self.layout_msg_list:
            message_name = message.proto.name
            output_dict_key = f"{message_name}.jsx"

            # Check for explicit model_type in widget_ui_data_element
            explicit_model_type = self.get_model_type_from_widget_ui_data(message)

            if explicit_model_type == "CHART":
                output_str = self.handle_jsx_file_output(message, JsxFileGenPlugin.chart_type)
            # Abbreviated Case
            elif message in self.abbreviated_merge_layout_msg_list:
                self.root_message = message
                for field in message.fields:
                    # It's assumed that abbreviated layout type will also have  some field having flux_fld_abbreviated
                    # set to get abbreviated dependent message name - verifying it
                    if self.is_option_enabled(field, JsxFileGenPlugin.flux_fld_abbreviated):
                        fld_abbreviated_option_value = \
                            self.get_simple_option_value_from_proto(field,
                                                                    JsxFileGenPlugin.flux_fld_abbreviated)[1:]
                        break
                else:
                    err_str = f"Could not find any field having {JsxFileGenPlugin.flux_fld_abbreviated} option set in " \
                              f"message {message_name}"
                    logging.exception(err_str)
                    raise Exception(err_str)
                output_str = self.handle_jsx_file_output(message, JsxFileGenPlugin.abbreviated_merge_type)
            else:
                # Root Type
                if message in self.root_msg_list:
                    if message in self.repeated_msg_list:
                        output_str = self.handle_jsx_file_output(message, JsxFileGenPlugin.repeated_root_type)
                    else:
                        output_str = self.handle_jsx_file_output(message, JsxFileGenPlugin.root_type)
                # Non Root Type
                else:
                    output_str = self.handle_jsx_file_output(message, JsxFileGenPlugin.non_root_type)

            output_dict[output_dict_key] = output_str

        return output_dict


if __name__ == "__main__":
    main(JsxFileGenPlugin)
