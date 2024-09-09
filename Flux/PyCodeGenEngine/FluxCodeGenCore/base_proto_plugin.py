#!/usr/bin/env python
import os
import re
from typing import List, Dict, ClassVar, Any, Set, Tuple, Callable
import logging
from abc import ABC, abstractmethod
from pathlib import PurePath
import copy

# 3rd party imports
import numpy as np
import protogen

# project imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.extended_protogen_plugin import ExtendedProtogenPlugin
from Flux.PyCodeGenEngine.FluxCodeGenCore.extended_protogen_options import ExtendedProtogenOptions
from FluxPythonUtils.scripts.utility_functions import parse_to_int, parse_to_float, convert_camel_case_to_specific_case

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
    output_file_name_to_template_file_path_dict: Dict[str, str]
        will be populated by derived implementation based on output generation
        depending on insert points based template
    """
    flux_option_file_name = "flux_options.proto"
    msg_options_standard_prefix = "FluxMsg"
    fld_options_standard_prefix = "FluxFld"
    flux_fld_val_is_datetime: ClassVar[str] = "FluxFldValIsDateTime"
    flux_file_import_dependency_model: ClassVar[str] = "FluxFileImportDependencyModel"
    flux_fld_alias: ClassVar[str] = "FluxFldAlias"
    flux_msg_json_root: ClassVar[str] = "FluxMsgJsonRoot"
    flux_msg_json_root_time_series: ClassVar[str] = "FluxMsgJsonRootTimeSeries"
    flux_msg_json_query: ClassVar[str] = "FluxMsgJsonQuery"
    flux_json_root_create_field: ClassVar[str] = "CreateOp"
    flux_json_root_create_all_field: ClassVar[str] = "CreateAllOp"
    flux_json_root_read_field: ClassVar[str] = "ReadOp"
    flux_json_root_update_field: ClassVar[str] = "UpdateOp"
    flux_json_root_update_all_field: ClassVar[str] = "UpdateAllOp"
    flux_json_root_patch_field: ClassVar[str] = "PatchOp"
    flux_json_root_patch_all_field: ClassVar[str] = "PatchAllOp"
    flux_json_root_delete_field: ClassVar[str] = "DeleteOp"
    flux_json_root_delete_all_field: ClassVar[str] = "DeleteAllOp"
    flux_json_root_read_by_id_websocket_field: ClassVar[str] = "ReadByIDWebSocketOp"
    flux_json_root_set_reentrant_lock_field: ClassVar[str] = "SetReentrantLock"
    flux_json_query_name_field: ClassVar[str] = "QueryName"
    flux_json_query_aggregate_var_name_field: ClassVar[str] = "AggregateVarName"
    flux_json_query_params_field: ClassVar[str] = "QueryParams"
    flux_json_query_params_data_type_field: ClassVar[str] = "QueryParamsDataType"
    flux_json_query_type_field: ClassVar[str] = "QueryType"
    flux_json_query_route_type_field: ClassVar[str] = "QueryRouteType"
    flux_json_query_route_get_type_field_val: ClassVar[str] = "GET"
    flux_json_query_route_patch_type_field_val: ClassVar[str] = "PATCH"
    flux_json_query_route_post_type_field_val: ClassVar[str] = "POST"
    flux_json_query_require_js_slice_changes_field: ClassVar[str] = "RequireJsSliceChanges"
    flux_json_root_ts_mongo_version_field: ClassVar[str] = "MongoVersion"
    flux_json_root_ts_granularity_field: ClassVar[str] = "Granularity"
    flux_json_root_pass_stored_obj_to_update_pre_post_callback: ClassVar[str] = "PassStoredObjToUpdatePrePostCallback"
    flux_json_root_pass_stored_obj_to_update_all_pre_post_callback: ClassVar[str] = "PassStoredObjToUpdateAllPrePostCallback"
    flux_fld_val_time_field: ClassVar[str] = "FluxFldValTimeField"
    flux_fld_val_meta_field: ClassVar[str] = "FluxFldValMetaField"
    flux_json_root_ts_expire_after_sec_field: ClassVar[str] = "ExpireAfterSeconds"
    flux_json_root_ts_sec_field_name_field: ClassVar[str] = "SecondaryField"
    flux_fld_is_required: ClassVar[str] = "FluxFldIsRequired"
    flux_fld_cmnt: ClassVar[str] = "FluxFldCmnt"
    flux_msg_cmnt: ClassVar[str] = "FluxMsgCmnt"
    flux_file_cmnt: ClassVar[str] = "FluxFileCmnt"
    flux_fld_index: ClassVar[str] = "FluxFldIndex"
    flux_fld_web_socket: ClassVar[str] = "FluxFldWebSocket"
    flux_fld_abbreviated: ClassVar[str] = "FluxFldAbbreviated"
    flux_fld_auto_complete: ClassVar[str] = "FluxFldAutoComplete"
    flux_fld_sequence_number: ClassVar[str] = "FluxFldSequenceNumber"
    flux_fld_button: ClassVar[str] = "FluxFldButton"
    flux_msg_title: ClassVar[str] = "FluxMsgTitle"
    flux_fld_title: ClassVar[str] = "FluxFldTitle"
    flux_fld_filter: ClassVar[str] = "FluxFldFilter"
    flux_fld_val_max: ClassVar[str] = "FluxFldValMax"
    flux_fld_val_min: ClassVar[str] = "FluxFldValMin"
    flux_msg_nested_fld_val_filter_param: ClassVar[str] = "FluxMsgNestedFldValFilterParam"
    flux_fld_date_time_format: ClassVar[str] = "FluxFldDateTimeFormat"
    flux_fld_elaborated_title: ClassVar[str] = "FluxFldElaborateTitle"
    flux_fld_name_color: ClassVar[str] = "FluxFldNameColor"
    flux_msg_widget_ui_data_element: ClassVar[str] = "FluxMsgWidgetUIDataElement"
    flux_msg_widget_ui_option: ClassVar[str] = "FluxMsgWidgetUIOption"
    widget_ui_option_depending_proto_file_name_field: ClassVar[str] = "depending_proto_file_name"
    widget_ui_option_depending_proto_model_name_field: ClassVar[str] = "depending_proto_model_name"
    widget_ui_option_depends_on_other_model_for_id_field: ClassVar[str] = "depends_on_other_model_for_id"
    widget_ui_option_depends_on_model_name_for_port_field: ClassVar[str] = "depends_on_model_name_for_port"
    widget_ui_option_override_default_crud_field: ClassVar[str] = "override_default_crud"
    widget_ui_option_override_default_crud_ui_crud_type_field: ClassVar[str] = "ui_crud_type"
    widget_ui_option_override_default_crud_query_name_field: ClassVar[str] = "query_name"
    widget_ui_option_override_default_crud_query_src_model_name_field: ClassVar[str] = "query_src_model_name"
    widget_ui_option_override_default_crud_ui_query_params_field: ClassVar[str] = "ui_query_params"
    widget_ui_option_override_default_crud_ui_query_params_field_fld: ClassVar[str] = "query_param_field"
    widget_ui_option_override_default_crud_ui_query_params_src_field: ClassVar[str] = "query_param_field_src"
    widget_ui_option_depends_on_other_model_for_dynamic_url_field: ClassVar[str] = \
        "depends_on_other_model_for_dynamic_url"
    flux_msg_widget_ui_data_element_widget_ui_data_field: ClassVar[str] = "widget_ui_data"
    flux_msg_aggregate_query_var_name: ClassVar[str] = "FluxMsgAggregateQueryVarName"
    aggregation_type_update: ClassVar[str] = "AggregateType_UpdateAggregate"
    aggregation_type_filter: ClassVar[str] = "AggregateType_FilterAggregate"
    aggregation_type_both: ClassVar[str] = "AggregateType_FilterNUpdate"
    aggregation_type_unspecified: ClassVar[str] = "AggregateType_UNSPECIFIED"
    flux_msg_crud_shared_lock: ClassVar[str] = "FluxMsgCRUDSharedLock"
    flux_file_crud_host: ClassVar[str] = "FluxFileCRUDHost"
    flux_file_crud_port_offset: ClassVar[str] = "FluxFileCRUDPortOffset"
    flux_fld_help: ClassVar[str] = "FluxFldHelp"
    flux_fld_ui_update_only: ClassVar[str] = "FluxFldUIUpdateOnly"
    flux_fld_ui_placeholder: ClassVar[str] = "FluxFldUIPlaceholder"
    flux_fld_default_value_placeholder_string: ClassVar[str] = "FluxFldDefaultValuePlaceholderString"
    flux_fld_alert_bubble_color: ClassVar[str] = "FluxFldAlertBubbleColor"
    flux_fld_alert_bubble_source: ClassVar[str] = "FluxFldAlertBubbleSource"
    flux_fld_color: ClassVar[str] = "FluxFldColor"
    flux_fld_server_populate: ClassVar[str] = "FluxFldServerPopulate"
    flux_fld_switch: ClassVar[str] = "FluxFldSwitch"
    flux_fld_orm_no_update: ClassVar[str] = "FluxFldOrmNoUpdate"
    flux_fld_size_max: ClassVar[str] = "FluxFldSizeMax"
    flux_fld_sticky: ClassVar[str] = "FluxFldSticky"
    flux_fld_val_sort_weight: ClassVar[str] = "FluxFldValSortWeight"
    flux_fld_hide: ClassVar[str] = "FluxFldHide"
    flux_fld_progress_bar: ClassVar[str] = "FluxFldProgressBar"
    flux_fld_filter_enable: ClassVar[str] = "FluxFldFilterEnable"
    flux_msg_server_populate: ClassVar[str] = "FluxMsgServerPopulate"
    flux_msg_main_crud_operations_agg: ClassVar[str] = "FluxMsgMainCRUDOperationsAgg"
    flux_fld_collection_link: ClassVar[str] = "FluxFldCollectionLink"
    flux_fld_no_common_key: ClassVar[str] = "FluxFldNoCommonKey"
    flux_fld_number_format: ClassVar[str] = "FluxFldNumberFormat"
    flux_fld_display_type: ClassVar[str] = "FluxFldDisplayType"
    flux_fld_display_zero: ClassVar[str] = "FluxFldDisplayZero"
    flux_fld_text_align: ClassVar[str] = "FluxFldTextAlign"
    flux_fld_column_size: ClassVar[str] = "FluxFldColumnSize"
    flux_fld_column_direction: ClassVar[str] = "FluxFldColumnDirection"
    flux_fld_micro_separator: ClassVar[str] = "FluxFldMicroSeparator"
    flux_msg_ui_get_all_limit: ClassVar[str] = "FluxMsgUIGetAllLimit"
    flux_fld_abbreviated_link: ClassVar[str] = "FluxFldAbbreviatedLink"
    flux_fld_mapping_underlying_meta_field: ClassVar[str] = "FluxFldMappingUnderlyingMetaField"
    flux_fld_mapping_src: ClassVar[str] = "FluxFldMappingSrc"
    flux_fld_mapping_projection_query_field: ClassVar[str] = "FluxFldMappingProjectionQueryField"
    flux_msg_executor_options: ClassVar[str] = "FluxMsgExecutorOptions"
    flux_fld_projections: ClassVar[str] = "FluxFldProjections"
    flux_fld_server_running_status: ClassVar[str] = "FluxFldServerRunningStatus"
    flux_fld_server_ready_status: ClassVar[str] = "FluxFldServerReadyStatus"
    flux_fld_diff_threshold: ClassVar[str] = "FluxFldDiffThreshold"
    executor_option_is_websocket_model_field: ClassVar[str] = "IsWebSocketModel"
    executor_option_enable_notify_all_field: ClassVar[str] = "EnableNotifyAll"
    executor_option_is_top_lvl_model_field: ClassVar[str] = "IsTopLvlModel"
    executor_option_executor_key_count_field: ClassVar[str] = "ExecutorKeyCounts"
    executor_option_executor_key_sequence_field: ClassVar[str] = "ExecutorKeySequence"
    executor_option_log_key_sequence_field: ClassVar[str] = "LogKeySequence"
    executor_option_is_repeated_field: ClassVar[str] = "IsRepeated"
    executor_option_cache_as_dict_with_key_field: ClassVar[str] = "CacheAsDictWithKeyField"
    flux_msg_small_sized_collection: ClassVar[str] = "FluxMsgSmallSizedCollection"
    flux_fld_PK: ClassVar[str] = "FluxFldPk"
    flux_enum_cmnt: ClassVar[str] = "FluxEnumCmnt"
    default_id_field_name: ClassVar[str] = "id"
    default_id_type_var_name: ClassVar[str] = "DefaultIdType"  # to be used in models as default type variable name
    proto_package_var_name: ClassVar[str] = "ProtoPackageName"  # to be used in models as proto_package_name variable name
    pendulum_datetime_type: ClassVar[str] = "pendulum.DateTime"
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
        # output_file_name_to_template_file_path_dict will be populated by derived implementation based
        # on output generation depending on insert points based template
        self.output_file_name_to_template_file_path_dict: Dict[str, str] = {}
        self.insertion_points_to_content_dict: Dict[str, str] | Dict[str, Dict[str, str]] = {}

    @abstractmethod
    def output_file_generate_handler(self, file: protogen.File | List[protogen.File]):
        """
            Abstract method which is responsible for generating outputs from derived plugin class.
            Must return dict having:
            1. output_file_name to output_content key-value pair - for non-insertion point based template output
            2. output_file_name to output_content_dict key-value pair, where output_content_dict must have
            insertion_point to replacing_content key-value pair - for non-insertion point based template output
        """
        raise NotImplementedError("Derived implementation must return dict of "
                                  "output file name-respective content key-value pair or "
                                  "output file name-dict of insertion points-respective content key-value pair ")

    def is_bool_option_enabled(self, msg_or_fld_option: protogen.Message | protogen.Field, option_name: str) -> bool:
        if (self.is_option_enabled(msg_or_fld_option, option_name) and
                self.get_simple_option_value_from_proto(msg_or_fld_option,
                                                        option_name)):
            return True
        else:
            return False

    @staticmethod
    def parse_string_to_original_types(value: str) -> str | int | bool | float:
        """
        :Returns: int or float: if value string contains only numerics,
                  bool: if value contains string parsed bool,
                  cleaned string with quotation marks: if value is dirty string,
                  same value: if both cases are not matched
        """
        value = value.removeprefix('"').removesuffix('"')   # cleaning data

        # bool check
        if value in ["True", "False", "true", "false"]:
            return True if value in ["True", "true"] else False
        # int check
        elif value.lstrip("-").isdigit():
            return int(value)
        # float check
        elif re.match(r'^-?\d+(?:\.\d+)$', value) is not None:
            return float(value)
        # else str
        else:
            if value.isspace():
                return ' '*len(value)
            return str(value.strip())

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
    def _type_cast_option_str_val_to_type(val_str: str, proto_type: str):
        if proto_type.lower() == "string":
            val_str = val_str.strip()
            value = val_str.removeprefix('"').removesuffix('"')   # cleaning data
            # explicitly checking if any str type bools are found - converting to bool if found
            if value.lower() == "true":
                return True
            elif value.lower() == "false":
                return False
            return value
        elif proto_type.lower() == "int32" or proto_type.lower() == "int32":
            return parse_to_int(val_str)
        elif proto_type.lower() == "bool":
            return True if ('true' in val_str) else False
        elif proto_type.lower() == "float":
            return parse_to_float(val_str)
        else:
            return val_str.strip()

    @staticmethod
    def get_simple_option_value_from_proto(
            proto_entity: protogen.Message | protogen.Field | protogen.File | protogen.Enum,
            option_name: str, is_repeated: bool | None = None) -> (List | str | int | bool | float | None):
        """
        Returns List if option is_repeated else value, returns None if option is not set
        """
        if (isinstance(proto_entity, protogen.Message) or isinstance(proto_entity, protogen.Field) or
                isinstance(proto_entity, protogen.Enum)):
            option_type = BaseProtoPlugin.get_simple_option_type(proto_entity.parent_file, option_name)
        elif isinstance(proto_entity, protogen.File):
            option_type = BaseProtoPlugin.get_simple_option_type(proto_entity, option_name)
        else:
            err_str = f"Unexpected: proto_entity type: {type(proto_entity)}, name: {proto_entity.proto.name}"
            logging.exception(err_str)
            raise Exception(err_str)

        options_str_list = [option_str
                            for option_str in str(proto_entity.proto.options).split("\n") if ":" in option_str]
        option_val_list: List = []
        for option_str in options_str_list:
            if re.search(r'\b' + option_name + r'\b', option_str):
                option_content = ":".join(str(option_str).split(":")[1:])
                if option_content.isspace():
                    option_val_list.append(option_content)
                option_val_list.append(BaseProtoPlugin._type_cast_option_str_val_to_type(option_content.strip(),
                                                                                         option_type))
        if is_repeated:
            return option_val_list
        else:
            if len(option_val_list) > 1:
                err_str = ("is_repeated param was supplied as False but option is of repeated type, "
                           f"option_name: {option_name}, proto_entity_name: {proto_entity.proto.name}")
                logging.exception(err_str)
                raise Exception(err_str)
            else:
                if option_val_list:
                    return option_val_list[0]
                else:
                    return None

    @staticmethod
    def _get_complex_option_value_from_proto(
            option_string: str, option_name: str | None = None,
            proto_entity: protogen.Message | protogen.Field | protogen.File | protogen.Enum | None = None,
            option_type: protogen.Message | None = None) -> Dict:
        if option_type is None:
            if (isinstance(proto_entity, protogen.Message) or isinstance(proto_entity, protogen.Field) or
                    isinstance(proto_entity, protogen.Enum)):
                option_type = BaseProtoPlugin.get_complex_option_type(proto_entity.parent_file, option_name)
            elif isinstance(proto_entity, protogen.File):
                option_type = BaseProtoPlugin.get_complex_option_type(proto_entity, option_name)
            else:
                err_str = f"Unexpected: proto_entity type: {type(proto_entity)}, name: {proto_entity.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
        # else taking param value

        output_dict: Dict[str, Any] = {}
        for field in option_type.fields:
            if field.message is None:
                field_name_search_str = f" {field.proto.name}:"
                if field_name_search_str in option_string:
                    field_name_index = option_string.index(field_name_search_str)
                    option_string_sliced = option_string[field_name_index + len(field_name_search_str):]
                    new_line_index = option_string_sliced.index("\n")
                    field_val = BaseProtoPlugin._type_cast_option_str_val_to_type(option_string_sliced[:new_line_index],
                                                                                  field.kind.name.lower())

                    is_repeated = False
                    field_val_list = []
                    if field.cardinality.name.lower() == "repeated":
                        is_repeated = True
                        field_val_list.append(field_val)
                        while field_name_search_str in option_string_sliced:
                            field_name_index = option_string_sliced.index(field_name_search_str)
                            option_string_sliced = option_string_sliced[field_name_index+len(field_name_search_str):]
                            new_line_index = option_string_sliced.index("\n")
                            field_val = \
                                BaseProtoPlugin._type_cast_option_str_val_to_type(option_string_sliced[:new_line_index],
                                                                                  field.kind.name.lower())
                            field_val_list.append(field_val)

                    if is_repeated:
                        output_dict[field.proto.name] = field_val_list
                    else:
                        output_dict[field.proto.name] = field_val

            else:
                field_name_search_str = f"{field.proto.name}"+" {"
                if field_name_search_str in option_string:
                    field_name_index = option_string.index(field_name_search_str)
                    option_string_sliced = option_string[field_name_index + len(field_name_search_str):]
                    field_val = (
                        BaseProtoPlugin._get_complex_option_value_from_proto(option_string_sliced, option_type=field.message))

                    is_repeated = False
                    field_val_list = []
                    if field.cardinality.name.lower() == "repeated":
                        is_repeated = True
                        field_val_list.append(field_val)
                        while field_name_search_str in option_string_sliced:
                            field_name_index = option_string_sliced.index(field_name_search_str)
                            option_string_sliced = option_string_sliced[field_name_index + len(field_name_search_str):]
                            field_val = (
                                BaseProtoPlugin._get_complex_option_value_from_proto(option_string_sliced,
                                                                                     option_type=field.message))
                            field_val_list.append(field_val)

                    if is_repeated:
                        output_dict[field.proto.name] = field_val_list
                    else:
                        output_dict[field.proto.name] = field_val
        return output_dict

    @staticmethod
    def get_complex_option_value_from_proto(
            proto_entity: protogen.Message | protogen.Field | protogen.File | protogen.Enum, option_name: str,
            is_option_repeated: bool | None = None) -> List[Dict] | Dict:
        """
        Interface to get option values from proto model file
        :param proto_entity: proto entity of which option value is to be found
        :param option_name: options name string
        :param is_option_repeated: used to check if option is repeated or not
        :return: returns List[Dict] if `is_option_repeated` is True else returns Dict,
                 returns empty List or Dict if option is not found
        """
        option_string = str(proto_entity.proto.options)
        option_name_check_str = f"[{option_name}]"
        if option_name_check_str in option_string:

            # taking list of options_str if options is repeated type
            option_string_list = []
            if is_option_repeated:
                while option_name_check_str in option_string:
                    option_name_index = option_string.index(option_name_check_str)
                    option_string = option_string[option_name_index + len(option_name_check_str):]
                    if option_name_check_str in option_string:
                        option_string_list.append(option_string[:option_string.index(option_name_check_str)])
                    else:
                        option_string_list.append(option_string)
                repeated_option_value_as_list_of_dict: List[Dict] = []
                for option_string_ in option_string_list:
                    option_val_dict = BaseProtoPlugin._get_complex_option_value_from_proto(option_string_,
                                                                                           option_name, proto_entity)
                    repeated_option_value_as_list_of_dict.append(option_val_dict)
                return repeated_option_value_as_list_of_dict
            else:
                option_name_index = option_string.index(option_name_check_str)
                # removing unnecessary starting str
                option_string = option_string[option_name_index + len(option_name_check_str):]

                # checking if any more option after this is present in this option_str
                if "[FluxMsg" in option_string:
                    # if next option is found taking start of next option as end of current option str
                    option_str_end_index = option_string.index("[FluxMsg")
                    option_string = option_string[:option_str_end_index]
                # else not required: taking complete sliced option_str
                option_val_dict = BaseProtoPlugin._get_complex_option_value_from_proto(option_string,
                                                                                       option_name, proto_entity)
                return option_val_dict
        if is_option_repeated:
            return []
        else:
            return {}

    @staticmethod
    def get_dependency_message_proto_obj(file: protogen.File, message_name: str):
        for dependency in file.dependencies:
            for message in dependency.messages:
                if message.proto.name == message_name:
                    return message
        return None

    @staticmethod
    def get_complex_option_type(file: protogen.File, option_name: str) -> protogen.Message | None:
        """
        returns option type if is of complex type or returns None otherwise
        """
        for dependency in file.dependencies:
            if dependency.proto.name == BaseProtoPlugin.flux_option_file_name:
                for option_field in dependency.extensions:
                    if option_field.proto.name == option_name:
                        return option_field.message

    @staticmethod
    def get_simple_option_type(file: protogen.File, option_name: str) -> str:
        """
        returns option type if is of simple type or returns None otherwise
        """
        for dependency in file.dependencies:
            if dependency.proto.name == BaseProtoPlugin.flux_option_file_name:
                for option_field in dependency.extensions:
                    if option_field.proto.name == option_name:
                        return option_field.kind.name.lower()

    @staticmethod
    def get_flux_msg_cmt_option_value(message: protogen.Message) -> str:
        flux_msg_cmt_option_value = \
            BaseProtoPlugin.get_simple_option_value_from_proto(message,
                                                               BaseProtoPlugin.flux_msg_cmnt)
        return flux_msg_cmt_option_value[2:-1] \
            if flux_msg_cmt_option_value is not None else ""

    @staticmethod
    def get_flux_fld_cmt_option_value(field: protogen.Field) -> str:
        flux_fld_cmt_option_value = \
            BaseProtoPlugin.get_simple_option_value_from_proto(field, BaseProtoPlugin.flux_fld_cmnt)
        return flux_fld_cmt_option_value[2:-1] \
            if flux_fld_cmt_option_value is not None else ""

    @staticmethod
    def get_flux_file_cmt_option_value(file: protogen.File) -> str:
        flux_file_cmt_option_value = \
            BaseProtoPlugin.get_simple_option_value_from_proto(file, BaseProtoPlugin.flux_file_cmnt)
        return flux_file_cmt_option_value[2:-1] \
            if flux_file_cmt_option_value is not None else ""

    @staticmethod
    def import_path_from_os_path(os_path_env_var_name: str, import_file_name: str):
        # remove projects home prefix from all import paths
        if (project_root_dir := os.getenv("PROJECT_ROOT")) is not None and len(project_root_dir):
            if (pydantic_path := os.getenv(os_path_env_var_name)) is not None and len(pydantic_path):
                if pydantic_path is not None and pydantic_path.startswith("/"):
                    pydantic_path = pydantic_path.removeprefix(project_root_dir)
                else:
                    raise Exception(f"invalid absolute path: {pydantic_path}")
                if pydantic_path.startswith("/"):
                    pydantic_path = pydantic_path[1:]
                return f'{".".join(pydantic_path.split(os.sep))}.{import_file_name}'
            else:
                err_str = f"Env var '{os_path_env_var_name}' received as {pydantic_path}"
                logging.exception(err_str)
                raise Exception(err_str)
        else:
            err_str = f"Env var 'PROJECT_ROOT' received as {project_root_dir}"
            logging.exception(err_str)
            raise Exception(err_str)

    @staticmethod
    def import_path_from_path_str(path_str: str, import_file_name: str):
        if (project_root_dir := os.getenv("PROJECT_ROOT")) is not None and len(project_root_dir):
            if path_str.startswith("/"):
                pydantic_path = path_str.removeprefix(project_root_dir)
            else:
                raise Exception(f"invalid absolute path: {path_str}")
            if pydantic_path.startswith("/"):
                pydantic_path = pydantic_path[1:]
            return f'{".".join(pydantic_path.split(os.sep))}.{import_file_name}'
        else:
            err_str = f"Env var 'PROJECT_ROOT' received as {project_root_dir}"
            logging.exception(err_str)
            raise Exception(err_str)

    def proto_to_py_datatype(self, field: protogen.Field) -> str:
        match field.kind.name.lower():
            case "message":
                if self.is_bool_option_enabled(field.message, BaseProtoPlugin.flux_msg_json_root):
                    return f"{field.message.proto.name}BaseModel"
                else:
                    return field.message.proto.name
            case "enum":
                return field.enum.proto.name
            case other:
                if self.is_bool_option_enabled(field, BaseProtoPlugin.flux_fld_val_is_datetime):
                    return BaseProtoPlugin.pendulum_datetime_type
                else:
                    return BaseProtoPlugin.proto_type_to_py_type_dict[field.kind.name.lower()]

    def get_nested_field_proto_to_py_datatype(self, field: protogen.Field, field_str: str):
        """
        :param field: field from where nested field starts
        :param field_str: field_str having nested field dot seperated
        """
        nested_field: protogen.Field = self.get_nested_field_proto_object(field, field_str)
        return self.proto_to_py_datatype(nested_field)

    def get_nested_field_proto_object(self, field: protogen.Field, field_str: str):
        """
        :param field: field from where nested field starts
        :param field_str: field_str having nested field dot seperated
        """
        field_str_dot_sep = field_str.split(".")

        if field_str_dot_sep[0] == field.proto.name:
            # If field_str starts with current field name, removing first field
            field_str_dot_sep = field_str_dot_sep[1:]

        if len(field_str_dot_sep) > 1:
            for nested_field in field.message.fields:
                if nested_field.proto.name == field_str_dot_sep[0]:
                    self.get_nested_field_proto_to_py_datatype(nested_field, ".".join(field_str_dot_sep[1:]))
        # else not required: if field_str_dot_sep is length 1 that means, either recursion has reached
        # last nested field or field_str only wanted absolute next nested field, handling for both is present below

        # handling for last nested field
        for nested_field in field.message.fields:
            if nested_field.proto.name == field_str_dot_sep[0]:
                return nested_field

    @staticmethod
    def get_projection_option_value_to_fields(message: protogen.Message) -> Dict[str, List[str]]:
        """
        returns dict where key is either temp str of query_name or proposed query name from projections option value
        to all field names having that projection value. For nested projection option value, temp str of query name or
        proposed query name is sliced and taken as key of dict and value of dict is set of field names including
        nested path.
        """
        projection_val_to_fields_dict: Dict[str, List[str]] = {}
        for field in message.fields:
            if BaseProtoPlugin.is_option_enabled(field, BaseProtoPlugin.flux_fld_projections):
                projection_option_val_list: List[str] = (
                    BaseProtoPlugin.get_simple_option_value_from_proto(field, BaseProtoPlugin.flux_fld_projections,
                                                                       is_repeated=True))
                for projection_option_val in projection_option_val_list:
                    mapping_key: str | None = None
                    if ":" in projection_option_val:
                        mapping_key = projection_option_val.split(":")[0]
                        projection_key = projection_option_val.split(":")[-1]
                    else:
                        projection_key = projection_option_val

                    if projection_key not in projection_val_to_fields_dict:
                        projection_val_to_fields_dict[projection_key] = []

                    if mapping_key:
                        mapping_key_dot_sep = mapping_key.split(".")
                        if mapping_key_dot_sep[0] == field.proto.name:
                            if len(mapping_key_dot_sep) > 1:
                                mapping_key = ".".join(mapping_key_dot_sep[1:])
                            else:
                                mapping_key = None
                    if mapping_key:
                        field_name = f"{field.proto.name}.{mapping_key}"
                    else:
                        field_name = f"{field.proto.name}"
                    projection_val_to_fields_dict[projection_key].append(field_name)
        return projection_val_to_fields_dict

    @staticmethod
    def get_projection_temp_query_name_to_generated_query_name_dict(message: protogen.Message) -> Dict[str, str]:
        projection_val_to_fields_dict: Dict[str, List[str]] = (
            BaseProtoPlugin.get_projection_option_value_to_fields(message))
        projection_val_to_projection_query_name_dict = {}

        for projection_val, field_names in projection_val_to_fields_dict.items():
            if projection_val.isnumeric():
                # numeric values are mapped to generated query name
                field_name_list = []
                for field_name in field_names:
                    if "." in field_name:
                        field_name_list.append("_".join(field_name.split(".")))
                    else:
                        field_name_list.append(field_name)
                fields_name_str = "_n_".join(field_name_list)
                message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
                query_name = f"get_{fields_name_str}_projection_from_{message_name_snake_cased}"
                projection_val_to_projection_query_name_dict[projection_val] = query_name
            else:
                # other values are mapped to same value itself
                projection_val_to_projection_query_name_dict[projection_val] = projection_val
        return projection_val_to_projection_query_name_dict

    def get_time_series_data_from_msg(
            self, message: protogen.Message) -> Tuple[str, str | None, str | None, int | None]:
        option_value_dict = (
            self.get_complex_option_value_from_proto(message, BaseProtoPlugin.flux_msg_json_root_time_series))

        # getting time_field
        for field in message.fields:
            if BaseProtoPlugin.is_option_enabled(field, BaseProtoPlugin.flux_fld_val_time_field):
                time_field = field.proto.name
                break
        else:
            err_str = (f"Couldn't find any field with {BaseProtoPlugin.flux_fld_val_time_field} option "
                       f"set for message {message.proto.name} having "
                       f"{BaseProtoPlugin.flux_msg_json_root_time_series} option")
            logging.exception(err_str)
            raise Exception(err_str)

        # getting meta_field
        meta_field: str | None = None
        for field in message.fields:
            if BaseProtoPlugin.is_option_enabled(field, BaseProtoPlugin.flux_fld_val_meta_field):
                meta_field = field.proto.name
                break

        granularity = option_value_dict.get(BaseProtoPlugin.flux_json_root_ts_granularity_field)
        expire_after_sec = option_value_dict.get(BaseProtoPlugin.flux_json_root_ts_expire_after_sec_field)

        return time_field, meta_field, granularity, expire_after_sec

    def handle_import_file_gen(self, model_import_file_name: str, import_str_callable: Callable[..., Any]) -> str:
        if (output_dir_path := os.getenv("PLUGIN_OUTPUT_DIR")) is not None and len(output_dir_path):
            model_import_file_path = PurePath(output_dir_path) / model_import_file_name
            current_import_statements = import_str_callable()
            if (model_type_env_name := os.getenv("ModelType")) is None or len(model_type_env_name) == 0:
                err_str = f"env var ModelType received as {model_type_env_name}"
                logging.exception(err_str)
                raise Exception(err_str)
            if not os.path.exists(model_import_file_path):
                output_str = "import logging\n"
                output_str += "import os\n\n"
                output_str += 'if (model_type := os.getenv("ModelType")) is None or len(model_type) == 0:\n'
                output_str += '    err_str = f"env var DBType must not be {model_type}"\n'
                output_str += '    logging.exception(err_str)\n'
                output_str += '    raise Exception(err_str)\n'
                output_str += 'else:\n'
                output_str += '    match model_type.lower():\n'
                output_str += f'        case "{model_type_env_name}":\n'
                for import_statement in current_import_statements:
                    output_str += import_statement
                output_str += f'        case other:\n'
                output_str += '            err_str = f"unsupported db type {model_type}"\n'
                output_str += f'            logging.exception(err_str)\n'
                output_str += f'            raise Exception(err_str)\n'
                return output_str
            else:
                with open(model_import_file_path) as import_file:
                    imports_file_content: List[str] = import_file.readlines()
                    imports_file_content_copy: List[str] = copy.deepcopy(imports_file_content)
                    match_str_index = imports_file_content.index("    match model_type.lower():\n")

                    # checking if already imported
                    for content in imports_file_content[match_str_index:]:
                        if "case" in content and model_type_env_name in content:
                            # getting ending import line for current model_type_env_name
                            for line in imports_file_content[imports_file_content.index(content)+1:]:
                                if "case" in line:
                                    next_model_type_imports_index = imports_file_content.index(line)
                                    break
                            counter = 0
                            for index in range(imports_file_content.index(content), next_model_type_imports_index):
                                # if current model_type already exists in match statement then removing old import
                                del imports_file_content_copy[index-counter]
                                counter += 1
                            break
                        # else not required: if current model_type already not in match statement then no need
                        # to remove it
                    imports_file_content_copy.insert(match_str_index+1, f'        case "{model_type_env_name}":\n')
                    for index, import_statement in enumerate(current_import_statements):
                        imports_file_content_copy.insert(match_str_index+1+(index+1), import_statement)

                return "".join(imports_file_content_copy)
        else:
            err_str = f"Env var 'PLUGIN_OUTPUT_DIR' received as {output_dir_path}"
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

        if len(plugin.files_to_generate) > 1:
            plugin_arg = plugin.files_to_generate
            file = plugin_arg[0]
        elif len(plugin.files_to_generate) == 1:
            plugin_arg = plugin.files_to_generate[0]
            file = plugin_arg
        else:
            err_str = "Can't find input files required for plugin"
            logging.error(err_str)
            raise Exception(err_str)

        output_file_name_to_insertion_points_n_content_dict: Dict[str, Dict[str, str]] = {}
        received_output_file_name_to_content = self.output_file_generate_handler(plugin_arg)

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
    if (project_dir_path := os.getenv("PROJECT_DIR")) is not None and len(project_dir_path):
        pydantic_class_gen_plugin = plugin_class(project_dir_path)
        pydantic_class_gen_plugin.process()
    else:
        err_str = f"Env var 'PROJECT_DIR' received as {project_dir_path}"
        logging.exception(err_str)
        raise Exception(err_str)
