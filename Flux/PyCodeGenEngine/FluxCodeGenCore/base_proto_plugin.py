#!/usr/bin/env python
import os
import re
from typing import List, Dict, ClassVar
import logging
from abc import ABC, abstractmethod
import protogen

# project imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.extended_protogen_plugin import ExtendedProtogenPlugin
from Flux.PyCodeGenEngine.FluxCodeGenCore.extended_protogen_options import ExtendedProtogenOptions

# Required for accessing custom options from schema
from Flux.PyCodeGenEngine.FluxCodeGenCore import insertion_imports


class BaseProtoPlugin(ABC):
    """
    Plugin base script to be inherited from plugin scripts (for example: db binding plugin)
    Uses template file to add content and insertion points in output and adds content provided
    by derived class at insertion points. Derived implementation needs to set data member lists
    `insertion_point_key_list` and `insertion_point_key_to_callable_list` which are used in
    method `__process` to set `insertion_points_to_content_dict` which is assigned to
    `insertion_points_to_content_dict` data member of ``ExtendedProtogenPlugin``.

    Attributes:
    -----------
    base_dir_path: str
        path of directory containing derived plugin implementation
    config_file_path: str
        path of yaml config file
    config_yaml:
        Dictionary converted from content inside yaml config file
    template_file_path: str
        path of template file to be used to generate output file
    output_file_name: str
        name of output file to be generated
    main_proto_msg_class_name: str
        name of proto main message class from proto schema, gets assigned at run-time
    insertion_point_key_to_callable_list: List[Callable]
        List of respective insertion point's handler methods to be assigned by derived class
    insertion_points_to_content_dict: Dict[str, str]
        Dictionary containing insertion point keys with respective contents as value. Gets
        assigned by `__process` method at run-time
    """
    msg_options_standard_prefix = "FluxMsg"
    fld_options_standard_prefix = "FluxFld"
    flux_fld_val_is_datetime: ClassVar[str] = "FluxFldValIsDateTime"
    flux_fld_alias: ClassVar[str] = "FluxFldAlias"
    flux_msg_json_root: ClassVar[str] = "FluxMsgJsonRoot"
    flux_msg_json_query: ClassVar[str] = "FluxMsgJsonQuery"
    flux_json_root_create_field: ClassVar[str] = "CreateDesc"
    flux_json_root_read_field: ClassVar[str] = "ReadDesc"
    flux_json_root_update_field: ClassVar[str] = "UpdateDesc"
    flux_json_root_patch_field: ClassVar[str] = "PatchDesc"
    flux_json_root_delete_field: ClassVar[str] = "DeleteDesc"
    flux_json_root_read_websocket_field: ClassVar[str] = "ReadWebSocketDesc"
    flux_json_root_update_websocket_field: ClassVar[str] = "UpdateWebSocketDesc"
    flux_json_root_set_reentrant_lock_field: ClassVar[str] = "SetReentrantLock"
    flux_json_root_set_reentrant_lock_to_top_field: ClassVar[str] = "SetReentrantLockToTop"
    flux_json_query_name_field: ClassVar[str] = "QueryName"
    flux_json_query_aggregate_var_name_field: ClassVar[str] = "AggregateVarName"
    flux_json_query_params_field: ClassVar[str] = "QueryParams"
    flux_json_query_params_data_type_field: ClassVar[str] = "QueryParamsDataType"
    flux_json_query_type_field: ClassVar[str] = "QueryType"
    flux_fld_is_required: ClassVar[str] = "FluxFldIsRequired"
    flux_fld_cmnt: ClassVar[str] = "FluxFldCmnt"
    flux_msg_cmnt: ClassVar[str] = "FluxMsgCmnt"
    flux_file_cmnt: ClassVar[str] = "FluxFileCmnt"
    flux_fld_index: ClassVar[str] = "FluxFldIndex"
    flux_fld_web_socket: ClassVar[str] = "FluxFldWebSocket"
    flux_fld_abbreviated: str = "FluxFldAbbreviated"
    flux_fld_auto_complete: str = "FluxFldAutoComplete"
    flux_fld_sequence_number: str = "FluxFldSequenceNumber"
    flux_fld_button: str = "FluxFldButton"
    flux_msg_title: str = "FluxMsgTitle"
    flux_fld_title: str = "FluxFldTitle"
    flux_fld_filter: str = "FluxFldFilter"
    flux_fld_val_max: str = "FluxFldValMax"
    flux_fld_val_min: str = "FluxFldValMin"
    flux_msg_nested_fld_val_filter_param: str = "FluxMsgNestedFldValFilterParam"
    flux_fld_date_time_format: str = "FluxFldDateTimeFormat"
    flux_fld_elaborated_title: str = "FluxFldElaborateTitle"
    flux_fld_name_color: str = "FluxFldNameColor"
    flux_msg_widget_ui_data: str = "FluxMsgWidgetUIData"
    flux_msg_aggregate_query_var_name: str = "FluxMsgAggregateQueryVarName"
    aggregation_type_update: str = "AggregateType_UpdateAggregate"
    aggregation_type_filter: str = "AggregateType_FilterAggregate"
    aggregation_type_both: str = "AggregateType_FilterNUpdate"
    aggregation_type_unspecified: str = "AggregateType_UNSPECIFIED"
    flux_msg_crud_shared_lock: str = "FluxMsgCRUDSharedLock"
    flux_file_crud_host: str = "FluxFileCRUDHost"
    flux_file_crud_port_offset: str = "FluxFileCRUDPortOffset"
    flux_fld_help: str = "FluxFldHelp"
    flux_fld_ui_update_only:  str = "FluxFldUIUpdateOnly"
    flux_fld_ui_placeholder:  str = "FluxFldUIPlaceholder"
    flux_fld_default_value_placeholder_string:  str = "FluxFldDefaultValuePlaceholderString"
    flux_fld_alert_bubble_color:  str = "FluxFldAlertBubbleColor"
    flux_fld_alert_bubble_source:  str = "FluxFldAlertBubbleSource"
    flux_fld_color:  str = "FluxFldColor"
    flux_fld_server_populate:  str = "FluxFldServerPopulate"
    flux_fld_switch:  str = "FluxFldSwitch"
    flux_fld_orm_no_update:  str = "FluxFldOrmNoUpdate"
    flux_fld_size_max:  str = "FluxFldSizeMax"
    flux_fld_sticky:  str = "FluxFldSticky"
    flux_fld_val_sort_weight:  str = "FluxFldValSortWeight"
    flux_fld_hide:  str = "FluxFldHide"
    flux_fld_progress_bar:  str = "FluxFldProgressBar"
    flux_fld_filter_enable:  str = "FluxFldFilterEnable"
    flux_msg_server_populate:  str = "FluxMsgServerPopulate"
    flux_msg_main_crud_operations_agg: str = "FluxMsgMainCRUDOperationsAgg"
    flux_fld_collection_link: str = "FluxFldCollectionLink"
    flux_fld_no_common_key: str = "FluxFldNoCommonKey"
    flux_fld_number_format: str = "FluxFldNumberFormat"
    flux_fld_display_type: str = "FluxFldDisplayType"
    flux_fld_display_zero: str = "FluxFldDisplayZero"
    flux_fld_text_align: str = "FluxFldTextAlign"
    flux_msg_ui_get_all_limit: str = "FluxMsgUIGetAllLimit"
    flux_fld_abbreviated_link: str = "FluxFldAbbreviatedLink"
    flux_msg_executor_options: str = "FluxMsgExecutorOptions"
    executor_option_is_websocket_model_field: str = "IsWebSocketModel"
    executor_option_enable_notify_all_field: str = "EnableNotifyAll"
    executor_option_is_top_lvl_model_field: str = "IsTopLvlModel"
    executor_option_executor_key_count_field: str = "ExecutorKeyCounts"
    executor_option_executor_key_sequence_field: str = "ExecutorKeySequence"
    executor_option_log_key_sequence_field: str = "LogKeySequence"
    default_id_field_name: ClassVar[str] = "id"
    default_id_type_var_name: str = "DefaultIdType"  # to be used in models as default type variable name
    proto_package_var_name: str = "ProtoPackageName"  # to be used in models as proto_package_name variable name
    proto_type_to_py_type_dict: ClassVar[Dict[str, str]] = {
        "int32": "int",
        "int64": "int",
        "string": "str",
        "bool": "bool",
        "float": "float",
        "double": "float"
    }
    proto_type_to_json_type_dict: Dict[str, str] = {
        "int32": "number",
        "int64": "number",
        "string": "string",
        "bool": "boolean",
        "enum": "enum",
        "message": "object",
        "float": "number",
        "double": "number"
    }

    def __init__(self, base_dir_path: str):
        self.base_dir_path: str = base_dir_path

        self.output_file_name_to_template_file_path_dict: Dict[str, str] = {}
        # Below data member will override on the run time
        self.insertion_points_to_content_dict: Dict[str, str] | Dict[str, Dict[str, str]] = {}

    @abstractmethod
    def output_file_generate_handler(self, file: protogen.File):
        raise NotImplementedError("Derived implementation must return dict of "
                                  "output file name-respective content key-value pair or "
                                  "output file name-dict of insertion points-respective content key-value pair ")

    def is_bool_option_enabled(self, msg_or_fld_option: protogen.Message | protogen.Field, option_name: str) -> bool:
        if self.is_option_enabled(msg_or_fld_option, option_name) and \
                "true" == self.get_non_repeated_valued_custom_option_value(msg_or_fld_option,
                                                                           option_name):
            return True
        else:
            return False

    @staticmethod
    def get_non_repeated_valued_custom_option_value(proto_entity: protogen.Message | protogen.Field | protogen.File,
                                                    option_name: str):
        options_list = [option for option in str(proto_entity.proto.options).split("\n") if ":" in option]
        for option in options_list:
            if re.search(r'\b' + option_name + r'\b', option):
                option_content = ":".join(str(option).split(":")[1:])
                if option_content.isspace():
                    return option_content
                return option_content.strip()
            # else not required: Avoiding if option_name not in option_obj

    @staticmethod
    def is_option_enabled(msg_or_fld_or_file: protogen.Message | protogen.Field | protogen.File,
                          option_name: str):
        """
        Check and return True if provided message | field | file proto object contains provided option
        enabled, return False otherwise
        """
        proto_option_str: str = str(msg_or_fld_or_file.proto.options)
        if re.search(r'\b' + option_name + r'\b', proto_option_str):
            return True
        return False

    @staticmethod
    def __get_complex_option_value_as_list_of_tuple(option_string: str, option_name: str):
        option_value_list_of_tuples = []
        for option_str_line in str(option_string).split("\n"):
            temp_list = []
            if option_name in str(option_str_line):
                option_str_line_index = option_string.index(option_str_line)
                sliced_message_option_str = option_string[option_str_line_index:]
                option_string = option_string[option_str_line_index + 1:]
                for sliced_option_str_line in sliced_message_option_str.split("\n"):
                    if ":" in sliced_option_str_line:
                        if '"' in sliced_option_str_line.split(":")[1]:
                            # For string value: removing extra quotation marks
                            temp_list.append(str(sliced_option_str_line.split(":")[1][2:-1]))
                        else:
                            if ' true' == sliced_option_str_line.split(":")[1] or ' false' == \
                                    sliced_option_str_line.split(":")[1]:
                                temp_list.append(True if sliced_option_str_line.split(":")[1] == ' true' else False)
                            else:
                                # For int value
                                temp_list.append(int(sliced_option_str_line.split(":")[1]))
                    elif "}" in sliced_option_str_line:
                        option_value_list_of_tuples.append(tuple(temp_list))
                        break
            # else not required: option_name not in option_string line, then ignore
        return option_value_list_of_tuples

    @staticmethod
    def get_complex_msg_option_values_as_list_of_tuple(message: protogen.Message, option_name: str) -> List[Dict]:
        message_options_temp_str = str(message.proto.options)
        option_value_list_of_tuples = \
            BaseProtoPlugin._get_complex_option_value_as_list_of_dict(message_options_temp_str, option_name)
        return option_value_list_of_tuples

    @staticmethod
    def get_field_default_value(field: protogen.Field):
        """
        Returns python syntax-ed default value of field (used by python code generators)
        Returns None if no default value is found in field proto object
        """
        output_str = None
        if default_val := field.proto.default_value:
            match field.kind.name.lower():
                case "string":
                    output_str = f"'{default_val}'"
                case "int32" | "int64" | "float":
                    output_str = default_val
                case "bool":
                    output_str = True if default_val == "true" else False
                case "enum":
                    enum_name = field.enum.proto.name
                    output_str = f"{enum_name}.{default_val}"
                case other:
                    err_str = f"Unsupported field type for default value, field {field.proto.name} of " \
                              f"message {field.parent.proto.name} has type {other}"
                    logging.exception(err_str)
                    raise Exception(err_str)
        return output_str

    @staticmethod
    def _get_complex_option_value_as_list_of_dict(option_string: str, option_name: str) -> List[Dict]:
        option_value_list_of_dict: List[Dict] = []
        for option_str_line in str(option_string).split("\n"):
            temp_dict: Dict[List[str, ...] | str] = {}
            if option_name in str(option_str_line):
                option_str_line_index = option_string.index(option_str_line)
                sliced_message_option_str = option_string[option_str_line_index:]
                option_string = option_string[option_str_line_index + 1:]
                for sliced_option_str_line in sliced_message_option_str.split("\n"):
                    if ":" in sliced_option_str_line:
                        field_name = sliced_option_str_line.split(":")[0][2:]
                        field_val = sliced_option_str_line.split(":")[1]
                        if '"' in field_val:
                            # For string value: removing extra quotation marks
                            processed_field_val = str(field_val[2:-1])
                        else:
                            # For bool value
                            if ' true' == field_val or ' false' == field_val:
                                processed_field_val = True if field_val == ' true' else False
                            else:
                                if sliced_option_str_line.split(":")[1].isdigit():
                                    processed_field_val = int(field_val)
                                else:
                                    processed_field_val = field_val
                        if field_name in temp_dict:
                            if isinstance(temp_dict[field_name], list):
                                temp_dict[field_name].append(processed_field_val)
                            else:
                                temp_dict[field_name] = [temp_dict[field_name], processed_field_val]
                        else:
                            temp_dict[field_name] = processed_field_val
                    elif "}" in sliced_option_str_line:
                        option_value_list_of_dict.append(temp_dict)
                        break
            # else not required: option_name not in option_string line, then ignore
        return option_value_list_of_dict

    @staticmethod
    def get_complex_option_set_values(proto_entity: protogen.Message | protogen.Field | protogen.File,
                                      option_name: str,
                                      is_option_repeated: bool | None = None) -> List[Dict] | Dict:
        """
        Returns list of dictionaries containing each complex option's value tree on each index.
        If Option is repeated type returns list of option value tree dicts else returns only one for non-repeated.
        """
        proto_entity_options_str = str(proto_entity.proto.options)
        option_value_list_of_dict = \
            BaseProtoPlugin._get_complex_option_value_as_list_of_dict(proto_entity_options_str, option_name)
        if is_option_repeated is not None and is_option_repeated:
            return option_value_list_of_dict
        else:
            if len(option_value_list_of_dict) < 2:
                if len(option_value_list_of_dict) == 1:
                    return option_value_list_of_dict[0]
                else:
                    return {}
            else:
                err_str = "Interface get_complex_option_values_as_list_of_dict has param is_option_repeated set " \
                          f"as either None or False but received repeated option values for option name {option_name}" \
                          f" in proto_entity {proto_entity.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)

    @staticmethod
    def get_flux_msg_cmt_option_value(message: protogen.Message) -> str:
        flux_msg_cmt_option_value = \
            BaseProtoPlugin.get_non_repeated_valued_custom_option_value(message,
                                                                        BaseProtoPlugin.flux_msg_cmnt)
        return flux_msg_cmt_option_value[2:-1] \
            if flux_msg_cmt_option_value is not None else ""

    @staticmethod
    def get_flux_fld_cmt_option_value(field: protogen.Field) -> str:
        flux_fld_cmt_option_value = \
            BaseProtoPlugin.get_non_repeated_valued_custom_option_value(field, BaseProtoPlugin.flux_fld_cmnt)
        return flux_fld_cmt_option_value[2:-1] \
            if flux_fld_cmt_option_value is not None else ""

    @staticmethod
    def get_flux_file_cmt_option_value(file: protogen.File) -> str:
        flux_file_cmt_option_value = \
            BaseProtoPlugin.get_non_repeated_valued_custom_option_value(file, BaseProtoPlugin.flux_file_cmnt)
        return flux_file_cmt_option_value[2:-1] \
            if flux_file_cmt_option_value is not None else ""

    @staticmethod
    def import_path_from_os_path(os_path_env_var_name: str, import_file_name: str):
        # remove projects home prefix from all import paths
        if (project_root_dir := os.getenv("PROJECT_ROOT")) is not None:
            if (pydantic_path := os.getenv(os_path_env_var_name)) is not None:
                if pydantic_path is not None and pydantic_path.startswith("/"):
                    pydantic_path = pydantic_path.removeprefix(project_root_dir)
                else:
                    raise Exception(f"invalid absolute path: {pydantic_path}")
                if pydantic_path.startswith("/"):
                    pydantic_path = pydantic_path[1:]
                return f'{".".join(pydantic_path.split(os.sep))}.{import_file_name}'
            else:
                err_str = f"Env var '{os_path_env_var_name}' received as None"
                logging.exception(err_str)
                raise Exception(err_str)
        else:
            err_str = "Env var 'PROJECT_ROOT' received as None"
            logging.exception(err_str)
            raise Exception(err_str)

    def _process(self, plugin: ExtendedProtogenPlugin) -> None:
        """
        Underlying method, handles the task of creating dictionary of insertion point keys and there
        insertion content as value. This Dictionary is then assigned to `insertion_points_to_content_dict`
        data member of ``ExtendedProtogenPlugin``
        """
        # @@@ May contain bug for explicit multi input files, so protoc command should
        # be used for single input file explicitly
        for file in plugin.files_to_generate:
            output_file_name_to_insertion_points_n_content_dict: Dict[str, Dict[str, str]] = {}
            received_output_file_name_to_content = self.output_file_generate_handler(file)

            for output_file_name, output_file_content in received_output_file_name_to_content.items():
                if isinstance(output_file_content, dict):
                    file_content_path = self.output_file_name_to_template_file_path_dict.get(output_file_name)
                    if file_content_path is not None:
                        if os.path.exists(file_content_path):
                            with open(file_content_path, "r") as fl:
                                file_content = fl.read()
                        else:
                            err_str = f"file: {file_content_path} does not exist"
                            logging.exception(err_str)
                            raise Exception(err_str)
                        generator = plugin.new_generated_file(output_file_name, file.py_import_path)
                        generator.P(file_content)
                    else:
                        err_str = "output_file_name_to_template_file_path_dict could not find any key matching " \
                                  f"output_file_name: {output_file_name}"
                        logging.exception(err_str)
                        raise Exception(err_str)
                    
                    output_file_name_to_insertion_points_n_content_dict[output_file_name] = {}
                    for insert_point, replacing_content in output_file_content.items():
                        output_file_name_to_insertion_points_n_content_dict[output_file_name][insert_point] = \
                            replacing_content
                elif isinstance(output_file_content, str):
                    generator = plugin.new_generated_file(output_file_name, file.py_import_path)
                    file_content = f"# @@protoc_insertion_point({output_file_name})"
                    generator.P(file_content)
                    output_file_name_to_insertion_points_n_content_dict[output_file_name] = {}
                    output_file_name_to_insertion_points_n_content_dict[output_file_name][output_file_name] = \
                        output_file_content
                else:
                    err_str = f"unsupported type: {type(output_file_content)} of output_file_content " \
                              f"for output_file_name {output_file_name}"
                    logging.exception(err_str)
                    raise Exception(err_str)

            plugin.insertion_points_to_content_dict = output_file_name_to_insertion_points_n_content_dict

    def process(self):
        extended_protogen_options = ExtendedProtogenOptions()
        extended_protogen_options.run(self._process)


def main(plugin_class):
    if (project_dir_path := os.getenv("PROJECT_DIR")) is not None:
        pydantic_class_gen_plugin = plugin_class(project_dir_path)
        pydantic_class_gen_plugin.process()
    else:
        err_str = "Env var 'PROJECT_DIR' received as None"
        logging.exception(err_str)
        raise Exception(err_str)
