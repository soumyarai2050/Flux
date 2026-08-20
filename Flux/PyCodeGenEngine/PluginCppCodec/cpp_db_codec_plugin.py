#1/usr/bin/env python
import json
import logging
from pathlib import PurePath
from typing import List, Callable, Tuple, Dict
import os
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEPTIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case, YAMLConfigurationManager

root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core. yaml"
root_flux_core_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(root_flux_core_config_yaml_path))


class CppDbHandlerPlugin(BaseProtoPlugin):
    """
    Plugin to generate sample output to serialize and deserialize from proto schema
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.field = []
        self.package_name: str = ""

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def get_field_names(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root):
                field_names = [field.proto.name for field in message.fields]

                for field_name in field_names:
                    if field_name not in self.field:
                        self.field.append(field_name)

    def dependency_message_proto_msg_handler(self, file: protogen.File):
        # Adding messages from core proto files having json_root option
        project_dir = os.getenv("PROJECT_DIR")
        if project_dir is None or not project_dir:
            err_str = f"env var DBType received as {project_dir}"
            logging.exception(err_str)
            raise Exception(err_str)

        core_or_util_files: List[str] = root_flux_core_config_yaml_dict.get("core_or_util_files")

        if "ProjectGroup" in project_dir:
            project_group_flux_core_config_yaml_path = PurePath(project_dir).parent.parent / "flux_core.yaml"
            project_group_flux_core_config_yaml_dict = (
                YAMLConfigurationManager.load_yaml_configurations(str(project_group_flux_core_config_yaml_path)))
            project_grp_core_or_util_files = project_group_flux_core_config_yaml_dict.get("core_or_util_files")
            if project_grp_core_or_util_files:
                core_or_util_files.extend(project_grp_core_or_util_files)

        if core_or_util_files is not None:
            for dependency_file in file.dependencies:
                dependency_file_name: str = dependency_file.proto.name
                if dependency_file_name in core_or_util_files:
                    if dependency_file_name.endswith("_core.proto"):
                        if self.is_option_enabled \
                                    (file, self.flux_file_import_dependency_model):
                            msg_list = []
                            import_data = (self.get_complex_option_value_from_proto
                                           (file, self.flux_file_import_dependency_model, True))
                            for item in import_data:
                                import_file_name = item['ImportFileName']
                                import_model_name = item['ImportModelName']

                                if import_file_name == dependency_file_name:
                                    for msg in dependency_file.messages:
                                        if msg.proto.name in import_model_name:
                                            if msg not in msg_list:
                                                msg_list.append(msg)
                            self.root_message_list.extend(msg_list)
                # else not required: if dependency file name not in core_or_util_files
                # config list, avoid messages from it
        # else not required: core_or_util_files key is not in yaml dict config
    @staticmethod
    def headers_generate_handler(file_name: str, class_name: str):
        output_content: str = ""
        output_content += "#pragma once\n\n"
        # output_content += "#include <mutex>\n"
        # output_content += "#include <unordered_map>\n\n"
        # output_content += f'#include "../../cpp_app/include/{class_name}_mongo_db_handler.h"\n'
        # output_content += f'#include "../CppUtilGen/{class_name}_key_handler.h"\n'
        # output_content += f'#include "../../FluxCppCore/include/market_data_json_codec.h"\n'
        # output_content += f'#include "../CppUtilGen/{class_name}_max_id_handler.h"\n'
        output_content += f'#include <bsoncxx/builder/basic/document.hpp>\n'
        output_content += f'#include <optional>\n'
        output_content += f'#include "mongo_db_handler.h"\n\n'
        output_content += '#include "string_util.h"\n'
        output_content += f'#include ".. /CppUtilGen/{class_name}_constants.h"\n\n'
        return output_content

    def _emit_field(self, field: protogen.Field, doc_var: str, accessor: str,
                    num_of_tabs: int, package_name: str,
                    is_top_level: bool = False, scope_depth: int = 0) -> str:
        # Unified field emitter. Walks one proto field of a struct at C++
        # expression `accessor` and appends the BSON-builder code that
        # serializes it into the bsoncxx document named `doc_var`. Recurses
        # for message-typed and repeated-of-message subfields.
        #
        # `is_top_level=True` is set only for direct fields of a root model
        # (called from prepare_doc / prepare_list_doc). Top-level scalar `id`
        # fields are skipped; nested 'id' subfields are mapped to `_id`.
        # `scope_depth` tracks model recursion independently of output indentation.
        f_name = field.proto.name
        f_card = field.cardinality.name.Lower()
        is_dt = CppDbHandlerPlugin.is_option_enabled(field, CppDbHandlerPlugin.flux_fld_val_is_datetime)
        tabs = "\t" * num_of_tabs
        field_scope_depth = scope_depth + 1
        field_scope_suffix = f'_scope_{field_scope_depth}'

        # Top-level scalar 'id' is skipped (legacy: if field_name != "id":').
        if is_top_level and f_name == "id" and field.message is None:
            return ""

        # Build the kvp key expression. Nested 'id' -> bare "_id" string;
        # everything else -> namespaced constant name.
        if f_name == "id" and not is_top_level:
            key_expr = '"_id"'
        else:
            key_expr = f'{package_name}_handler::{f_name}_fld_name'

        # Build the value expression for scalar fields; datetime wraps with the
        # b_date converter.
        def scalar_value(elem_accessor: str) -> str:
            if is_dt:
                return f'FluxCppCore::BsonDateUtil::convert_utc_string_to_b_date({elem_accessor})'
            return elem_accessor

        if field.message is None:
            # Scalar / enum leaf
            value = scalar_value(f' {accessor}. {f_name}_')
            if f_card == "required":
                return tabs + f'{doc_var}.append(FluxCppCore::kvp({key_expr}, {value})); \n'
            if f_card == "optional":
                out = tabs + f'if ({accessor}.is_{f_name}_set_)\n'
                out += tabs + f'\t{doc_var}.append(FluxCppCore::kvp({key_expr}, {value})); \n'
                return out
            # repeated scalar
            self.get_cpp_storage_type_for_proto_kind(field.kind.name.lower())
            self.emit_repeated_scalar_codegen_info("cpp_db_codec_plugin", field.parent, field)
            list_name = f'{f_name}_list{field_scope_suffix}'
            elem_name = f'{f_name}_value{field_scope_suffix}'
            out = tabs + f'if ({accessor}.is_{f_name}_set_) {{\n'
            out += tabs + f'\tbsoncxx::builder::basic::array {list_name} ; \n'
            out += tabs + f'\tfor (const auto& {elem_name} : {accessor}. {f_name}_) {{\n'
            out += tabs + f'\t\t{list_name}.append({elem_name}) ; \n'
            out += tabs + f'\t}}\n'
            out += tabs + f'\t{doc_var}.append(FuxCppCore::kvp({key_expr}, {list_name})) ; \n'
            out += tabs + f'}}\n'
            return out

        # Message-typed subfield: build sub-document (or array of sub-documents).
        sub_doc = f'{f_name}_document{field_scope_suffix}'
        if f_card == "repeated":
            list_name = f'{f_name}_list{field_scope_suffix}'
            elem_name = f'{f_name}_value{field_scope_suffix}'
            out = tabs + f'if ({accessor}.is_{f_name}_set_) {{\n'
            out += tabs + f'\tbsoncxx::builder::basic::array {list_name} ; \n'
            out += tabs + f'\tfor (const auto& {elem_name} : {accessor}. {f_name}_) {{\n'
            out += tabs + f'\t\tbsoncxx::builder::basic::document {sub_doc} ; \n'
            for sub_field in field.message.fields:
                out += self._emit_field(sub_field, sub_doc, elem_name,
                                         num_of_tabs + 2, package_name,
                                         scope_depth=field_scope_depth)
            out += tabs + f'\t\t{list_name}.append({sub_doc}); \n'
            out += tabs + f'\t}}\n'
            out += tabs + f'\t{doc_var}.append(FluxCppCore::kvp({key_expr}, {list_name})); \n'
            out += tabs + f'}}\n'
            return out

        if f_card == "optional":
            out = tabs + f'if ({accessor}.is_{f_name}_set_) {{\n'
            out += tabs + f'\tbsoncxx::builder::basic::document {sub_doc}; \n'
            for sub_field in field.message.fields:
                out += self._emit_field(sub_field, sub_doc, f' {accessor}. {f_name}_',
                                         num_of_tabs + 1, package_name,
                                         scope_depth=field_scope_depth)
            out += tabs + f'\t{doc_var}.append(FluxCppCore::kvp({key_expr}, {sub_doc})); \n'
            out += tabs + f'}}\n'
            return out

        # required message
        out = tabs + f'bsoncxx::builder::basic::document {sub_doc}; \n'
        for sub_field in field.message.fields:
            out += self._emit_field(sub_field, sub_doc,f' {accessor}. {f_name}_',
                                     num_of_tabs, package_name,
                                     scope_depth=field_scope_depth)
        out += tabs + f'{doc_var}.append(FluxCppCore::kvp({key_expr}, {sub_doc}));\n'
        return out

    def generate_prepare_doc(self, message: protogen.Message, message_name_snake_cased: str,
                             package_name: str, message_name: str):
        # prepare_doc(const T& kr _< msg>_obj, document& r _< msg>_document)
        # Walks every direct field of 'message' via the unified _emit_field
        # emitter, anchored at accessor 'kr _< msg>_obj' and writing into
        # bsoncxx document 'r _< msg>_document' at indent depth 2.
        accessor = f"kr_{message_name_snake_cased}_obj"
        doc_var = f"r_{message_name_snake_cased}_document"
        out = f"\tinline void prepare_doc(const {message_name} &{accessor}, " \
              f"bsoncxx::builder::basic::document &{doc_var}) "
        out += " {\n"
        for field in message.fields:
            out += self._emit_field(field, doc_var, accessor,
                                     num_of_tabs=2, package_name=package_name,
                                     is_top_level=True)
        return out

    def generate_prepare_docs(self, message: protogen.Message, message_name_snake_cased: str,
                              package_name: str, message_name: str):
        # prepare_list_doc(const TList& r _< msg>_list_obj,
        #                  vector<document>& r_<msg>_document_list)
        # Iterates the list and for each element, walks every direct field via
        # _emit_field anchored at `r _< msg>_list_obj .< msg> _. at(i)` (indent 3).
        # The trailing emplace_back + closing braces are appended by the
        # caller (output_file_generate_handler) for historical layout reasons.
        list_obj = f"r_{message_name_snake_cased}_list_obj"
        accessor = f"{list_obj}.{message_name_snake_cased}_.at(i)"
        doc_var = f"r_{message_name_snake_cased}_document"
        out = f"\tinline void prepare_list_doc(const {message_name}List " \
              f"&{list_obj}, std::vector<bsoncxx::builder::basic::document> " \
              f"&{doc_var}_list) "
        out += " {\n"
        out += f"\t\tfor (size_t i =0; i < {list_obj}.{message_name_snake_cased}_.size(); ++i) {{\n"
        out += f"\t\t\tbsoncxx::builder::basic::document {doc_var}; \n"
        for field in message.fields:
            out += self._emit_field(field, doc_var, accessor,
                                     num_of_tabs=3, package_name=package_name,
                                     is_top_level=True)
        return out

    def _get_relevant_patch_ops_by_root_option(self, message: protogen.Message) -> Dict[str, List[str]]:
        patch_ops_by_root_option: Dict[str, List[str]] = {}
        for root_option in (self.flux_msg_cpp_json_root, self.flux_msg_json_root_time_series):
            if self.is_option_enabled(message, root_option):
                root_ops = self.get_complex_option_value_from_proto(message, root_option, False) or {}
                patch_ops = [
                    op for op in (self.flux_json_root_patch_field, self.flux_json_root_patch_all_field)
                    if op in root_ops
                ]
                if patch_ops:
                    patch_ops_by_root_option[root_option] = patch_ops
        return patch_ops_by_root_option

    @staticmethod
    def _collect_repeated_scalar_paths(message: protogen.Message) -> List[Tuple[str, str]]:
        repeated_scalar_paths: List[Tuple[str, str]] = []

        def walk(msg: protogen.Message, path_prefix: str, active_types: set[str]) -> None:
            msg_name = msg.proto. name
            if msg_name in active_types:
                return
            active_types.add(msg_name)
            try:
                for fld in msg.fields:
                    fld_kind = fld.kind.name.lower()
                    fld_cardinality = fld.cardinality.name.lower()
                    fld_path = f"{path_prefix}.{fld.proto.name}" if path_prefix else fld.proto.name
                    if fld.message is None:
                        if fld_cardinality == "repeated":
                            repeated_scalar_paths.append((fld_path, fld_kind))
                    else:
                        child_path = f"{fld_path}[]" if fld_cardinality == "repeated" else fld_path
                        walk(fld.message, child_path, active_types)
            finally:
                active_types.remove(msg_name)

        walk(message, "", set())
        return repeated_scalar_paths

    def _validate_patch_repeated_scalar_compatibility(self, file: protogen.File,
                                                      message: protogen.Message) -> None:
        patch_ops_by_root_option = self._get_relevant_patch_ops_by_root_option(message)
        if not patch_ops_by_root_option:
            return

        repeated_scalar_paths = self._collect_repeated_scalar_paths(message)
        if not repeated_scalar_paths:
            return

        patch_ops_lines = [
            f" - {root_option}: {', '.join(patch_ops)}"
            for root_option, patch_ops in patch_ops_by_root_option.items()
        ]
        field_lines = [
            f" - {field_path} : repeated {fld_kind}"
            for field_path, fld_kind in repeated_scalar_paths
        ]
        raise ValueError(
            "C++ MongoDB codec generation rejects PatchOp/PatchAllOp for a "
            "root model whose transitive field tree contains repeated scalar "
            "or enum fields. \n"
            f"Proto file: {file.proto.name}\n"
            f"Root message: {message.proto.name}\n"
            "Enabled patch operations by root option: \n"
            f"{chr(10).join(patch_ops_lines)}\n"
            "Repeated scalar/enum fields: \n"
            f"{chr(10).join(field_lines)}\n"
            "Remediation: remove PatchOp/PatchALLOp from the offending root "
            "option block(s), switch to PUT/full-document replace only, or "
            "remodel the field as repeated <message-with-id> so MongoDB "
            "element-level patch can target individual elements by _id.")

    def output_file_generate_handler(self, file: protogen.File):
        # pre-requisite calls
        self.get_all_root_message(file.messages)
        self.dependency_message_proto_msg_handler(file)
        self.get_field_names(self.root_message_list)
        file_name = str(file.proto.name).split(".")[0]
        package_name = str(file.proto.package)
        self.package_name = package_name
        output_content = ""

        class_name_list = package_name.split("_")
        class_name = ''.join(word.capitalize() for word in class_name_list)
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content += self.headers_generate_handler(file_name, class_name_snake_cased)

        output_content += f"namespace {class_name_snake_cased}_handler {{\n\n"

        for message in self.root_message_list:
            self._validate_patch_repeated_scalar_compatibility(file, message)

        # -----------------------------------------------------------------
        # CODEC EMISSION GATE - LOCKSTEP ANCHOR (do NOT change in isolation)
        # This gate (Python root OR TS root, NOT C++ root) decides which
        # messages get prepare_doc / prepare_list_doc emitted in
        # <svc>_mongo_db_codec.h. Two other plugins reference the symbols
        # produced here and MUST stay in sync, else the C++ build fails with
        # undefined-symbol link errors:
        #  1. PyCodeGenEngine/PluginCppTest/cpp_codec_test_plugin.py
        #     is_current_codec_root() (around Line 36) - gtest scaffolding
        #     that calls prepare_doc; mirrors this gate verbatim.
        #  2. PyCodeGenEngine/PluginCppCodec/cpp_db_test_cpp_plugin.py
        #     (around line 57) - currently has its emission gate commented
        #     out and produces an include-only .cpp; if that gate is ever
        #     restored, it must mirror this one.
        # If you change this gate (Python U TS) > also update both above and
        # regen all three to verify symbol parity. Audit context:
        # /export/home/sumkumar/.claude/projects/-export-home-sumkumar-data-sumkumar-apps-trade-engine/memory/project_root_option_gate_audit.md
        # -------------------------------------------------------------------
        for message in self.root_message_list:
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root) or \
                    CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root_time_series):
                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    # if CppDbHandlerPlugin.is_option_enabled(field, "FluxFldPk"):
                    message_name = message.proto.name
                    message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                    output_content += self.generate_prepare_doc(message, message_name_snake_cased, package_name,
                                                                message_name)
                    output_content += "\t}\n\n"
                    output_content += self.generate_prepare_docs(message, message_name_snake_cased, package_name,
                                                                 message_name)
                    output_content += f"\t\t\tr_{message_name_snake_cased}_document_list.emplace_back(std::move(" \
                                      f"r_{message_name_snake_cased}_document)); \n"
                    output_content += "\t\t}\n\t}\n\n"

                    # output_content += "\t};\n\n"
                    break

        # Generate TimeSeriesConfig factory functions for models with both
        # FluxMsgCppJsonRoot and FluxMsgJsonRootTimeSeries options
        granularity_map = {"Sec": "seconds", "Min": "minutes", "Hrs": "hours"}
        for message in self.root_message_list:
            if (CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_cpp_json_root) and
                    CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root_time_series)):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
                time_field, meta_field, granularity, expire_after_sec = self.get_time_series_data_from_msg(message)
                granularity_str = granularity_map.get(str(granularity), "seconds")
                expire_val=expire_after_sec if expire_after_sec else 0
                meta_field_str = meta_field if meta_field else ""

                output_content += f'\tinline FluxCppCore::TimeSeriesConfig get_{message_name_snake_cased}_ts_config() {{\n'
                output_content += f'\t\treturn {{"{time_field}", "{meta_field_str}", "{granularity_str}", {expire_val}}}; \n'
                output_content += f'\t}}\n\n'

        # Generate get_ts_config_by_name() dispatcher for auto-detection in MongoDBCodec constructor
        ts_model_names = []
        for message in self.root_message_list:
            if (CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_cpp_json_root) and
                    CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root_time_series)):
                ts_model_names.append((message.proto.name, convert_camel_case_to_specific_case(message.proto.name)))

        if ts_model_names:
            output_content += '\tinline std::optional<FluxCppCore::TimeSeriesConfig> get_ts_config_by_name(const std::string& name) {\n'
        for model_name, snake_name in ts_model_names:
            output_content += f'\t\tif (name == "{model_name}") return get_{snake_name}_ts_config(); \n'
        output_content += '\t\treturn std::nullopt;\n'
        output_content += '\t}\n\n'

        output_content += "}\n"

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{class_name_snake_cased}_mongo_db_codec.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppDbHandlerPlugin)