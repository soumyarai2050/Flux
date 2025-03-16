#!/usr/bin/env python
import logging
import os
import re
from typing import List, Callable, Dict, Final
import time
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main
from FluxPythonUtils.scripts.general_utility_functions import capitalized_to_camel_case, \
    convert_to_camel_case, convert_to_capitalized_camel_case, YAMLConfigurationManager
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case

if (project_dir := os.getenv("PROJECT_DIR")) is not None and len(project_dir):
    project_dir_path = PurePath(project_dir)
else:
    err_str = f"Couldn't find 'PROJECT_DIR' env var, value is {project_dir}"
    logging.exception(err_str)
    raise Exception(err_str)
config_yaml_path = project_dir_path / "data" / "config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))


class JsSliceFileGenPlugin(BaseJSLayoutPlugin):
    indentation_space: Final[str] = "    "

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_slice_content(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_camel_cased = capitalized_to_camel_case(message_name)
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = "import createGenericSlice from '../utils/genericSlice';\n"
        output_str += "import { MODEL_TYPES } from '../constants.js';\n"
        if message_name == "UILayout":
            output_str += "import { defaultLayouts } from '../projectSpecificUtils.js';\n\n"
            output_str += "const injectedReducers = {\n"
            output_str += JsSliceFileGenPlugin.indentation_space + "setStoredObjByName(state, action) {\n"
            output_str += JsSliceFileGenPlugin.indentation_space*2 + f"const storedObjKey = 'stored{message_name}Obj';\n"
            output_str += JsSliceFileGenPlugin.indentation_space*2 + "const { name, data, type } = action.payload;\n"
            output_str += JsSliceFileGenPlugin.indentation_space*2 + "if (type === 'data') {\n"
            output_str += (JsSliceFileGenPlugin.indentation_space*3 + "const layoutDataElement = state[storedObjKey]."
                           "widget_ui_data_elements.find((o) => o.i === name);\n")
            output_str += JsSliceFileGenPlugin.indentation_space*3 + "if (!data.bind_id_val) {\n"
            output_str += JsSliceFileGenPlugin.indentation_space*4 + "layoutDataElement.widget_ui_data.splice(0, 1, data);\n"
            output_str += JsSliceFileGenPlugin.indentation_space*3 + "} else {\n"
            output_str += (JsSliceFileGenPlugin.indentation_space*4 + "const idx = layoutDataElement.widget_ui_data.indexOf((o) => "
                           "o.bind_id_val === data.bind_id_val);\n")
            output_str += JsSliceFileGenPlugin.indentation_space*4 + "if (idx !== -1) {\n"
            output_str += JsSliceFileGenPlugin.indentation_space*5 + "layoutDataElement.widget_ui_data.splice(idx, 1, data);\n"
            output_str += JsSliceFileGenPlugin.indentation_space*4 + "} else {\n"
            output_str += JsSliceFileGenPlugin.indentation_space*5 + "layoutDataElement.widget_ui_data.push(data);\n"
            output_str += JsSliceFileGenPlugin.indentation_space*4 + "}\n"
            output_str += JsSliceFileGenPlugin.indentation_space*3 + "}\n"
            output_str += JsSliceFileGenPlugin.indentation_space*2 + "} else if (type === 'option') {\n"
            output_str += JsSliceFileGenPlugin.indentation_space*3 + "const layoutDataElements = state[storedObjKey].widget_ui_data_elements;\n"
            output_str += JsSliceFileGenPlugin.indentation_space*3 + "const idx = layoutDataElements.findIndex((o) => o.i === name);\n"
            output_str += JsSliceFileGenPlugin.indentation_space*3 + "if (idx !== -1) {\n"
            output_str += JsSliceFileGenPlugin.indentation_space*4 + "layoutDataElements.splice(idx, 1, data);\n"
            output_str += JsSliceFileGenPlugin.indentation_space*3 + "} else {\n"
            output_str += JsSliceFileGenPlugin.indentation_space*4 + "layoutDataElements.push(data);\n"
            output_str += JsSliceFileGenPlugin.indentation_space*3 + "}\n"
            output_str += JsSliceFileGenPlugin.indentation_space*2 + "}\n"
            output_str += JsSliceFileGenPlugin.indentation_space + "},\n"
            output_str += "};\n"
        output_str += "\n"
        output_str += "const { reducer, actions } = createGenericSlice({\n"
        output_str += JsSliceFileGenPlugin.indentation_space + f"modelName: '{message_name_snake_cased}',\n"
        if message in self.repeated_msg_list:
            output_str += JsSliceFileGenPlugin.indentation_space + f"modelType: MODEL_TYPES.REPEATED_ROOT,\n"
        elif message in self.abbreviated_merge_layout_msg_list:
            output_str += JsSliceFileGenPlugin.indentation_space + f"modelType: MODEL_TYPES.ABBREVIATION_MERGE,\n"
        else:
            output_str += JsSliceFileGenPlugin.indentation_space + f"modelType: MODEL_TYPES.ROOT,\n"

        # adding attribute telling some abbreviated msg is dependent on this message
        for abb_msg in self.abbreviated_merge_layout_msg_list:
            dependent_msg_list = self.msg_name_to_dependent_msg_name_list_dict.get(abb_msg.proto.name)
            if message_name in dependent_msg_list and message not in self.abbreviated_merge_layout_msg_list:
                # if some abbreviated message is dependent on this message and this message
                # itself is not abbreviated type
                output_str += JsSliceFileGenPlugin.indentation_space + f"isAbbreviationSource: true,\n"

        if message_name == "UILayout":
            output_str += JsSliceFileGenPlugin.indentation_space + "extraState: {\n"
            output_str += JsSliceFileGenPlugin.indentation_space*2 + f"stored{message_name}Obj: "+"{ profile_id: 'default', widget_ui_data_elements: defaultLayouts },\n"
            output_str += JsSliceFileGenPlugin.indentation_space*2 + f"isLoading: true,\n"
            output_str += JsSliceFileGenPlugin.indentation_space + "},\n"
            output_str += JsSliceFileGenPlugin.indentation_space + "injectedReducers\n"
        elif message in self.alert_type_message_list:
            output_str += JsSliceFileGenPlugin.indentation_space + f"isAlertModel: true\n"
        output_str += "});\n\n"
        output_str += "export default reducer;\n"
        output_str += "export { actions };\n"
        return output_str

    def output_file_generate_handler(self, file: protogen.File | List[protogen.File]):
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)

        output_dict = {}

        # sorting created message lists
        self.root_msg_list.sort(key=lambda message_: message_.proto.name)

        for message in self.root_msg_list:
            message_name_camel_cased = capitalized_to_camel_case(message.proto.name)
            output_dict_key = f"{message_name_camel_cased}Slice.js"
            output_str = self.handle_slice_content(message)

            output_dict[output_dict_key] = output_str

        return output_dict


if __name__ == "__main__":
    main(JsSliceFileGenPlugin)
