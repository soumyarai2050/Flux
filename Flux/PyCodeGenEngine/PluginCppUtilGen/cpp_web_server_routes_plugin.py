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
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, YAMLConfigurationManager
from Flux.CodeGenProjects.TradeEngine.ProjectGroupPlugins.PluginStratExecutor.strat_executor_plugin import \
    StratExecutorPlugin

root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
root_flux_core_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(
    str(root_flux_core_config_yaml_path))


class CppWebServerRoutesPlugin(BaseProtoPlugin):
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


    def output_file_generate_handler(self, file: protogen.File):

        file_name: str = str(file.proto.name).split(".")[0]
        package_name: str = str(file.proto.package)
        class_name_list: List[str] = package_name.split('_')
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        for msg in file.messages:
            if (self.is_option_enabled(msg, CppWebServerRoutesPlugin.flux_msg_json_root) or
                self.is_option_enabled(msg, CppWebServerRoutesPlugin.flux_msg_json_root_time_series)):
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
                        if (self.is_option_enabled(msg, CppWebServerRoutesPlugin.flux_msg_json_root) or
                            self.is_option_enabled(msg, CppWebServerRoutesPlugin.flux_msg_json_root_time_series)):
                            self.root_message_list.append(msg)

        output_content: str = "#pragma once"
        output_content += "\n\n"
        output_content += '#include "boost/beast/http.hpp"\n\n'
        output_content += f'#include "{file_name}.h"\n'
        output_content += f'#include "{class_name_snake_cased}_json_to_object.h"\n'
        output_content += f'#include "mongo_db_codec.h"\n'
        output_content += '#include "../../../../../../FluxCppCore/include/web_server_route.h"\n\n'

        output_content += f'using namespace FluxCppCore;\n\n'

        output_content += f'class {class_name}WebServer {{\n\n'
        output_content += f'protected:\n'
        output_content += f'\tConfig m_config_;\n'
        output_content += f'\tboost::asio::io_context m_ioc_;\n'
        output_content += f'\tboost::asio::ip::tcp::acceptor m_acceptor_;\n'
        output_content += f'\tstd::atomic<bool> m_shutdown_{{false}};\n'
        output_content += f'\tboost::asio::steady_timer m_timer_;\n'
        output_content += f'\tstd::shared_ptr<MongoDBHandler> m_mongo_db_handler_;\n'
        output_content += f'\tMarketDataConsumer& m_market_data_consumer_;\n\n'

        output_content += "\tstd::vector<Route> m_routes_{\n"

        msg_name_list: List[str] = ["MarketDepth", "LastTrade"]
        for msg in self.root_message_list:
            msg_name = msg.proto.name
            mas_name_snake_cased: str = convert_camel_case_to_specific_case(msg_name)
            generate_or_not: bool = False
            for fld in msg.fields:
                if CppWebServerRoutesPlugin.is_option_enabled(fld, CppWebServerRoutesPlugin.flux_fld_PK):
                    generate_or_not = True
                    break
            if generate_or_not:
                output_content += (f'\t\tRoute{{"create-{mas_name_snake_cased}", std::regex(R"(^/create-{mas_name_snake_cased}$)"), '
                                   f'{{boost::beast::http::verb::post}}, [this](auto& req, auto& res, auto& match) '
                                   f'{{ create_{mas_name_snake_cased}(req, res, match); }}}},\n')
                output_content += (f'\t\tRoute{{"put-{mas_name_snake_cased}", std::regex(R"(^/put-{mas_name_snake_cased}$)"), {{'
                                   f'boost::beast::http::verb::put}}, [this](auto& req, auto& res, auto& match) {{ '
                                   f'put_{mas_name_snake_cased}(req, res, match); }}}},\n')
                output_content += (f'\t\tRoute{{"patch-{mas_name_snake_cased}", std::regex(R"(^/patch-{mas_name_snake_cased}$)"), {{'
                                   f'boost::beast::http::verb::patch}}, [this](auto& req, auto& res, auto& match) {{ '
                                   f'patch_{mas_name_snake_cased}(req, res, match); }}}},\n')
                output_content += (f'\t\tRoute{{"get_all-{mas_name_snake_cased}", std::regex(R"(^/get_all-{mas_name_snake_cased}$)"), {{'
                                   f'boost::beast::http::verb::get}}, [this](auto& req, auto& res, auto& match) {{ '
                                   f'get_all_{mas_name_snake_cased}(req, res, match); }}}},\n')
                output_content  += (f'\t\tRoute{{"get-{mas_name_snake_cased}/{{{mas_name_snake_cased}_id}}", std::regex('
                                    f'R"(^/get-{mas_name_snake_cased}/(\\d+)$)"), {{boost::beast::http::verb::get}}, [this]('
                                    f'auto& req, auto& res, auto& match) {{ get_{mas_name_snake_cased}_by_id(req, res, '
                                    f'match); }}}},\n')
        output_content += '\t};\n\n'

        for msg in self.root_message_list:
            msg_name = msg.proto.name
            mas_name_snake_cased: str = convert_camel_case_to_specific_case(msg_name)
            generate_or_not: bool = False
            for fld in msg.fields:
                if CppWebServerRoutesPlugin.is_option_enabled(fld, CppWebServerRoutesPlugin.flux_fld_PK):
                    generate_or_not = True
                    break
            if generate_or_not:
                output_content += (f'\tMongoDBCodec<{msg_name}, {msg_name}List> m_{mas_name_snake_cased}_mongo_db_codec'
                                   f'{{m_mongo_db_handler_}};\n')

        output_content += f'public:\n\n'
        output_content += (f'\texplicit {class_name}WebServer(Config& config, std::shared_ptr<MongoDBHandler> mongo_db_handler, '
                           f'MarketDataConsumer& market_data_consumer) : '
                           f'm_config_(config), m_acceptor_(m_ioc_, {{boost::asio::ip::make_address('
                           f'm_config_.m_http_host_), static_cast<boost::asio::ip::port_type>('
                           f'm_config_.m_http_server_port_)}}), m_timer_(m_ioc_), m_mongo_db_handler_(mongo_db_handler), '
                           f'm_market_data_consumer_(market_data_consumer) {{}}\n\n')

        output_content += f'\tvoid run() {{\n'
        output_content += f'\t\treset_timer();\n'
        output_content += f'\t\tdo_accept();\n'
        output_content += f'\t\tm_ioc_.run();\n'
        output_content += f'\t}}\n\n'

        output_content += f'\tvoid cleanup() {{\n'
        output_content += f'\t\tm_ioc_.stop();\n'
        output_content += f'\t}}\n\n'

        output_content += 'protected:\n\n'
        output_content += f'\tvoid reset_timer() {{\n'
        output_content += f'\t\tm_timer_.expires_after(std::chrono::seconds(market_data_handler::connection_timeout));\n'
        output_content += f'\t\tm_timer_.async_wait([this](const boost::system::error_code& ec) {{\n'
        output_content += f'\t\t\tif (!ec) {{\n'
        output_content += f'\t\t\t\tm_shutdown_ = true;\n'
        output_content += f'\t\t\t\tm_acceptor_.close();\n'
        output_content += f'\t\t\t}}\n'
        output_content += f'\t\t}});\n'
        output_content += f'\t}}\n\n'

        output_content += f'\tvoid do_accept() {{\n'
        output_content += f'\t\tif (m_shutdown_) {{\n'
        output_content += f'\t\t\treturn;\n'
        output_content += f'\t\t}}\n'
        output_content += f'\t\tm_acceptor_.async_accept([this](boost::system::error_code ec, tcp::socket socket) {{\n'
        output_content += f'\t\t\tif (!ec) {{\n'
        output_content += f'\t\t\t\treset_timer();\n'
        output_content += f'\t\t\t\tboost::beast::tcp_stream stream(std::move(socket));\n'
        output_content += f'\t\t\t\thandle_request(stream);\n'
        output_content += f'\t\t\t}}\n'
        output_content += f'\t\t\tdo_accept();\n'
        output_content += f'\t\t}});\n'
        output_content += f'\t}}\n\n'

        output_content += f'\tvoid handle_request(beast::tcp_stream& stream) const {{\n'
        output_content += f'\t\tbeast::flat_buffer buffer;\n'
        output_content += f'\t\thttp::request<http::string_body> req;\n'
        output_content += f'\t\thttp::read(stream, buffer, req);\n'
        output_content += f'\t\thttp::response<http::string_body> res;\n'
        output_content += (f'\t\tconst auto route = std::find_if(m_routes_.begin(), m_routes_.end(), '
                           f'[&req](const Route& route) {{\n')
        output_content += (f'\t\t\treturn std::find(route.methods.begin(), route.methods.end(), req.method()) != '
                           f'route.methods.end() && std::regex_match(std::string(req.target()), route.path_pattern);\n')
        output_content += f'\t\t\t}});\n'
        output_content += f'\t\tif (route != m_routes_.end()) {{\n'
        output_content += f'\t\t\tstd::smatch match;\n'
        output_content += f'\t\t\tstd::string target_str = std::string(req.target());\n'
        output_content += f'\t\t\tif (std::regex_search(target_str, match, route->path_pattern)) {{\n'
        output_content += f'\t\t\t\troute->handler(req, res, match);\n'
        output_content += f'\t\t\t}} else {{\n'
        output_content += f'\t\t\t\tres = http::response<http::string_body>{{http::status::bad_request, req.version()}};\n'
        output_content += f'\t\t\t\tres.set(http::field::content_type, "text/plain");\n'
        output_content += f'\t\t\t\tres.body() = "Request path does not match expected format";\n'
        output_content += f'\t\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t\t}}\n'
        output_content += f'\t\t}} else {{\n'
        output_content += f'\t\t\tstd::string ec = "Route not found";\n'
        output_content += f'\t\t\tres.result(boost::beast::http::status::not_found);\n'
        output_content += f'\t\t\tres.set(http::field::content_type, "application/json");\n'
        output_content += f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(ec.size()));\n'
        output_content += f'\t\t\tres.body() = ec;\n'
        output_content += f'\t\t\tres.prepare_payload();\n'
        output_content += f'\t\t}}\n'
        output_content += f'\t\thttp::write(stream, res);\n'
        output_content += f'\t\tres.clear();\n'
        output_content += f'\t}}\n\n'
        for msg in self.root_message_list:
            msg_name = msg.proto.name
            mas_name_snake_cased: str = convert_camel_case_to_specific_case(msg_name)
            generate_or_not: bool = False
            for fld in msg.fields:
                if CppWebServerRoutesPlugin.is_option_enabled(fld, CppWebServerRoutesPlugin.flux_fld_PK):
                    generate_or_not = True
                    break
            if generate_or_not:
                if msg_name in msg_name_list:
                    output_content += (f'\tvoid create_{mas_name_snake_cased}(boost::beast::http::request<boost::beast::'
                                       f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                                       f'string_body>& res, [[maybe_unused]] const std::smatch&) {{\n')
                    output_content += f'\t\tif (req.method() == boost::beast::http::verb::post) {{\n'
                    output_content += f'\t\t\t{msg_name} {mas_name_snake_cased};\n'
                    # output_content += f'\t\t\t{class_name}JsonToObject::json_to_object(req.body(), {mas_name_snake_cased});\n'
                    output_content += f'\t\t\tm_market_data_consumer_.process_{mas_name_snake_cased}(req.body());\n'
                    # output_content += f'\t\t\tauto inserted_id = m_{mas_name_snake_cased}_mongo_db_codec.insert({mas_name_snake_cased});\n'
                    # output_content += f'\t\t\tif (inserted_id == -1) {{\n'
                    # output_content += f'\t\t\t\tres.result(boost::beast::http::status::internal_server_error);\n'
                    # output_content += f'\t\t\t}}\n'
                    output_content += f'\t\t\tres.result(boost::beast::http::status::created);\n'
                    output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
                    output_content += f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(res.body().size()));\n'
                    output_content += f'\t\t\tres.body() = req.body();\n'
                    output_content += f'\t\t\tres.prepare_payload();\n'
                    output_content += f'\t\t}} else {{\n'
                    output_content += f'\t\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
                    output_content += f'\t\t}}\n'
                    output_content += f'\t}}\n\n'

                    output_content += (f'\tvoid put_{mas_name_snake_cased}(boost::beast::http::request<boost::beast::'
                                       f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                                       f'string_body>& res, [[maybe_unused]] const std::smatch& match) {{\n')
                    output_content += f'\t\tif (req.method() == boost::beast::http::verb::put) {{\n'
                    output_content += f'\t\t\t{msg_name} {mas_name_snake_cased};\n'
                    output_content += f'\t\t\tm_market_data_consumer_.process_{mas_name_snake_cased}(req.body());\n'
                    # output_content += f'\t\t\t{class_name}JsonToObject::json_to_object(req.body(), {mas_name_snake_cased});\n'
                    # output_content += f'\t\t\tauto inserted_id = m_{mas_name_snake_cased}_mongo_db_codec.patch({mas_name_snake_cased});\n'
                    # output_content += f'\t\t\tif (!inserted_id) {{\n'
                    # output_content += f'\t\t\t\tres.result(boost::beast::http::status::internal_server_error);\n'
                    # output_content += f'\t\t\t}}\n'
                    output_content += f'\t\t\tres.result(boost::beast::http::status::created);\n'
                    output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
                    output_content += f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(res.body().size()));\n'
                    output_content += f'\t\t\tres.body() = req.body();\n'
                    output_content += f'\t\t\tres.prepare_payload();\n'
                    output_content += f'\t\t}} else {{\n'
                    output_content += f'\t\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
                    output_content += f'\t\t}}\n'
                    output_content += f'\t}}\n\n'

                    output_content += (f'\tvoid patch_{mas_name_snake_cased}(boost::beast::http::request<boost::beast::'
                                       f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                                       f'string_body>& res, [[maybe_unused]] const std::smatch& match) {{\n')
                    output_content += f'\tif (req.method() == boost::beast::http::verb::patch) {{\n'
                    output_content += f'\t\t\t{msg_name} {mas_name_snake_cased};\n'
                    output_content += f'\t\t\tm_market_data_consumer_.process_{mas_name_snake_cased}(req.body());\n'
                    # output_content += f'\t\t\t{class_name}JsonToObject::json_to_object(req.body(), {mas_name_snake_cased});\n'
                    # output_content += f'\t\t\tauto inserted_id = m_{mas_name_snake_cased}_mongo_db_codec.patch({mas_name_snake_cased});\n'
                    # output_content += f'\t\t\tif (!inserted_id) {{\n'
                    # output_content += f'\t\t\t\tres.result(boost::beast::http::status::internal_server_error);\n'
                    # output_content += f'\t\t\t}}\n'
                    output_content += f'\t\t\tres.result(boost::beast::http::status::created);\n'
                    output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
                    output_content += f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(res.body().size()));\n'
                    output_content += f'\t\t\tres.body() = req.body();\n'
                    output_content += f'\t\t\tres.prepare_payload();\n'
                    output_content += f'\t\t}} else {{\n'
                    output_content += f'\t\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
                    output_content += f'\t\t}}\n'
                    output_content += f'\t}}\n\n'
                else:
                    output_content += (f'\tvoid create_{mas_name_snake_cased}(boost::beast::http::request<boost::beast::'
                                       f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                                       f'string_body>& res, [[maybe_unused]] const std::smatch&) {{\n')
                    output_content += f'\t\tif (req.method() == boost::beast::http::verb::post) {{\n'
                    output_content += f'\t\t\t{msg_name} {mas_name_snake_cased};\n'
                    output_content += f'\t\t\t{class_name}JsonToObject::json_to_object(req.body(), {mas_name_snake_cased});\n'
                    output_content += f'\t\t\tauto inserted_id = m_{mas_name_snake_cased}_mongo_db_codec.insert({mas_name_snake_cased});\n'
                    output_content += f'\t\t\tif (inserted_id == -1) {{\n'
                    output_content += f'\t\t\t\tres.result(boost::beast::http::status::internal_server_error);\n'
                    output_content += f'\t\t\t}}\n'
                    output_content += f'\t\t\tres.result(boost::beast::http::status::created);\n'
                    output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
                    output_content += f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(res.body().size()));\n'
                    output_content += f'\t\t\tres.body() = req.body();\n'
                    output_content += f'\t\t\tres.prepare_payload();\n'
                    output_content += f'\t\t}} else {{\n'
                    output_content += f'\t\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
                    output_content += f'\t\t}}\n'
                    output_content += f'\t}}\n\n'

                    output_content += (f'\tvoid put_{mas_name_snake_cased}(boost::beast::http::request<boost::beast::'
                                       f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                                       f'string_body>& res, [[maybe_unused]] const std::smatch& match) {{\n')
                    output_content += f'\t\tif (req.method() == boost::beast::http::verb::put) {{\n'
                    output_content += f'\t\t\t{msg_name} {mas_name_snake_cased};\n'
                    output_content += f'\t\t\t{class_name}JsonToObject::json_to_object(req.body(), {mas_name_snake_cased});\n'
                    output_content += f'\t\t\tauto inserted_id = m_{mas_name_snake_cased}_mongo_db_codec.patch({mas_name_snake_cased});\n'
                    output_content += f'\t\t\tif (!inserted_id) {{\n'
                    output_content += f'\t\t\t\tres.result(boost::beast::http::status::internal_server_error);\n'
                    output_content += f'\t\t\t}}\n'
                    output_content += f'\t\t\tres.result(boost::beast::http::status::created);\n'
                    output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
                    output_content += f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(res.body().size()));\n'
                    output_content += f'\t\t\tres.body() = req.body();\n'
                    output_content += f'\t\t\tres.prepare_payload();\n'
                    output_content += f'\t\t}} else {{\n'
                    output_content += f'\t\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
                    output_content += f'\t\t}}\n'
                    output_content += f'\t}}\n\n'

                    output_content += (f'\tvoid patch_{mas_name_snake_cased}(boost::beast::http::request<boost::beast::'
                                       f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                                       f'string_body>& res, [[maybe_unused]] const std::smatch& match) {{\n')
                    output_content += f'\tif (req.method() == boost::beast::http::verb::patch) {{\n'
                    output_content += f'\t\t\t{msg_name} {mas_name_snake_cased};\n'
                    output_content += f'\t\t\t{class_name}JsonToObject::json_to_object(req.body(), {mas_name_snake_cased});\n'
                    output_content += f'\t\t\tauto inserted_id = m_{mas_name_snake_cased}_mongo_db_codec.patch({mas_name_snake_cased});\n'
                    output_content += f'\t\t\tif (!inserted_id) {{\n'
                    output_content += f'\t\t\t\tres.result(boost::beast::http::status::internal_server_error);\n'
                    output_content += f'\t\t\t}}\n'
                    output_content += f'\t\t\tres.result(boost::beast::http::status::created);\n'
                    output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
                    output_content += f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(res.body().size()));\n'
                    output_content += f'\t\t\tres.body() = req.body();\n'
                    output_content += f'\t\t\tres.prepare_payload();\n'
                    output_content += f'\t\t}} else {{\n'
                    output_content += f'\t\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
                    output_content += f'\t\t}}\n'
                    output_content += f'\t}}\n\n'


                output_content += (f'\tvoid get_all_{mas_name_snake_cased}(boost::beast::http::request<boost::beast::'
                                   f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                                   f'string_body>& res, [[maybe_unused]] const std::smatch& match) {{\n')
                output_content += f'\t\tif (req.method() == boost::beast::http::verb::get) {{\n'
                output_content += f'\t\t\t{msg_name}List {mas_name_snake_cased}_list;\n'
                output_content += (f'\t\t\tm_{mas_name_snake_cased}_mongo_db_codec.get_all_data_from_collection('
                                   f'{mas_name_snake_cased}_list);\n')
                output_content += f'\t\t\tboost::json::object json;\n'
                output_content += f'\t\t\t{class_name}ObjectToJson::object_to_json({mas_name_snake_cased}_list, json);\n'
                output_content += f'\t\t\tres.result(boost::beast::http::status::ok);\n'
                output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
                output_content += f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(boost::json::serialize(json).size()));\n'
                output_content += f'\t\t\tres.body() = boost::json::serialize(json);\n'
                output_content += f'\t\t\tres.prepare_payload();\n'
                output_content += f'\t\t}} else {{\n'
                output_content += f'\t\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
                output_content += f'\t\t}}\n'
                output_content += f'\t}}\n\n'

                output_content += (f'\tvoid get_{mas_name_snake_cased}_by_id(boost::beast::http::request<boost::beast::'
                                   f'http::string_body>& req, boost::beast::http::response<boost::beast::http::'
                                   f'string_body>& res, [[maybe_unused]] const std::smatch& match) {{\n')
                output_content += f'\t\tif (req.method() == boost::beast::http::verb::get) {{\n'
                output_content += f'\t\t\t{msg_name} {mas_name_snake_cased};\n'
                output_content += (f'\t\t\tm_{mas_name_snake_cased}_mongo_db_codec.get_data_by_id_from_collection('
                                   f'{mas_name_snake_cased}, stoi(match[1]));\n')
                output_content += f'\t\t\tboost::json::object json;\n'
                output_content += f'\t\t\t{class_name}ObjectToJson::object_to_json({mas_name_snake_cased}, json);\n'
                output_content += f'\t\t\tres.result(boost::beast::http::status::ok);\n'
                output_content += f'\t\t\tres.set(boost::beast::http::field::content_type, "application/json");\n'
                output_content += f'\t\t\tres.set(boost::beast::http::field::content_length, std::to_string(boost::json::serialize(json).size()));\n'
                output_content += f'\t\t\tres.body() = boost::json::serialize(json);\n'
                output_content += f'\t\t\tres.prepare_payload();\n'
                output_content += f'\t\t}} else {{\n'
                output_content += f'\t\t\tres.result(boost::beast::http::status::method_not_allowed);\n'
                output_content += f'\t\t}}\n'
                output_content += f'\t}}\n\n'
        output_content += "};\n\n"

        output_file_name = f"{class_name_snake_cased}_web_server_routes.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppWebServerRoutesPlugin)
