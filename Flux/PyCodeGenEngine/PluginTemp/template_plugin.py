#!/usr/bin/env python
import logging
import os
import time
from pathlib import PurePath

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main


class TemplatePlugin(BaseProtoPlugin):
    """
    Plugin to generate temp_plugin files
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def get_sample_output_content(self, file):
        # some basic attributes to access proto data
        json_sample_output = f'"""\n'
        json_sample_output += f"Proto File Name: {file.proto.name}\n\n"
        json_sample_output += f"List of all messages and their field with their cardinality and kind:\n"
        for message in file.messages:
            json_sample_output += f"Message Name: {message.proto.name}:\n"
            # checking if option FluxMsgJsonRoot is enabled or not on (taking this option for example,
            # all other complex options are accessed using same way)
            # for simple options use same as mentioned in fld lvl option access intro
            json_sample_output += f"    if {TemplatePlugin.flux_msg_json_root} option enabled: " \
                                  f"{TemplatePlugin.is_option_enabled(message, TemplatePlugin.flux_msg_json_root)}\n"
            json_sample_output += \
                f"    option value if present: " \
                f"{TemplatePlugin.get_complex_option_set_values(message, TemplatePlugin.flux_msg_json_root)}\n"
            for field in message.fields:
                json_sample_output += f"    Field Name: {field.proto.name}\n"
                json_sample_output += f"        default value (if any): {self.get_field_default_value(field)}\n"
                json_sample_output += f"        kind: {field.kind.name}\n"
                json_sample_output += f"        cardinality: {field.cardinality.name}\n"
                # Using FluxFldHelp option for example, all other simple types are accessed using same way for
                # msg, fld and file levels.
                json_sample_output += f"        if option {TemplatePlugin.flux_fld_help} set: " \
                                      f"{TemplatePlugin.is_option_enabled(field, TemplatePlugin.flux_fld_help)}\n"
                json_sample_output += \
                    f"        option value if is set: " \
                    f"{TemplatePlugin.get_non_repeated_valued_custom_option_value(field, TemplatePlugin.flux_fld_help)}\n"
                json_sample_output += "\n"
            json_sample_output += "\n"
        json_sample_output += f'"""'
        return json_sample_output

    def get_sample_output_content_for_insert_points(self, file):
        """
        returning dict of key-value of insertion points to replacing content
        """
        proto_file_name: str = str(file.proto.name).split(".")[0]
        py_code_gen_engine_path = None
        if (template_file_name := os.getenv("TEMPLATE_FILE_NAME")) is not None and \
                (py_code_gen_engine_path := os.getenv("PY_CODE_GEN_ENGINE_PATH")) is not None:
            template_file_path = PurePath(py_code_gen_engine_path) / PurePath(__file__).parent / template_file_name
        else:
            err_str = f"Env var 'TEMPLATE_FILE_NAME' and 'PY_CODE_GEN_ENGINE_PATH'" \
                      f"received as {template_file_name} and {py_code_gen_engine_path}"
            logging.exception(err_str)
            raise Exception(err_str)
        output_file_name = f"{proto_file_name}_temp_plugin_out_with_insert_points.txt"

        # IMPORTANT: below data-member needs to be updated with each output file to its
        # corresponding template file path if template output needs to be generated.
        self.output_file_name_to_template_file_path_dict[output_file_name] = str(template_file_path)
        return {
            "insert_point_1": "Text replaced by insertion_point_1",
            "insert_point_2": "Text replaced by insertion_point_2"
        }

    def output_file_generate_handler(self, file: protogen.File):
        """
        Abstract method which is responsible for generating outputs from derived plugin class.
        Must return dict having:
        1. output_file_name to output_content key-value pair - for non-insertion point based template output
        2. output_file_name to output_content_dict key-value pair, where output_content_dict must have
        insertion_point to replacing_content key-value pair - for non-insertion point based template output
        """
        proto_file_name: str = str(file.proto.name).split(".")[0]
        output_json = {
            # If generated file is generated without any template with insert points in it,
            # it should be like below as output_file_name - output_file_content key-value pair
            f"{proto_file_name}_temp_plugin_out.py": self.get_sample_output_content(file),

            # If generated file is generated with template having insert points in it,
            # it should be like below as output_file_name - content_dict key-value pair,
            # where content_dict is each insertion_point-replacing_text as key-value pair
            f"{proto_file_name}_temp_plugin_out_with_insert_points.txt":
                self.get_sample_output_content_for_insert_points(file),
        }
        return output_json


if __name__ == "__main__":
    main(TemplatePlugin)
