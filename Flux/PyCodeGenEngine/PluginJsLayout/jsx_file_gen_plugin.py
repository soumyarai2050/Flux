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
        message_name = message.proto.name
        message_name_camel_cased = convert_to_camel_case(message_name)
        output_str = "import React, { useMemo } from 'react';\n"
        output_str += "import { useSelector } from 'react-redux';\n"
        output_str += "import PropTypes from 'prop-types';\n"
        output_str += "import { getServerUrl, getModelSchema } from '../utils';\n"
        output_str += "import * as Selectors from '../selectors';\n"
        if model_type == JsxFileGenPlugin.non_root_type:
            root_msg = self.get_root_msg_for_non_root_type(message)
            root_message_name = root_msg.proto.name
            root_message_name_camel_cased = convert_to_camel_case(root_message_name)
            output_str += "import { actions as ModelActions } from '../features/"+f"{root_message_name_camel_cased}Slice';\n"
        else:
            output_str += "import { actions as ModelActions } from '../features/"+f"{message_name_camel_cased}Slice';\n"
        if message_name in self.msg_name_to_dependent_msg_name_list_dict:
            dependent_msg_name_list: List[str] = self.msg_name_to_dependent_msg_name_list_dict[message_name]
            for dependent_msg_name in dependent_msg_name_list:
                dependent_message_name_camel_cased = convert_to_camel_case(dependent_msg_name)
                output_str += ("import { actions as "+f"{dependent_msg_name}"+"Actions } "+
                               f"from '../features/{dependent_message_name_camel_cased}Slice';\n")

        model_type_str = self.get_model_type_str_for_model_type(model_type)
        output_str += f"import {model_type_str} from '../containers/{model_type_str}';\n\n"

        return output_str

    def handle_model_doc_str(self, message_name: str, model_type: str):
        output_str = "/**\n"
        if model_type == JsxFileGenPlugin.abbreviated_merge_type:
            output_str += f" * {message_name} component acts as a wrapper for managing strat collection data sources.\n"
        else:
            output_str += f" * {message_name} component.\n"
        output_str += " * @returns {JSX.Element} The "+f"{message_name} component.\n"
        output_str += " */\n\n"
        return output_str

    def handle_model_declaration(self, message: protogen.Message, model_type: str):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f"const MODEL_NAME = '{message_name_snake_cased}';\n\n"
        output_str += f"const {message_name} = () => "+"{\n"
        output_str += JsxFileGenPlugin.indentation_space + "const { schema, schemaCollections } = useSelector((state) => state.schema);\n\n"
        output_str += JsxFileGenPlugin.indentation_space + "const modelDataSource = useMemo(() => {\n"
        output_str += JsxFileGenPlugin.indentation_space*2 + "const modelName = MODEL_NAME;\n"
        output_str += JsxFileGenPlugin.indentation_space*2 + "const modelSchema = getModelSchema(modelName, schema);\n"
        output_str += JsxFileGenPlugin.indentation_space*2 + "return {\n"
        output_str += JsxFileGenPlugin.indentation_space*3 + "name: modelName,\n"
        output_str += JsxFileGenPlugin.indentation_space*3 + "actions: ModelActions,\n"
        output_str += JsxFileGenPlugin.indentation_space*3 + "schema: modelSchema,\n"
        output_str += JsxFileGenPlugin.indentation_space*3 + "url: getServerUrl(modelSchema),\n"
        # adding attribute telling some abbreviated msg is dependent on this message
        for abb_msg in self.abbreviated_merge_layout_msg_list:
            dependent_msg_list = self.msg_name_to_dependent_msg_name_list_dict.get(abb_msg.proto.name)
            if model_type == JsxFileGenPlugin.root_type:
                if message_name in dependent_msg_list:
                    # if some abbreviated message is dependent on this message
                    output_str += JsxFileGenPlugin.indentation_space * 2 + f"isAbbreviationSource: true,\n"
            elif model_type == JsxFileGenPlugin.non_root_type:
                root_msg = self.get_root_msg_for_non_root_type(message)
                root_message_name = root_msg.proto.name
                if root_message_name in dependent_msg_list:
                    # if some abbreviated message is dependent on this message
                    output_str += JsxFileGenPlugin.indentation_space*3 + f"isAbbreviationSource: true,\n"
            # else not required: ignore if this message itself is abbreviated type
        output_str += JsxFileGenPlugin.indentation_space * 3 + "fieldsMetadata: schemaCollections[modelName],\n"
        if model_type == JsxFileGenPlugin.non_root_type:
            root_msg = self.get_root_msg_for_non_root_type(message)
            root_message_name = root_msg.proto.name
            output_str += JsxFileGenPlugin.indentation_space*3 + f"selector: Selectors.select{root_message_name}\n"
        else:
            output_str += JsxFileGenPlugin.indentation_space*3 + f"selector: Selectors.select{message_name}\n"
        output_str += JsxFileGenPlugin.indentation_space*2 + "}\n"
        output_str += JsxFileGenPlugin.indentation_space + "}, [schema, schemaCollections]);\n\n"
        dependent_msg_name_list: List[str] = self.msg_name_to_dependent_msg_name_list_dict.get(message_name)
        if dependent_msg_name_list:
            if model_type == JsxFileGenPlugin.abbreviated_merge_type:
                output_str += JsxFileGenPlugin.indentation_space + "const dataSources = useMemo(() => {\n"
                output_str += JsxFileGenPlugin.indentation_space * 2 + "const dataSourceDict = {\n"
                for dependent_msg_name in dependent_msg_name_list:
                    dependent_msg_name_snake_cased: str = convert_camel_case_to_specific_case(dependent_msg_name)
                    output_str += (JsxFileGenPlugin.indentation_space * 3 + f"'{dependent_msg_name_snake_cased}': " +
                                   "{ actions: " + f"{dependent_msg_name}Actions, selector: Selectors.select{dependent_msg_name}" + " },\n")
                output_str += JsxFileGenPlugin.indentation_space * 2 + "}\n"
                output_str += JsxFileGenPlugin.indentation_space * 2 + "return Object.keys(dataSourceDict).map((dataSourceName) => {\n"
                output_str += JsxFileGenPlugin.indentation_space * 3 + "const { actions, selector } = dataSourceDict[dataSourceName];\n"
                output_str += JsxFileGenPlugin.indentation_space * 3 + "const dataSourceSchema = getModelSchema(dataSourceName, schema);\n"
                output_str += JsxFileGenPlugin.indentation_space * 3 + "return {\n"
                output_str += JsxFileGenPlugin.indentation_space * 4 + "name: dataSourceName,\n"
                output_str += JsxFileGenPlugin.indentation_space * 4 + f"actions: actions,\n"
                output_str += JsxFileGenPlugin.indentation_space * 4 + "schema: dataSourceSchema,\n"
                output_str += JsxFileGenPlugin.indentation_space * 4 + "url: getServerUrl(dataSourceSchema),\n"
                output_str += JsxFileGenPlugin.indentation_space * 4 + "fieldsMetadata: schemaCollections[dataSourceName],\n"
                output_str += JsxFileGenPlugin.indentation_space * 4 + f"selector: selector\n"
                output_str += JsxFileGenPlugin.indentation_space * 3 + "}\n"
                output_str += JsxFileGenPlugin.indentation_space * 2 + "})\n"
                output_str += JsxFileGenPlugin.indentation_space + "}, [schema, schemaCollections])\n\n"
                data_source_str = "dataSources={dataSources}"
            else:
                dependent_msg_name: str = dependent_msg_name_list[0]
                dependent_msg_name_snake_cased: str = convert_camel_case_to_specific_case(dependent_msg_name)
                output_str += JsxFileGenPlugin.indentation_space + "const dataSource = useMemo(() => {\n"
                output_str += JsxFileGenPlugin.indentation_space*2 + f"const dataSourceName = '{dependent_msg_name_snake_cased}';\n"
                output_str += JsxFileGenPlugin.indentation_space*2 + "const dataSourceSchema = getModelSchema(dataSourceName, schema);\n"
                output_str += JsxFileGenPlugin.indentation_space*2 + "return {\n"
                output_str += JsxFileGenPlugin.indentation_space*3 + "name: dataSourceName,\n"
                output_str += JsxFileGenPlugin.indentation_space*3 + f"actions: {dependent_msg_name}Actions,\n"
                output_str += JsxFileGenPlugin.indentation_space*3 + "schema: dataSourceName,\n"
                output_str += JsxFileGenPlugin.indentation_space*3 + "url: getServerUrl(dataSourceSchema),\n"
                output_str += JsxFileGenPlugin.indentation_space*3 + "fieldsMetadata: schemaCollections[dataSourceName],\n"
                output_str += JsxFileGenPlugin.indentation_space*3 + f"selector: Selectors.select{dependent_msg_name}\n"
                output_str += JsxFileGenPlugin.indentation_space*2 + "}\n"
                output_str += JsxFileGenPlugin.indentation_space + "}, [schema, schemaCollections])\n\n"
                data_source_str = "dataSource={dataSource}"
        else:
            data_source_str = "dataSource={null}"
        output_str += JsxFileGenPlugin.indentation_space + "return (\n"
        model_type_str = self.get_model_type_str_for_model_type(model_type)
        output_str += JsxFileGenPlugin.indentation_space*2 + f"<{model_type_str}\n"
        output_str += JsxFileGenPlugin.indentation_space*3 + "modelName={MODEL_NAME}\n"
        output_str += JsxFileGenPlugin.indentation_space*3 + "modelDataSource={modelDataSource}\n"
        output_str += JsxFileGenPlugin.indentation_space*3 + f"{data_source_str}\n"
        if model_type == JsxFileGenPlugin.non_root_type:
            root_msg = self.get_root_msg_for_non_root_type(message)
            root_message_name = root_msg.proto.name
            root_message_name_snake_cased = convert_camel_case_to_specific_case(root_message_name)
            output_str += JsxFileGenPlugin.indentation_space*3 + "modelRootName={'"+f"{root_message_name_snake_cased}"+"'}\n"
        # else not required: other types are roots
        output_str += JsxFileGenPlugin.indentation_space*2 + "/>\n"
        output_str += JsxFileGenPlugin.indentation_space + ");\n"
        output_str += "};\n\n"
        return output_str

    def handle_model_proptype(self, message: protogen.Message, message_name: str, model_type: str):
        output_str = "/**\n"
        output_str += f" * PropTypes for {message_name}.\n"
        output_str += f" */\n"
        output_str += f"{message_name}.propTypes = "+"{\n"
        output_str += JsxFileGenPlugin.indentation_space + "modelName: PropTypes.string,\n"
        output_str += JsxFileGenPlugin.indentation_space + "modelDataSource: PropTypes.shape({\n"
        output_str += JsxFileGenPlugin.indentation_space*2 + "name: PropTypes.string.isRequired,\n"
        output_str += JsxFileGenPlugin.indentation_space*2 + "selector: PropTypes.func.isRequired,\n"
        output_str += JsxFileGenPlugin.indentation_space*2 + "actions: PropTypes.object.isRequired,\n"
        output_str += JsxFileGenPlugin.indentation_space*2 + "schema: PropTypes.object.isRequired,\n"
        output_str += JsxFileGenPlugin.indentation_space*2 + "url: PropTypes.string,\n"
        output_str += JsxFileGenPlugin.indentation_space + "}),\n"
        if model_type == JsxFileGenPlugin.abbreviated_merge_type:
            output_str += JsxFileGenPlugin.indentation_space + "dataSources: PropTypes.arrayOf(\n"
            output_str += JsxFileGenPlugin.indentation_space*2 + "PropTypes.shape({\n"
            output_str += JsxFileGenPlugin.indentation_space*3 + "name: PropTypes.string.isRequired,\n"
            output_str += JsxFileGenPlugin.indentation_space*3 + "selector: PropTypes.object.isRequired,\n"
            output_str += JsxFileGenPlugin.indentation_space*3 + "actions: PropTypes.object.isRequired,\n"
            output_str += JsxFileGenPlugin.indentation_space*3 + "schema: PropTypes.object.isRequired,\n"
            output_str += JsxFileGenPlugin.indentation_space*3 + "url: PropTypes.string\n"
            output_str += JsxFileGenPlugin.indentation_space*2 + "})\n"
            output_str += JsxFileGenPlugin.indentation_space + ")\n"
        else:
            output_str += JsxFileGenPlugin.indentation_space + "dataSource: PropTypes.shape({\n"
            output_str += JsxFileGenPlugin.indentation_space*2 + "name: PropTypes.string.isRequired,\n"
            output_str += JsxFileGenPlugin.indentation_space*2 + "selector: PropTypes.func.isRequired,\n"
            output_str += JsxFileGenPlugin.indentation_space*2 + "actions: PropTypes.object.isRequired,\n"
            output_str += JsxFileGenPlugin.indentation_space*2 + "schema: PropTypes.object.isRequired,\n"
            output_str += JsxFileGenPlugin.indentation_space*2 + "url: PropTypes.string\n"
            output_str += JsxFileGenPlugin.indentation_space + "}),\n"
        output_str += "};\n\n"
        return output_str

    def handle_jsx_file_output(self, message: protogen.Message, model_type: str) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = self.handle_import_output(message, model_type)
        output_str += self.handle_model_doc_str(message_name, model_type)
        output_str += self.handle_model_declaration(message, model_type)
        output_str += self.handle_model_proptype(message, message_name, model_type)
        output_str += f"export default {message_name};\n"

        return output_str

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
            # Abbreviated Case
            if message in self.abbreviated_merge_layout_msg_list:
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
