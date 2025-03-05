#!/usr/bin/env python
from pathlib import PurePath
from typing import List
import os
import time
import logging

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.file_n_general_utility_functions import (convert_camel_case_to_specific_case, YAMLConfigurationManager)
from FluxPythonUtils.scripts.general_utility_functions import convert_to_capitalized_camel_case
from Flux.CodeGenProjects.TradeEngine.ProjectGroupPlugins.PluginStratExecutor.strat_executor_plugin import \
    StratExecutorPlugin

root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
root_flux_core_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(
    str(root_flux_core_config_yaml_path))


class CppWebServers(BaseProtoPlugin):
    """
    Plugin to generate sample output to key generate from proto schema
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.root_message_name_list: List[str] = []
        self.field = []
        self.depend_msg_list: List[protogen.Message] = []

    def get_nested_msg(self, msg: protogen.Message):
        for fld in msg.fields:
            if fld.message is not None and fld.message not in self.depend_msg_list:
                self.get_nested_msg(fld.message)
                self.depend_msg_list.append(fld.message)

    def generate_create_route(self, mas_name_snake_cased: str):
        return (f'\t\tRoute{{"create-{mas_name_snake_cased}", std::regex(R"(^/create-{mas_name_snake_cased}$)"), '
                f'{{boost::beast::http::verb::post}}, [this](auto& req, auto& res, auto& match) '
                f'{{ create_{mas_name_snake_cased}(req, res, match); }}}},\n')

    def generate_get_all_route(self, mas_name_snake_cased):
        return (f'\t\tRoute{{"get-all-{mas_name_snake_cased}", std::regex(R"(^/get-all-{mas_name_snake_cased}(\\?.*)?$)"), {{'
                f'boost::beast::http::verb::get}}, [this](auto& req, auto& res, auto& match) {{ '
                f'get_all_{mas_name_snake_cased}(req, res, match); }}}},\n')

    def generate_get_route(self, mas_name_snake_cased):
        return (f'\t\tRoute{{"get-{mas_name_snake_cased}/{{{mas_name_snake_cased}_id}}", std::regex('
                f'R"(^/get-{mas_name_snake_cased}/(\\d+)$)"), {{boost::beast::http::verb::get}}, [this]('
                f'auto& req, auto& res, auto& match) {{ get_{mas_name_snake_cased}_by_id(req, res, '
                f'match); }}}},\n')

    def generate_put_route(self, mas_name_snake_cased):
        return (f'\t\tRoute{{"put-{mas_name_snake_cased}", std::regex(R"(^/put-{mas_name_snake_cased}$)"), {{'
                f'boost::beast::http::verb::put}}, [this](auto& req, auto& res, auto& match) {{ '
                f'put_{mas_name_snake_cased}(req, res, match); }}}},\n')

    def generate_patch_route(self, mas_name_snake_cased):
        return (f'\t\tRoute{{"patch-{mas_name_snake_cased}", std::regex(R"(^/patch-{mas_name_snake_cased}$)"), {{'
                f'boost::beast::http::verb::patch}}, [this](auto& req, auto& res, auto& match) {{ '
                f'patch_{mas_name_snake_cased}(req, res, match); }}}},\n')

    def generate_delete_route(self, mas_name_snake_cased):
        return (f'\t\tRoute{{"delete-{mas_name_snake_cased}/{{{mas_name_snake_cased}_id}}", std::regex(R"('
                f'^/delete-{mas_name_snake_cased}/(\\d+)$)"), {{boost::beast::http::verb::'
                f'delete_}}, [this](auto& req, auto& res, auto& match) {{ '
                f'delete_{mas_name_snake_cased}_by_id(req, res, match); }}}},\n')

    def generate_delete_all_route(self, mas_name_snake_cased):
        return (f'\t\tRoute{{"delete-all-{mas_name_snake_cased}", std::regex(R"(^/delete-all-'
                f'{mas_name_snake_cased}$)"), {{boost::beast::http::verb::delete_}}, [this]'
                f'(auto& req, auto& res, auto& match) {{ delete_all_{mas_name_snake_cased}('
                f'req, res, match); }}}},\n')

    def generate_time_series_create(self, package_name: str, class_name: str, msg_name: str, mas_name_snake_cased: str,
                                    msg: protogen.Message):
        output_content = ""
        output_content += (f'void {class_name}WebNWsServer::create_{mas_name_snake_cased}(boost::beast::http::request<boost::beast::'
                           f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                           f'string_body>& res, [[maybe_unused]] const std::smatch&) {{\n')
        output_content += f'\tif (req.method() == boost::beast::http::verb::post) {{\n'
        output_content += '\t\ttry {\n'
        output_content += '\t\t\tboost::json::object json;\n'
        output_content += '\t\t\tMarketDataJsonToObject::parse_string_to_json(req.body(), json);\n'
        output_content += '\t\t\tif (!json.if_contains("_id")) {\n'
        output_content += (f'\t\t\t\tjson["_id"] = json["_id"] = ++{mas_name_snake_cased}_db_id_;\n')
        output_content += '\t\t\t}\n'
        for fld in msg.fields:
            if fld.message is not None:
                for f in fld.message.fields:
                    if f.proto.name == "id":
                        output_content += f'\t\t\tif (json.if_contains("{fld.proto.name}")) {{\n'
                        output_content += (f'\t\t\t\tauto {fld.proto.name}_json = json['
                                           f'"{fld.proto.name}"].get_object();\n')
                        output_content += f'\t\t\t\tif (!{fld.proto.name}_json.if_contains("_id")) {{\n'
                        if f.kind.name.lower() == "string":
                            output_content += (f'\t\t\t\t\t{fld.proto.name}_json["_id"] = '
                                               f'std::to_string({mas_name_snake_cased}_db_id_);\n')
                        else:
                            output_content += (f'\t\t\t\t\t{fld.proto.name}_json["_id"] = '
                                               f'{mas_name_snake_cased}_db_id_;\n')
                        output_content += f'\t\t\t\t\tjson["{fld.proto.name}"] = {fld.proto.name}_json;\n'
                        output_content += f'\t\t\t\t}}\n'
                        output_content += f'\t\t\t}}\n'
        output_content += f'\t\t\t{msg_name} {mas_name_snake_cased};\n'
        output_content += f'\t\t\t{class_name}JsonToObject::json_to_object(boost::json::serialize(json), {mas_name_snake_cased});\n'
        output_content += f'\t\t\tm_{package_name}_publisher_->process_{mas_name_snake_cased}({mas_name_snake_cased});\n'
        output_content += (f'\t\t\tm_{package_name}_publisher_->get_{mas_name_snake_cased}('
                           f'{mas_name_snake_cased}, {mas_name_snake_cased}_db_id_);\n')
        output_content += (f"\t\t\t{class_name}ObjectToJson::object_to_json({mas_name_snake_cased}, "
                           f"json);\n")
        output_content += f'\t\t\tres.result(boost::beast::http::status::created);\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += (f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string'
                           f'(boost::json::serialize(json).size()));\n')
        output_content += f'\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t}} catch (std::exception& e) {{\n'
        output_content += '\t\t\tboost::json::object json;\n'
        output_content += f'\t\t\tjson["detail"] = e.what();\n'
        output_content += f'\t\t\tres.result(boost::beast::http::status::bad_request);\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += (f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string('
                           f'boost::json::serialize(json).size()));\n')
        output_content += f'\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t}}\n'
        output_content += f'\t}} else {{\n'
        output_content += f'\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
        output_content += f'\t}}\n'
        output_content += f'}}\n\n'

        return output_content

    def generate_create_method(self, package_name: str, class_name: str, msg_name: str, mas_name_snake_cased: str,
                               msg: protogen.Message):
        output_content = ""
        output_content += (f'void {class_name}WebNWsServer::create_{mas_name_snake_cased}(boost::beast::http::request<boost::beast::'
                           f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                           f'string_body>& res, [[maybe_unused]] const std::smatch&) {{\n')
        output_content += f'\tif (req.method() == boost::beast::http::verb::post) {{\n'
        output_content += "\t\ttry {\n"
        output_content += '\t\t\tboost::json::object json;\n'
        output_content += '\t\t\tMarketDataJsonToObject::parse_string_to_json(req.body(), json);\n'
        output_content += '\t\t\tif (!json.if_contains("_id")) {\n'
        output_content += (f'\t\t\t\tjson["_id"] = m_{package_name}_publisher_->'
                           f'get_next_insert_id_{mas_name_snake_cased}();\n')
        output_content += '\t\t\t}\n'
        output_content += f'\t\t\t{msg_name} {mas_name_snake_cased};\n'
        output_content += f'\t\t\t{class_name}JsonToObject::json_to_object(boost::json::serialize(json), {mas_name_snake_cased});\n'
        output_content += (f'\t\t\tauto inserted_id = m_{package_name}_publisher_->insert_{mas_name_snake_cased}('
                           f'{mas_name_snake_cased});\n')
        output_content += f'\t\t\tif (inserted_id == -1) {{\n'
        output_content += f'\t\t\t\tres.result(boost::beast::http::status::internal_server_error);\n'
        output_content += f'\t\t\t}} else {{\n'
        # output_content += f'\t\t\t\tstd::string key;\n'
        # output_content += f'\t\t\t\t{class_name}KeyHandler::get_key_out({mas_name_snake_cased}, key);\n'
        # output_content += (f'\t\t\t\tm_{package_name}_publisher_->m_{mas_name_snake_cased}_codec_.'
        #                    f'm_root_model_key_to_db_id[key] = {mas_name_snake_cased}.id_;\n')
        output_content += f'\t\t\t\tm_{package_name}_publisher_->process_{mas_name_snake_cased}({mas_name_snake_cased});\n'
        output_content += (f'\t\t\t\tm_{package_name}_publisher_->get_{mas_name_snake_cased}('
                           f'{mas_name_snake_cased}, {mas_name_snake_cased}.id_);\n')
        output_content += (f"\t\t\t\t{class_name}ObjectToJson::object_to_json({mas_name_snake_cased}, "
                           f"json);\n")
        output_content += f'\t\t\t\tres.result(boost::beast::http::status::created);\n'
        output_content += f'\t\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += (f'\t\t\t\tres.set(boost::beast::http::field::content_length, std::to_string'
                           f'(boost::json::serialize(json).size()));\n')
        output_content += f'\t\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\t\tres.prepare_payload();\n'
        output_content += "\t\t\t}\n"
        output_content += "\t\t} catch (std::exception& e) {\n"
        output_content += f'\t\t\tres.result(boost::beast::http::status::bad_request);\n'
        output_content += f'\t\t\tboost::json::object json;\n'
        output_content += f'\t\t\tjson["error"] = e.what();\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += (f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string('
                           f'boost::json::serialize(json).size()));\n')
        output_content += f'\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t}}\n'
        output_content += f'\t}} else {{\n'
        output_content += f'\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
        output_content += f'\t}}\n'
        output_content += f'}}\n\n'

        return output_content

    def generate_put_method(self, package_name: str, class_name: str, msg_name: str, mas_name_snake_cased: str,
                            msg: protogen.Message):
        output_content = ""
        output_content += (f'void {class_name}WebNWsServer::put_{mas_name_snake_cased}(boost::beast::http::request<boost::beast::'
                           f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                           f'string_body>& res, [[maybe_unused]] const std::smatch& match) {{\n')
        output_content += f'\tif (req.method() == boost::beast::http::verb::put) {{\n'
        output_content += '\t\ttry {\n'
        output_content += f'\t\t\t{msg_name} {mas_name_snake_cased};\n'
        output_content += f'\t\t\t{class_name}JsonToObject::json_to_object(req.body(), {mas_name_snake_cased});\n'
        output_content += (f'\t\t\tauto inserted_id = m_{package_name}_publisher_->patch_{mas_name_snake_cased}('
                           f'{mas_name_snake_cased});\n')
        output_content += f'\t\t\tif (!inserted_id) {{\n'
        output_content += f'\t\t\t\tres.result(boost::beast::http::status::bad_request);\n'
        output_content += f'\t\t\t\tboost::json::object json;\n'
        output_content += (f'\t\t\t\tjson["detail"] = "Id not Found: {msg_name} " + std::to_string('
                           f'{mas_name_snake_cased}.id_);\n')
        output_content += f'\t\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += (f'\t\t\t\tres.set(boost::beast::http::field::content_length, std::'
                           f'to_string(boost::json::serialize(json).size()));\n')
        output_content += f'\t\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t\t}} else {{\n'
        output_content += f'\t\t\t\tm_{package_name}_publisher_->process_{mas_name_snake_cased}({mas_name_snake_cased});\n'
        output_content += f'\t\t\t\tboost::json::object json;\n'
        output_content += (f'\t\t\t\tm_{package_name}_publisher_->get_{mas_name_snake_cased}('
                           f'{mas_name_snake_cased}, {mas_name_snake_cased}.id_);\n')
        output_content += (f'\t\t\t\t{class_name}ObjectToJson::object_to_json({mas_name_snake_cased}, '
                           f'json);\n')
        output_content += f'\t\t\t\tres.result(boost::beast::http::status::ok);\n'
        output_content += f'\t\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += f'\t\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(boost::json::serialize(json).size()));\n'
        output_content += f'\t\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\t\tres.prepare_payload();\n'
        output_content += "\t\t\t}\n"
        output_content += f'\t\t}} catch (std::exception& e) {{\n'
        output_content += "\t\t\tboost::json::object json;\n"
        output_content += f'\t\t\tjson["detail"] = e.what();\n'
        output_content += f'\t\t\tres.result(boost::beast::http::status::bad_request);\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += (f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string('
                           f'boost::json::serialize(json).size()));\n')
        output_content += f'\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\tres.prepare_payload();\n'
        output_content += "\t\t}\n"
        output_content += f'\t}} else {{\n'
        output_content += f'\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
        output_content += f'\t}}\n'
        output_content += f'}}\n\n'

        return output_content

    def generate_patch_method(self, package_name: str, class_name: str, msg_name: str, mas_name_snake_cased: str,
                              msg: protogen.Message):
        output_content = ""
        output_content += (f'void {class_name}WebNWsServer::patch_{mas_name_snake_cased}(boost::beast::http::request<boost::beast::'
                           f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                           f'string_body>& res, [[maybe_unused]] const std::smatch& match) {{\n')
        output_content += f'\tif (req.method() == boost::beast::http::verb::patch) {{\n'
        output_content += "\t\ttry {\n"
        output_content += f'\t\t\tauto json_obj = boost::json::parse(req.body()).as_object();\n'
        output_content += f'\t\t\tint64_t patch_id{{0}};\n'
        output_content += f'\t\t\ttry {{\n'
        output_content += f'\t\t\t\tpatch_id = json_obj["_id"].as_int64();\n'
        output_content += '\t\t\t} catch (std::exception& e) {\n'
        output_content += (f'\t\t\t\tthrow std::invalid_argument(std::format("Error processing `_id`'
                           f': {{}}", e.what()));\n')
        output_content += '\t\t\t}\n\n'
        output_content += f'\t\t\t{msg_name} {mas_name_snake_cased};\n'
        output_content += (f'\t\t\tif (m_{package_name}_publisher_->get_{mas_name_snake_cased}('
                           f'{mas_name_snake_cased}, patch_id)) {{\n')
        output_content += f'\t\t\t\tboost::json::object {mas_name_snake_cased}_json;\n'
        output_content += (f'\t\t\t\t{class_name}ObjectToJson::object_to_json({mas_name_snake_cased}, '
                           f'{mas_name_snake_cased}_json);\n')
        output_content += f'\t\t\t\tfor (const auto& [key, val] : json_obj) {{\n'
        output_content += f'\t\t\t\t\t{mas_name_snake_cased}_json[key] = val;\n'
        output_content += f'\t\t\t\t}}\n'
        output_content += (f'\t\t\t\t{class_name}JsonToObject::json_to_object(boost::json::serialize('
                           f'{mas_name_snake_cased}_json), {mas_name_snake_cased});\n')
        output_content += (f'\t\t\t\tauto inserted_id = m_{package_name}_publisher_->'
                           f'patch_{mas_name_snake_cased}(patch_id, json_obj);\n')
        output_content += f'\t\t\t\tif (!inserted_id) {{\n'
        output_content += f'\t\t\t\t\tres.result(boost::beast::http::status::bad_request);\n'
        output_content += f'\t\t\t\t\tboost::json::object json;\n'
        output_content += (f'\t\t\t\t\tjson["detail"] = "Id not Found: {msg_name} " + std::to_string('
                           f'patch_id);\n')
        output_content += f'\t\t\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += (f'\t\t\t\t\tres.set(boost::beast::http::field::content_length, std::'
                           f'to_string(boost::json::serialize(json).size()));\n')
        output_content += f'\t\t\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t\t\t}} else {{\n'
        output_content += f'\t\t\t\t\t{msg_name} {mas_name_snake_cased};\n'
        output_content += (f'\t\t\t\t\tm_{package_name}_publisher_->get_{mas_name_snake_cased}('
                           f'{mas_name_snake_cased}, patch_id);\n')
        output_content += f'\t\t\t\t\tm_{package_name}_publisher_->process_{mas_name_snake_cased}({mas_name_snake_cased});\n'
        output_content += f'\t\t\t\t\tboost::json::object json;\n'

        output_content += (
            f'\t\t\t\t\t{class_name}ObjectToJson::object_to_json({mas_name_snake_cased}, '
            f'json);\n')
        output_content += f'\t\t\t\t\tres.result(boost::beast::http::status::ok);\n'
        output_content += f'\t\t\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += f'\t\t\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(boost::json::serialize(json).size()));\n'
        output_content += f'\t\t\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\t\t\tres.prepare_payload();\n'
        output_content += "\t\t\t\t}\n"
        output_content += f'\t\t\t}} else {{\n'
        output_content += f'\t\t\t\tres.result(boost::beast::http::status::bad_request);\n'
        output_content += f'\t\t\t\tboost::json::object json;\n'
        output_content += (f'\t\t\t\tjson["detail"] = "Id not Found: {msg_name} " + std::to_string('
                           f'patch_id);\n')
        output_content += f'\t\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += (f'\t\t\t\tres.set(boost::beast::http::field::content_length, std::'
                           f'to_string(boost::json::serialize(json).size()));\n')
        output_content += f'\t\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t\t}}\n\n'
        # output_content += f'\t\t\t{class_name}JsonToObject::json_to_object(req.body(), {mas_name_snake_cased});\n'
        output_content += "\t\t} catch (std::exception& e) {\n"
        output_content += "\t\t\tboost::json::object json;\n"
        output_content += f'\t\t\tjson["detail"] = e.what();\n'
        output_content += f'\t\t\tres.result(boost::beast::http::status::bad_request);\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += (f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string('
                           f'boost::json::serialize(json).size()));\n')
        output_content += f'\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\tres.prepare_payload();\n'
        output_content += "\t\t}\n"
        output_content += f'\t}} else {{\n'
        output_content += f'\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
        output_content += f'\t}}\n'
        output_content += f'}}\n\n'

        return output_content

    def generate_get_method(self, package_name: str, class_name: str, msg_name: str, mas_name_snake_cased: str,
                            msg: protogen.Message):
        output_content = ""
        output_content += (f'void {class_name}WebNWsServer::get_{mas_name_snake_cased}_by_id(boost::beast::http::request<boost::beast::'
                           f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                           f'string_body>& res, [[maybe_unused]] const std::smatch& match) {{\n')
        output_content += f'\tif (req.method() == boost::beast::http::verb::get) {{\n'
        output_content += f'\t\t{msg_name} {mas_name_snake_cased};\n'
        # output_content += (f'\t\t\tm_{package_name}_publisher_->m_{mas_name_snake_cased}_codec_.get_data_by_id_from_collection('
        #                    f'{mas_name_snake_cased}, stoi(match[1]));\n')
        output_content += f'\t\tboost::json::object json;\n'
        output_content += (f'\t\tif (m_{package_name}_publisher_->get_{mas_name_snake_cased}('
                           f'{mas_name_snake_cased}, stoi(match[1]))) {{\n')
        output_content += f'\t\t\t{class_name}ObjectToJson::object_to_json({mas_name_snake_cased}, json);\n'
        output_content += f'\t\t\tres.result(boost::beast::http::status::ok);\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(boost::json::serialize(json).size()));\n'
        output_content += f'\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t}} else {{\n'
        output_content += f'\t\t\tjson["detail"] = "Id not Found: {msg_name} " + match[1].str();\n'
        output_content += f'\t\t\tres.result(boost::beast::http::status::bad_request);\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(boost::json::serialize(json).size()));\n'
        output_content += f'\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t}}\n'
        output_content += f'\t}} else {{\n'
        output_content += f'\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
        output_content += f'\t}}\n'
        output_content += f'}}\n\n'

        return output_content

    def generate_get_all_method(self, package_name: str, class_name: str, msg_name: str, mas_name_snake_cased: str,
                                msg: protogen.Message):
        output_content = ""
        output_content += (f'void {class_name}WebNWsServer::get_all_{mas_name_snake_cased}(boost::beast::http::request<boost::beast::'
                           f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                           f'string_body>& res, [[maybe_unused]] const std::smatch& match) {{\n')
        output_content += f'\tif (req.method() == boost::beast::http::verb::get) {{\n'
        output_content += '\t\tstd::string target = std::string(req.target());\n'
        output_content += '\t\tstd::regex limit_regex(R"(limit_obj_count=(-?\\d+))");\n'
        output_content += '\t\tstd::smatch limit_match;\n'
        output_content += '\t\tint32_t limit{0};\n'
        output_content += '\t\tif (std::regex_search(target, limit_match, limit_regex)) {\n'
        output_content += '\t\t\tlimit = std::stoi(limit_match[1].str());\n'
        output_content += '\t\t}\n\n'
        output_content += f'\t\t{msg_name}List {mas_name_snake_cased}_list;\n'
        output_content += (f'\t\tm_{package_name}_publisher_->get_{mas_name_snake_cased}('
                           f'{mas_name_snake_cased}_list, limit);\n')
        output_content += f'\t\tboost::json::object json;\n'
        output_content += f'\t\t{class_name}ObjectToJson::object_to_json({mas_name_snake_cased}_list, json);\n'
        output_content += f'\t\tres.result(boost::beast::http::status::ok);\n'
        output_content += f'\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += (f'\t\tres.set(boost::beast::http::field::content_length, std::to_string('
                           f'boost::json::serialize(json[{mas_name_snake_cased}_fld_name].get_array()).'
                           f'size()));\n')
        output_content += (f'\t\tres.body() = boost::json::serialize('
                           f'json[{mas_name_snake_cased}_fld_name].get_array());\n')
        output_content += f'\t\tres.prepare_payload();\n'
        output_content += f'\t}} else {{\n'
        output_content += f'\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
        output_content += f'\t}}\n'
        output_content += f'}}\n\n'

        return output_content

    def generate_delete_method(self, package_name: str, class_name: str, msg_name: str, mas_name_snake_cased: str,
                               msg: protogen.Message):
        output_content = ""
        output_content += (f'void {class_name}WebNWsServer::delete_{mas_name_snake_cased}_by_id(boost::beast::http::request<boost::'
                           f'beast::http::string_body>& req, boost::beast::http::response<boost::beast::'
                           f'http::string_body>& res, [[maybe_unused]] const std::smatch& match) {{\n')
        output_content += f'\tif (req.method() == boost::beast::http::verb::delete_) {{\n'
        output_content += (
            f'\t\tbool status = m_{package_name}_publisher_->delete_{mas_name_snake_cased}(stoi(match[1]));\n')
        output_content += f'\t\tboost::json::object json;\n'
        output_content += f'\t\tif (status) {{\n'
        output_content += f'\t\t\tjson["status"] = "deleted successfully";\n'
        output_content += f'\t\t\tjson["id"] = match[1].str();\n'
        output_content += f'\t\t\tres.result(boost::beast::http::status::ok);\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += (f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string('
                           f'boost::json::serialize(json).size()));\n')
        output_content += f'\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t}} else {{\n'
        output_content += f'\t\t\tjson["detail"] = "Id not Found: {msg_name} " + match[1].str();\n'
        # output_content += f'\t\t\t\tjson["id"] = match[1].str();\n'
        output_content += f'\t\t\tres.result(boost::beast::http::status::bad_request);\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += (f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string('
                           f'boost::json::serialize(json).size()));\n')
        output_content += f'\t\t\tres.body() = boost::json::serialize(json);\n'
        output_content += f'\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t}}\n'
        output_content += f'\t}} else {{\n'
        output_content += f'\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
        output_content += f'\t}}\n'
        output_content += f'}}\n\n'

        return output_content

    def generate_delete_all_method(self, package_name: str, class_name: str, msg_name: str, mas_name_snake_cased: str,
                                   msg: protogen.Message):
        output_content = ""
        output_content += (f'void {class_name}WebNWsServer::delete_all_{mas_name_snake_cased}(boost::beast::http::request<boost::beast::http'
                           f'::string_body>& req, boost::beast::http::response<boost::beast::http::'
                           f'string_body>& res, [[maybe_unused]] const std::smatch&) {{\n')
        output_content += f'\tif (req.method() == boost::beast::http::verb::delete_) {{\n'
        output_content += (f'\t\tbool status = m_{package_name}_publisher_->delete_{mas_name_snake_cased}();\n')
        output_content += f'\t\tif (status) {{\n'
        output_content += '\t\t\tstd::string response = "{\\"status\\":\\"success\\"}";\n'
        output_content += f'\t\t\tres.result(boost::beast::http::status::ok);\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(response.size()));\n'
        output_content += f'\t\t\tres.body() = response;\n'
        output_content += f'\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t}} else {{\n'
        output_content += '\t\t\tstd::string response = "{\\"status\\":\\"failed\\"}";\n'
        output_content += f'\t\t\tres.result(boost::beast::http::status::internal_server_error);\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += (f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string('
                           f'response.size()));\n')
        output_content += f'\t\t\tres.body() = response;\n'
        output_content += f'\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t}}\n'
        output_content += f'\t}} else {{\n'
        output_content += f'\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
        output_content += f'\t}}\n'
        output_content += f'}}\n\n'

        return output_content

    @staticmethod
    def generate_header_swagger_method():
        output: str = ""
        output += ("\tvoid serve_swagger_ui(boost::beast::http::request<boost::beast::http::string_body>& req, "
                   "boost::beast::http::response<boost::beast::http::string_body>& res, "
                   "[[maybe_unused]] const std::smatch& match);\n")
        output += ("\tvoid serve_swagger_json(boost::beast::http::request<boost::beast::http::string_body>& req, "
                   "boost::beast::http::response<boost::beast::http::string_body>& res, "
                   "[[maybe_unused]] const std::smatch& match);\n")
        return output

    @staticmethod
    def generate_header_connection_methods():
        output: str = ""
        output += "\tvoid reset_timer();\n"
        output += "\tbool start_connection();\n"
        output += "\tvoid do_accept();\n"
        output += ("\tvoid handle_request(boost::beast::http::request<boost::beast::http::string_body>& req, "
                   "boost::beast::http::response<boost::beast::http::string_body>& res) const;\n")
        return output

    @staticmethod
    def generate_header_create_method(msg_name_snake_cased: str):
        return (f"\tvoid create_{msg_name_snake_cased}(boost::beast::http::request<boost::beast::http::string_body>& req, "
                "boost::beast::http::response<boost::beast::http::string_body>& res, "
                "[[maybe_unused]] const std::smatch&);\n")

    @staticmethod
    def generate_header_put_method(msg_name_snake_cased: str):
        return (f"\tvoid put_{msg_name_snake_cased}(boost::beast::http::request<boost::beast::http::string_body>& req, "
                "boost::beast::http::response<boost::beast::http::string_body>& res, "
                "[[maybe_unused]] const std::smatch&);\n")

    @staticmethod
    def generate_header_patch_method(msg_name_snake_cased: str):
        return (f"\tvoid patch_{msg_name_snake_cased}(boost::beast::http::request<boost::beast::http::string_body>& req, "
                "boost::beast::http::response<boost::beast::http::string_body>& res, "
                "[[maybe_unused]] const std::smatch&);\n")

    @staticmethod
    def generate_header_get_method(msg_name_snake_cased: str):
        output: str = ""
        output +=  (f"\tvoid get_{msg_name_snake_cased}_by_id(boost::beast::http::request<boost::beast::http::string_body>& req, "
                    "boost::beast::http::response<boost::beast::http::string_body>& res, "
                    "[[maybe_unused]] const std::smatch&);\n")
        output += (f"\tvoid get_all_{msg_name_snake_cased}(boost::beast::http::request<boost::beast::http::string_body>& req, "
                   "boost::beast::http::response<boost::beast::http::string_body>& res, "
                   "[[maybe_unused]] const std::smatch&);\n")
        return output

    @staticmethod
    def generate_header_delete_method(msg_name_snake_cased: str):
        return (f"\tvoid delete_{msg_name_snake_cased}_by_id(boost::beast::http::request<boost::beast::http::string_body>& req, "
                "boost::beast::http::response<boost::beast::http::string_body>& res, "
                "[[maybe_unused]] const std::smatch&);\n")

    @staticmethod
    def generate_header_delete_all_method(msg_name_snake_cased: str):
        return (f"\tvoid delete_all_{msg_name_snake_cased}(boost::beast::http::request<boost::beast::http::string_body>& req, "
                "boost::beast::http::response<boost::beast::http::string_body>& res, "
                "[[maybe_unused]] const std::smatch&);\n")


    def output_cpp_file_generate_handler(self, file: protogen.File):

        file_name: str = str(file.proto.name).split(".")[0]
        package_name: str = str(file.proto.package)
        package_name_camel_case = convert_to_capitalized_camel_case(package_name)
        class_name_list: List[str] = package_name.split('_')
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)


        output_content: str = ""
        output_content += f'#include "../../cpp_app/replay/{class_name_snake_cased}_publisher.h"\n'
        output_content += f'#include "{class_name_snake_cased}_web_n_ws_server.h"\n\n'

        output_content += f'void {class_name}WebNWsServer::RouteConnections::publish(const std::string& message) {{\n'
        output_content += "\tstd::lock_guard<std::mutex> lock(mutex);\n"
        output_content += "\tboost::system::error_code error_code;\n"
        output_content += "\tfor (auto it = connections.begin(); it != connections.end();) {\n"
        output_content += "\t\tauto& ws_ptr = *it;\n"
        output_content += "\t\tws_ptr->write(asio::buffer(message), error_code);\n"
        output_content += "\t\tif (error_code) {\n"
        output_content += ('\t\t\tLOG_ERROR_IMPL(GetCppAppLogger(), "CombinedServer: Error writing data to client. '
                           'Error: {};;; Data: {}", error_code.message(), message);\n')
        output_content += f'\t\t\tit = connections.erase(it);\n'
        output_content += f'\t\t}} else {{\n'
        output_content += f'\t\t\t++it;\n'
        output_content += f'\t\t}}\n'
        output_content += f'\t}}\n'
        output_content += f'}}\n\n'

        output_content += (f'{class_name}WebNWsServer::{class_name}WebNWsServer(Config& config, {class_name}PublisherInterface* '
                           f'{class_name_snake_cased}_publisher) : m_config_(config), '
                           f'm_{class_name_snake_cased}_publisher_({class_name_snake_cased}_publisher), m_timer_(m_ioc_), '
                           f'm_ws_timer_(m_ioc_)')

        for msg in self.root_message_list:
            msg_name = msg.proto.name
            mas_name_snake_cased: str = convert_camel_case_to_specific_case(msg_name)
            if self.is_option_enabled(msg, self.flux_msg_cpp_json_root):
                if self.is_option_enabled(msg, CppWebServers.flux_msg_json_root_time_series):
                    output_content += (f", {mas_name_snake_cased}_db_id_("
                                       f"m_{class_name_snake_cased}_publisher_->"
                                       f"get_{mas_name_snake_cased}_next_inserted_id())")

        output_content += '{\n\n'
        output_content += '\tif (start_connection()) {\n'
        output_content += (f'\t\tm_{class_name_snake_cased}_thread_ = std::jthread(&{class_name}WebNWsServer::run, '
                           f'this);\n')
        output_content += '\t}\n'
        output_content += '}\n\n'

        output_content += f'void {class_name}WebNWsServer::run() {{\n'
        output_content += f'\treset_timer();\n'
        output_content += f'\tdo_accept();\n'
        output_content += f'\tm_ioc_.run();\n'
        output_content += f'}}\n\n'

        output_content += f'void {class_name}WebNWsServer::cleanup() {{\n'
        output_content += f'\tm_ioc_.stop();\n'
        output_content += f'}}\n\n'

        output_content += (f'void {class_name}WebNWsServer::register_route_handler('
                           f'std::shared_ptr<WebSocketRouteHandler> handler) {{\n')
        output_content += "\tauto route_path = handler->get_route_path();\n"
        output_content += "\tm_ws_routes_[route_path] = std::make_shared<RouteConnections>();\n"
        output_content += "\tm_ws_routes_[route_path]->handler = handler;\n"
        output_content += "}\n\n"

        output_content += (f'bool {class_name}WebNWsServer::publish_to_route(const std::string& route, '
                           f'const std::string& message) {{\n')
        output_content += '\tauto route_it = m_ws_routes_.find(route);\n'
        output_content += '\tif (route_it == m_ws_routes_.end()) {\n'
        output_content += '\t\tLOG_ERROR_IMPL(GetCppAppLogger(), "CombinedServer: Invalid route: {}", route);\n'
        output_content += '\t\treturn false;\n'
        output_content += '\t}\n'
        output_content += '\troute_it->second->publish(message);\n'
        output_content += '\treturn true;\n'
        output_content += '}\n\n'

        output_content += f'[[nodiscard]] bool {class_name}WebNWsServer::has_ws_clients_connected() const {{\n'
        output_content += f'\tfor (const auto& [route, connections] : m_ws_routes_) {{\n'
        output_content += f'\t\tif (!connections->connections.empty()) {{\n'
        output_content += f'\t\t\treturn true;\n'
        output_content += f'\t\t}}\n'
        output_content += f'\t}}\n'
        output_content += f'\treturn false;\n'
        output_content += f'}}\n\n'

        output_content += (f'void {class_name}WebNWsServer::serve_swagger_ui([[maybe_unused]] boost::beast::http::request<boost::beast::http::'
                           'string_body>& req, boost::beast::http::response<boost::beast::http::string_body>& res, '
                           '[[maybe_unused]] const std::smatch& match) {\n')
        output_content += '\tres.result(boost::beast::http::status::ok);\n'
        output_content += '\tres.set(boost::beast::http::field::content_type, "text/html");\n'
        output_content += '\tres.body() = R"(\n'
        output_content += '\t\t<!DOCTYPE html>\n'
        output_content += '\t\t<html>\n'
        output_content += '\t\t<head>\n'
        output_content += '\t\t\t<title>Swagger UI</title>\n'
        output_content += ('\t\t\t<link rel="stylesheet" type="text/css" href='
                           '"https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.15.5/swagger-ui.css">\n')
        output_content += '\t\t</head>\n'
        output_content += '\t\t<body>\n'
        output_content += '\t\t\t<div id="swagger-ui"></div>\n'
        output_content += ('\t\t\t<script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.15.5/'
                           'swagger-ui-bundle.js"></script>\n')
        output_content += '\t\t\t<script>\n'
        output_content += "\t\t\t\tSwaggerUIBundle({url: '/swagger.json', dom_id: '#swagger-ui',});\n"
        output_content += "\t\t\t</script>\n"
        output_content += "\t\t</body>\n"
        output_content += "\t\t</html>\n"
        output_content += '\t)";\n'
        output_content += '\tres.prepare_payload();\n'
        output_content += '}\n\n'

        output_content += (f'void {class_name}WebNWsServer::serve_swagger_json([[maybe_unused]] boost::beast::http::request<boost::beast::http::'
                           'string_body>& req, boost::beast::http::response<boost::beast::http::string_body>& res, '
                           '[[maybe_unused]] const std::smatch& match) {\n')
        output_content += ('\tstd::ifstream swagger_file(m_config_.m_swagger_ui_json_path_);\n')
        output_content += f'\tif (!swagger_file.is_open()) {{\n'
        output_content += '\t\tres.result(boost::beast::http::status::internal_server_error);\n'
        output_content += '\t\tres.body() = "Failed to open swagger.json";\n'
        output_content += '\t\tres.prepare_payload();\n'
        output_content += '\t\treturn;\n'
        output_content += '\t}\n\n'
        output_content += ('\tstd::string swagger_content((std::istreambuf_iterator<char>(swagger_file)), '
                           'std::istreambuf_iterator<char>());\n')
        output_content += '\tres.result(boost::beast::http::status::ok);\n'
        output_content += '\tres.body() = swagger_content;\n'
        output_content += '\tres.prepare_payload();\n'
        output_content += '}\n\n'

        output_content += f'void {class_name}WebNWsServer::reset_timer() {{\n'
        output_content += f'\tm_timer_.expires_after(std::chrono::seconds(market_data_handler::connection_timeout));\n'
        output_content += f'\tm_timer_.async_wait([this](const boost::system::error_code& ec) {{\n'
        output_content += f'\t\tif (!ec) {{\n'
        output_content += f'\t\t\tm_shutdown_ = true;\n'
        output_content += f'\t\t\tm_acceptor_->close();\n'
        output_content += f'\t\t}}\n'
        output_content += f'\t}});\n'
        output_content += f'}}\n\n'

        output_content += f'bool {class_name}WebNWsServer::start_connection() {{\n'
        output_content += '\ttry {\n'
        output_content += ('\t\tm_acceptor_ = std::make_unique<boost::asio::ip::tcp::acceptor>(m_ioc_, '
                           'boost::asio::ip::tcp::endpoint{boost::asio::ip::make_address(m_config_.m_http_host_), '
                           'static_cast<boost::asio::ip::port_type>(m_config_.m_http_server_port_)});\n')
        output_content += '\t\treturn true;\n'
        output_content += '\t} catch (const boost::system::system_error& error) {\n'
        output_content += '\t\tstd::string err_msg = error.what();\n'
        output_content += '\t\tif (error.code().value() == 98 || err_msg.contains("bind: Address already in use")) {\n'
        output_content += '\t\t\t--m_server_retry_count_;\n'
        output_content += '\t\t\tif (m_server_retry_count_ > 0) {\n'
        output_content += '\t\t\t\tusleep(0.5);\n'
        output_content += '\t\t\t\treturn start_connection();\n'
        output_content += '\t\t\t} else {\n'
        output_content += ('\t\t\t\tLOG_ERROR_IMPL(GetCppAppLogger(), "WebSocketServer: Failed to start server on '
                           'Host: {}, Port: {}. Error: {}. Retrying...", m_config_.m_http_host_, '
                           'm_config_.m_http_server_port_, error.what());\n')
        output_content += '\t\t\t\treturn false;\n'
        output_content += '\t\t\t}\n'
        output_content += '\t\t} else {\n'
        output_content += ('\t\t\tLOG_ERROR_IMPL(GetCppAppLogger(), "WebSocketServer: Failed to start server on '
                           'Host: {}, Port: {}. Error: {}. Retrying...", m_config_.m_http_host_, '
                           'm_config_.m_http_server_port_, error.what());\n')
        output_content += f'\t\t\treturn false;\n'
        output_content += f'\t\t}}\n'
        output_content += f'\t}}\n'
        output_content += f'}}\n'

        output_content += f'void {class_name}WebNWsServer::do_accept() {{\n'
        output_content += f'\tif (m_shutdown_) {{\n'
        output_content += f'\t\treturn;\n'
        output_content += f'\t}}\n'
        output_content += f'\tm_acceptor_->async_accept([this](boost::system::error_code ec, tcp::socket socket) {{\n'
        output_content += f'\t\tif (!ec) {{\n'
        output_content += f'\t\t\treset_timer();\n'
        output_content += f'\t\t\tbeast::flat_buffer buffer;\n'
        output_content += f'\t\t\thttp::request<http::string_body> req;\n'
        output_content += f'\t\t\thttp::read(socket, buffer, req);\n'
        output_content += f'\t\t\tif (websocket::is_upgrade(req)) {{\n'
        output_content += f'\t\t\t\tstd::string path = std::string(req.target());\n'
        output_content += f'\t\t\t\tauto route_it = m_ws_routes_.find(path);\n'
        output_content += f'\t\t\t\tif (route_it != m_ws_routes_.end()) {{\n'
        output_content += (f'\t\t\t\t\tauto ws_ptr = std::make_shared<websocket::stream<tcp::socket>>(std::move('
                           f'socket));\n')
        output_content += f'\t\t\t\t\ttry {{\n'
        output_content += (f'\t\t\t\t\t\tws_ptr->set_option(websocket::stream_base::timeout::suggested('
                           f'beast::role_type::server));\n')
        output_content += f'\t\t\t\t\t\tauto read_buffer = std::make_shared<beast::flat_buffer>();\n'
        output_content += f'\t\t\t\t\t\tws_ptr->accept(req);\n\n'
        output_content += (f'\t\t\t\t\t\tws_ptr->async_read(*read_buffer, [this, ws_ptr, read_buffer, path]('
                           f'boost::system::error_code read_ec, std::size_t) {{\n')
        output_content += f'\t\t\t\t\t\t\tif (read_ec == websocket::error::closed) {{\n'
        output_content += f'\t\t\t\t\t\t\t\tauto route_it = m_ws_routes_.find(path);\n'
        output_content += f'\t\t\t\t\t\t\t\tif (route_it != m_ws_routes_.end()) {{\n'
        output_content += f'\t\t\t\t\t\t\t\t\tstd::lock_guard<std::mutex> lock(route_it->second->mutex);\n'
        output_content += f'\t\t\t\t\t\t\t\t\tauto& connections = route_it->second->connections;\n'
        output_content += (f'\t\t\t\t\t\t\t\t\tconnections.erase(std::remove(connections.begin(), connections.end(), '
                           f'ws_ptr), connections.end());\n')
        output_content += f'\t\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t\tboost::system::error_code close_ec;\n'
        output_content += f'\t\t\t\t\t\t\t\tws_ptr->next_layer().shutdown(tcp::socket::shutdown_both, close_ec);\n'
        output_content += f'\t\t\t\t\t\t\t\tws_ptr->next_layer().close(close_ec);\n'
        output_content += f'\t\t\t\t\t\t\t\treturn;\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}});\n'
        output_content += f'\t\t\t\t\t\t{{\n'
        output_content += f'\t\t\t\t\t\tstd::lock_guard<std::mutex> lock(route_it->second->mutex);\n'
        output_content += f'\t\t\t\t\t\t\troute_it->second->connections.push_back(ws_ptr);\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\tif (route_it->second->handler) {{\n'
        output_content += f'\t\t\t\t\t\t\troute_it->second->handler->handle_new_connection(ws_ptr);\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}} catch (std::exception const& error) {{\n'
        output_content += (f'\t\t\t\t\t\tLOG_ERROR_IMPL(GetCppAppLogger(), "Error while accepting client: {{}}", '
                           f'error.what());\n')
        output_content += f'\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t}} else {{\n'
        output_content += f'\t\t\t\t\tLOG_ERROR_IMPL(GetCppAppLogger(), "CombinedServer: Unsupported route: {{}}", path);\n'
        output_content += f'\t\t\t\t}}\n'
        output_content += f'\t\t\t}} else {{\n'
        output_content += f'\t\t\t\thttp::response<http::string_body> res;\n'
        output_content += f'\t\t\t\thandle_request(req, res);\n'
        output_content += f'\t\t\t\thttp::write(socket, res);\n'
        output_content += f'\t\t\t}}\n'
        output_content += f'\t\t}}\n'
        output_content += f'\t\tdo_accept();\n'
        output_content += f'\t}});\n'
        output_content += f'}}\n\n'

        output_content += (f'void {class_name}WebNWsServer::handle_request(boost::beast::http::request<'
                           f'boost::beast::http::string_body>& req, boost::beast::http::response<boost::beast::'
                           f'http::string_body>& res) const {{\n')
        output_content += f'\tif (req.method() == http::verb::options) {{\n'
        output_content += f'\t\tres.result(http::status::ok);\n'
        output_content += f'\t\tres.set(http::field::access_control_allow_origin, "*");\n'
        output_content += f'\t\tres.set(http::field::access_control_allow_headers, "*");\n'
        output_content += f'\t\tres.set(http::field::access_control_allow_methods, "*");\n'
        output_content += f'\t\tres.set(http::field::access_control_allow_credentials, "*");\n'
        output_content += f'\t\tres.prepare_payload();\n'
        output_content += f'\t\treturn;\n'
        output_content += f'\t}}\n'
        output_content += ('\tLOG_INFO_IMPL(GetCppAppLogger(), "Handling request: Method = {}, Target = {}, data= '
                           '{}",std::string(req.method_string()), std::string(req.target()), '
                           'std::string(req.body()));\n\n')
        output_content += (f'\tconst auto route = std::find_if(m_routes_.begin(), m_routes_.end(), '
                           f'[&req](const Route& route) {{\n')
        output_content += (f'\t\treturn std::find(route.methods.begin(), route.methods.end(), req.method()) != '
                           f'route.methods.end() && std::regex_match(std::string(req.target()), route.path_pattern);\n')
        output_content += f'\t\t}});\n'
        output_content += f'\tif (route != m_routes_.end()) {{\n'
        output_content += f'\t\tstd::smatch match;\n'
        output_content += f'\t\tstd::string target_str = std::string(req.target());\n'
        output_content += f'\t\tif (std::regex_search(target_str, match, route->path_pattern)) {{\n'
        output_content += f'\t\t\troute->handler(req, res, match);\n'
        output_content += f'\t\t}} else {{\n'
        output_content += f'\t\t\tres = http::response<http::string_body>{{http::status::bad_request, req.version()}};\n'
        output_content += f'\t\t\tres.set(http::field::content_type, "text/plain");\n'
        output_content += f'\t\t\tres.body() = "Request path does not match expected format";\n'
        output_content += f'\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t}}\n'
        output_content += f'\t}} else {{\n'
        output_content += f'\t\tstd::string ec = "Route not found";\n'
        output_content += f'\t\tres.result(boost::beast::http::status::not_found);\n'
        output_content += f'\t\tres.set(http::field::content_type, "application/json");\n'
        output_content += f'\t\tres.set(boost::beast::http::field::content_length, std::to_string(ec.size()));\n'
        output_content += f'\t\tres.body() = ec;\n'
        output_content += f'\t\tres.prepare_payload();\n'
        output_content += f'\t}}\n\n'
        output_content += f'\tres.set(http::field::access_control_allow_origin, "*");\n'
        output_content += f'\tres.set(http::field::access_control_allow_headers, "*");\n'
        output_content += f'\tres.set(http::field::access_control_allow_methods, "*");\n'
        output_content += f'\tres.set(http::field::access_control_allow_credentials, "*");\n'
        output_content += f'}}\n\n'

        for msg in self.root_message_list:
            cpp_server_operations = self.get_complex_option_value_from_proto(msg, self.flux_msg_cpp_json_root, False)
            msg_name = msg.proto.name
            mas_name_snake_cased: str = convert_camel_case_to_specific_case(msg_name)
            # print(f'=================================== {self.is_bool_option_enabled(msg, self.flux_msg_is_cpp_web_server_model)} ------------------------------ {msg.proto.name}')
            if self.is_option_enabled(msg, self.flux_msg_cpp_json_root):
                for key, val in cpp_server_operations.items():
                    if key == self.flux_json_root_create_field:
                        output_content += self.generate_time_series_create(package_name, class_name, msg_name,
                                                                           mas_name_snake_cased, msg) if (
                            self.is_option_enabled(msg, self.flux_msg_json_root_time_series)) else (
                            self.generate_create_method(package_name, class_name, msg_name, mas_name_snake_cased, msg))
                    elif key == self.flux_json_root_update_field:
                        output_content += self.generate_put_method(package_name, class_name, msg_name,
                                                                   mas_name_snake_cased, msg)
                    elif key == self.flux_json_root_patch_field:
                        output_content += self.generate_patch_method(package_name, class_name, msg_name,
                                                                     mas_name_snake_cased, msg)
                    elif key == self.flux_json_root_read_field:
                        output_content += self.generate_get_method(package_name, class_name, msg_name,
                                                                   mas_name_snake_cased, msg)
                        output_content += self.generate_get_all_method(
                            package_name, class_name, msg_name, mas_name_snake_cased, msg
                        )
                    elif key == self.flux_json_root_delete_field:
                        output_content += self.generate_delete_method(package_name, class_name, msg_name,
                                                                      mas_name_snake_cased, msg)
                    elif key == self.flux_json_root_delete_all_field:
                        output_content += self.generate_delete_all_method(package_name, class_name, msg_name,
                                                                          mas_name_snake_cased, msg)

        return output_content



    def output_file_generate_handler(self, file: protogen.File):

        file_name: str = str(file.proto.name).split(".")[0]
        package_name: str = str(file.proto.package)
        package_name_camel_case = convert_to_capitalized_camel_case(package_name)
        class_name_list: List[str] = package_name.split('_')
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        for msg in file.messages:
            if (self.is_option_enabled(msg, CppWebServers.flux_msg_json_root) or
                    self.is_option_enabled(msg, CppWebServers.flux_msg_json_root_time_series)):
                self.root_message_list.append(msg)
                self.root_message_name_list.append(msg.proto.name)

        flux_import_models: list = self.get_complex_option_value_from_proto(file, self.flux_file_import_dependency_model, True)
        # print(flux_import_models[0])

        msg_name_list: list = []
        import_file_name_list: List[str] = []
        for i in flux_import_models:
            import_file_name_list.append(i.get("ImportFileName"))
            for msg in i.get("ImportModelName"):
                self.root_message_name_list.append(msg)

        for dependency_file in file.dependencies:
            dependency_name = dependency_file.proto.name
            if dependency_name in import_file_name_list:
                for msg in dependency_file.messages:
                    if msg.proto.name in self.root_message_name_list:
                        if (self.is_option_enabled(msg, CppWebServers.flux_msg_json_root) or
                                self.is_option_enabled(msg, CppWebServers.flux_msg_json_root_time_series)):
                            self.root_message_list.append(msg)

        output_content: str = "#pragma once"
        output_content += "\n\n"
        output_content += '#include "boost/beast/http.hpp"\n\n'
        output_content += '#include "boost/asio.hpp"\n'
        output_content += '#include "boost/beast/websocket.hpp"\n'
        output_content += f'#include "{file_name}.h"\n'
        output_content += f'#include "{class_name_snake_cased}_json_to_object.h"\n'
        output_content += f'#include "mongo_db_codec.h"\n'
        output_content += f'#include "web_socket_route_handler.h"\n'
        output_content += f'#include "../../cpp_app/include/config_parser.h"\n'
        output_content += '#include "../../../../../../FluxCppCore/include/web_server_route.h"\n\n'

        output_content += f'using namespace FluxCppCore;\n\n'
        output_content += f'class {class_name}Publisher;\n\n'

        output_content += f'class {class_name}WebNWsServer {{\n\n'

        output_content += "public:\n\n"
        output_content += "\tstruct RouteConnections {\n"
        output_content += "\t\tstd::mutex mutex;\n"
        output_content += "\t\tstd::vector<std::shared_ptr<websocket::stream<tcp::socket>>> connections;\n"
        output_content += "\t\tstd::shared_ptr<WebSocketRouteHandler> handler;\n"
        output_content += "\t\tvoid publish(const std::string& message);\n"
        output_content += "\t};\n\n"

        output_content += (f"\texplicit {class_name}WebNWsServer(Config& config, "
                           f"{class_name}PublisherInterface* {class_name_snake_cased}_publisher);\n")
        output_content += "\tvoid run();\n"
        output_content += "\tvoid cleanup();\n"
        output_content += "\tvoid register_route_handler(std::shared_ptr<WebSocketRouteHandler> handler);\n"
        output_content += "\tbool publish_to_route(const std::string& route, const std::string& message);\n"
        output_content += "\t[[nodiscard]] bool has_ws_clients_connected() const;\n"
        output_content += "\tvoid shutdown();\n\n"

        output_content += f'protected:\n'
        output_content += f'\tConfig& m_config_;\n'
        output_content += f'\t{class_name}PublisherInterface* m_{class_name_snake_cased}_publisher_;\n'
        output_content += f'\tboost::asio::io_context m_ioc_;\n'
        output_content += f'\tstd::unique_ptr<boost::asio::ip::tcp::acceptor> m_acceptor_;\n'
        output_content += f'\tstd::atomic<bool> m_shutdown_{{false}};\n'
        output_content += f'\tboost::asio::steady_timer m_timer_;\n'
        output_content += f'\tboost::asio::deadline_timer m_ws_timer_;\n'
        output_content += f'\tstd::jthread m_{package_name}_thread_;\n'
        output_content += f'\tint8_t m_server_retry_count_{{3}};\n'
        output_content += f'\tstd::unordered_map<std::string, std::shared_ptr<RouteConnections>> m_ws_routes_;\n'
        # output_content += f'\tstd::shared_ptr<MongoDBHandler> m_mongo_db_handler_;\n'

        output_content += "\tstd::vector<Route> m_routes_{\n"
        output_content += ('\t\tRoute{"/docs", std::regex(R"(^/docs$)"), {boost::beast::http::verb::get}, '
                           '[this](auto& req, auto& res, auto& match) { serve_swagger_ui(req, res, match); }},\n')
        output_content += ('\t\tRoute{"/swagger.json", std::regex(R"(^/swagger\\.json$)"), {boost::beast::http::verb::get}, '
                           '[this](auto& req, auto& res, auto& match) { serve_swagger_json(req, res, match); }},\n')

        for msg in self.root_message_list:
            if self.is_option_enabled(msg, self.flux_msg_cpp_json_root):
                cpp_server_operations = self.get_complex_option_value_from_proto(msg, self.flux_msg_cpp_json_root, False)
                msg_name = msg.proto.name
                mas_name_snake_cased: str = convert_camel_case_to_specific_case(msg_name)
                for key, val in cpp_server_operations.items():
                    if key == self.flux_json_root_create_field:
                        output_content += self.generate_create_route(mas_name_snake_cased)
                    elif key == self.flux_json_root_update_field:
                        output_content += self.generate_put_route(mas_name_snake_cased)
                    elif key == self.flux_json_root_patch_field:
                        output_content += self.generate_patch_route(mas_name_snake_cased)
                    elif key == self.flux_json_root_read_field:
                        output_content += self.generate_get_route(mas_name_snake_cased)
                        output_content += self.generate_get_all_route(mas_name_snake_cased)
                    elif key == self.flux_json_root_delete_field:
                        output_content += self.generate_delete_route(mas_name_snake_cased)
                    elif key == self.flux_json_root_delete_all_field:
                        output_content += self.generate_delete_all_route(mas_name_snake_cased)
        output_content += '\t};\n\n'

        for msg in self.root_message_list:
            msg_name = msg.proto.name
            mas_name_snake_cased: str = convert_camel_case_to_specific_case(msg_name)
            if self.is_option_enabled(msg, self.flux_msg_cpp_json_root):
                if self.is_option_enabled(msg, CppWebServers.flux_msg_json_root_time_series):
                    output_content += f"\tint32_t {mas_name_snake_cased}_db_id_;\n\n"

        output_content += self.generate_header_swagger_method()
        output_content += self.generate_header_connection_methods()

        for msg in self.root_message_list:
            cpp_server_operations = self.get_complex_option_value_from_proto(msg, self.flux_msg_cpp_json_root, False)
            msg_name = msg.proto.name
            mas_name_snake_cased: str = convert_camel_case_to_specific_case(msg_name)
            # print(f'=================================== {self.is_bool_option_enabled(msg, self.flux_msg_is_cpp_web_server_model)} ------------------------------ {msg.proto.name}')
            if self.is_option_enabled(msg, self.flux_msg_cpp_json_root):
                for key, val in cpp_server_operations.items():
                    if key == self.flux_json_root_create_field:
                        output_content += self.generate_header_create_method(mas_name_snake_cased)
                    elif key == self.flux_json_root_update_field:
                        output_content += self.generate_header_put_method(mas_name_snake_cased)
                    elif key == self.flux_json_root_patch_field:
                        output_content += self.generate_header_patch_method(mas_name_snake_cased)
                    elif key == self.flux_json_root_read_field:
                        output_content += self.generate_header_get_method(mas_name_snake_cased)
                    elif key == self.flux_json_root_delete_field:
                        output_content += self.generate_header_delete_method(mas_name_snake_cased)
                    elif key == self.flux_json_root_delete_all_field:
                        output_content += self.generate_header_delete_all_method(mas_name_snake_cased)

        output_content += "};\n\n"

        output_file_name = f"{class_name_snake_cased}_web_n_ws_server.h"
        cpp_output_file_name = f"{class_name_snake_cased}_web_n_ws_server.cpp"
        cpp_output_file_content = self.output_cpp_file_generate_handler(file)

        return {output_file_name: output_content, cpp_output_file_name : cpp_output_file_content}


if __name__ == "__main__":
    main(CppWebServers)
