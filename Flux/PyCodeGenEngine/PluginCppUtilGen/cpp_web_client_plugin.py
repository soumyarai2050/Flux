#!/usr/bin/env python
import logging
from typing import List, Callable, Tuple, Dict
import os
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case


class CppWebCLientPlugin(BaseProtoPlugin):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.field = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def get_field_names(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            if CppWebCLientPlugin.is_option_enabled\
                        (message, CppWebCLientPlugin.flux_msg_json_root):
                field_names = [field.proto.name for field in message.fields]

                for field_name in field_names:
                    if field_name not in self.field:
                        self.field.append(field_name)

    @staticmethod
    def header_generate_handler(file_name: str, class_name_snake_cased: str):
        output_content: str = ""
        output_content += "#pragma once\n\n"
        output_content += '#include <boost/beast.hpp>\n'
        output_content += '#include <boost/asio/ip/tcp.hpp>\n\n'

        output_content += f'#include "../ProtoGenCc/{file_name}.pb.h"\n'
        output_content += f'#include "../CppCodec/{class_name_snake_cased}_json_codec.h"\n'
        output_content += f'#include "{class_name_snake_cased}_populate_random_values.h"\n\n'

        return output_content

    @staticmethod
    def generate_client_url(message_name_snake_cased: str, class_name_snake_cased: str):
        output_content: str = ""
        output_content += f'const std::string get_all_{message_name_snake_cased}_client_url = ' \
                          f'"/{class_name_snake_cased}/get-all-{message_name_snake_cased}";\n'
        output_content += f'const std::string create_{message_name_snake_cased}_client_url = ' \
                          f'"/{class_name_snake_cased}/create-{message_name_snake_cased}";\n'
        output_content += f'const std::string create_all_{message_name_snake_cased}_client_url = ' \
                          f'"/{class_name_snake_cased}/create_all-{message_name_snake_cased}";\n'
        output_content += f'const std::string get_{message_name_snake_cased}_client_url = ' \
                          f'"/{class_name_snake_cased}/get-{message_name_snake_cased}";\n'
        output_content += f'const std::string put_{message_name_snake_cased}_client_url = ' \
                          f'"/{class_name_snake_cased}/put-{message_name_snake_cased}";\n'
        output_content += f'const std::string patch_{message_name_snake_cased}_client_url = ' \
                          f'"/{class_name_snake_cased}/patch-{message_name_snake_cased}";\n'
        output_content += f'const std::string delete_{message_name_snake_cased}_client_url = ' \
                          f'"/{class_name_snake_cased}/delete-{message_name_snake_cased}";\n\n'

        return output_content

    @staticmethod
    def generate_get_all_client(package_name: str, message_name: str, message_name_snake_cased: str, class_name: str):
        output_content: str = ""

        output_content += f'\t[[nodiscard]] bool get_all_{message_name_snake_cased}_client ({package_name}::' \
                          f'{message_name}List &{message_name_snake_cased}_list) const {{\n'
        output_content += '\t\tboost::asio::io_context io_context;\n'
        output_content += "\t\tboost::asio::ip::tcp::resolver resolver(io_context);\n"
        output_content += "\t\tauto result = resolver.resolve(host_, port_);\n\n"
        output_content += f"\t\tboost::beast::http::request<boost::beast::http::string_body> request{{boost::" \
                          f"beast::http::verb::get, get_all_{message_name_snake_cased}_client_url, 11}};\n"
        output_content += "\t\trequest.set(boost::beast::http::field::host, host_);\n"
        output_content += "\t\trequest.set(boost::beast::http::field::user_agent, BOOST_BEAST_VERSION_STRING);\n"
        output_content += "\n\t\tboost::asio::ip::tcp::socket socket(io_context);\n"
        output_content += "\t\tboost::asio::connect(socket, result.begin(), result.end());\n"
        output_content += "\t\tboost::beast::http::write(socket, request);\n\n"
        output_content += "\t\tboost::beast::flat_buffer buffer;\n"
        output_content += "\t\tboost::beast::http::response<boost::beast::http::dynamic_body> response;\n"
        output_content += "\t\tboost::beast::http::read(socket, buffer, response);\n"
        output_content += f"\t\tstd::string all_{message_name_snake_cased} = boost::beast::buffers_to_string" \
                          f"(response.body().data());\n\n"
        output_content += "\t\ttry {\n"
        output_content += "\t\t\tsocket.shutdown(boost::asio::ip::tcp::socket::shutdown_both);\n"
        output_content += "\t\t\tsocket.close();\n"
        output_content += "\t\t} catch (const boost::system::system_error& exception) {\n"
        output_content += '\t\t\tstd::cerr << "Error: " << exception.what() << std::endl;\n'
        output_content += "\t\t}\n\n"
        output_content += f"\t\tstd::string modified_{message_name_snake_cased}_json;\n"
        output_content += f'\t\tfor (int i = 0; i < all_{message_name_snake_cased}.size(); ++i) {{\n'
        output_content += f"\t\t\tif (all_{message_name_snake_cased}[i] == '_' && (i + 1 < all_{message_name_snake_cased}." \
                          f"size()) && all_{message_name_snake_cased}[i + 1] == 'i' && all_" \
                          f"{message_name_snake_cased}[i + 2] == 'd') {{\n"
        output_content += "\t\t\t\t// Skip the underscore if `_id` is detected\n"
        output_content += "\t\t\t\t// Do nothing, and let the loop increment i automatically\n"
        output_content += "\t\t\t} else {\n"
        output_content += "\t\t\t\t// Copy the character to the modified json\n"
        output_content += f"\t\t\t\tmodified_{message_name_snake_cased}_json += all_{message_name_snake_cased}[i];\n"
        output_content += "\t\t\t}\n\t\t}\n\n"
        output_content += f"\t\tbool status =  MarketDataJSONCodec::decode_{message_name_snake_cased}_list(" \
                          f"{message_name_snake_cased}_list, modified_{message_name_snake_cased}_json);\n"
        output_content += f"\t\treturn status;\n"
        output_content += "\t}\n\n"

        return output_content

    @staticmethod
    def generate_get_client(package_name: str, message_name: str, message_name_snake_cased: str, class_name: str):
        output_content: str = ""

        output_content += f'\t[[nodiscard]] bool get_{message_name_snake_cased}_client({package_name}::' \
                          f'{message_name} &{message_name_snake_cased}, const std::string ' \
                          f'&{message_name_snake_cased}_id) const {{\n'
        output_content += '\t\tboost::asio::io_context io_context;\n'
        output_content += "\t\tboost::asio::ip::tcp::resolver resolver(io_context);\n"
        output_content += "\t\tauto result = resolver.resolve(host_, port_);\n\n"
        output_content += f"\t\tboost::beast::http::request<boost::beast::http::string_body> request{{boost::" \
                          f"beast::http::verb::get, get_{message_name_snake_cased}_client_url + '/' + " \
                          f"{message_name_snake_cased}_id, 11}};\n"
        output_content += "\t\trequest.set(boost::beast::http::field::host, host_);\n"
        output_content += "\t\trequest.set(boost::beast::http::field::user_agent, BOOST_BEAST_VERSION_STRING);\n"
        output_content += "\n\t\tboost::asio::ip::tcp::socket socket(io_context);\n"
        output_content += "\t\tboost::asio::connect(socket, result.begin(), result.end());\n"
        output_content += "\t\tboost::beast::http::write(socket, request);\n\n"
        output_content += "\t\tboost::beast::flat_buffer buffer;\n"
        output_content += "\t\tboost::beast::http::response<boost::beast::http::dynamic_body> response;\n"
        output_content += "\t\tboost::beast::http::read(socket, buffer, response);\n"
        output_content += f"\t\tstd::string {message_name_snake_cased}_json = boost::beast::buffers_to_string" \
                          f"(response.body().data());\n\n"
        output_content += "\t\ttry {\n"
        output_content += "\t\t\tsocket.shutdown(boost::asio::ip::tcp::socket::shutdown_both);\n"
        output_content += "\t\t\tsocket.close();\n"
        output_content += "\t\t} catch (const boost::system::system_error& exception) {\n"
        output_content += '\t\t\tstd::cerr << "Error: " << exception.what() << std::endl;\n'
        output_content += "\t\t}\n\n"
        output_content += f"\t\tstd::string modified_{message_name_snake_cased}_json;\n"
        output_content += f'\t\tfor (int i = 0; i < {message_name_snake_cased}_json.size(); ++i) {{\n'
        output_content += f"\t\t\tif ({message_name_snake_cased}_json[i] == '_' && (i + 1 < " \
                          f"{message_name_snake_cased}_json.size()) && {message_name_snake_cased}_json[i + 1] == " \
                          f"'i' && {message_name_snake_cased}_json[i + 2] == 'd') {{\n"
        output_content += "\t\t\t\t// Skip the underscore if `_id` is detected\n"
        output_content += "\t\t\t\t// Do nothing, and let the loop increment i automatically\n"
        output_content += "\t\t\t} else {\n"
        output_content += "\t\t\t\t// Copy the character to the modified json\n"
        output_content += f"\t\t\t\tmodified_{message_name_snake_cased}_json += {message_name_snake_cased}_json[i];\n"
        output_content += "\t\t\t}\n\t\t}\n\n"
        output_content += f"\t\tbool status =  MarketDataJSONCodec::decode_{message_name_snake_cased}(" \
                          f"{message_name_snake_cased}, modified_{message_name_snake_cased}_json);\n"
        output_content += f"\t\treturn status;\n"
        output_content += "\t}\n\n"

        return output_content

    @staticmethod
    def generate_create_client(package_name: str, message_name: str, message_name_snake_cased: str, class_name: str):

        output_content: str = ""

        output_content += f'\t[[nodiscard]] bool create_{message_name_snake_cased}_client ({package_name}::' \
                          f'{message_name} &{message_name_snake_cased}) const {{\n'
        output_content += f"\t\tstd::string {message_name_snake_cased}_json;\n"
        output_content += f"\t\tbool status = {class_name}JSONCodec::encode_{message_name_snake_cased}" \
                          f"({message_name_snake_cased}, {message_name_snake_cased}_json, true);\n"
        output_content += f"\t\tif (status) {{\n"
        output_content += '\t\t\tboost::asio::io_context io_context;\n'
        output_content += "\t\t\tboost::asio::ip::tcp::resolver resolver(io_context);\n"
        output_content += "\t\t\tauto result = resolver.resolve(host_, port_);\n\n"
        output_content += f"\t\t\tboost::beast::http::request<boost::beast::http::string_body> request{{boost::" \
                          f"beast::http::verb::post, create_{message_name_snake_cased}_client_url, 11}};\n"
        output_content += "\t\t\trequest.set(boost::beast::http::field::host, host_);\n"
        output_content += "\t\t\trequest.set(boost::beast::http::field::user_agent, BOOST_BEAST_VERSION_STRING);\n"
        output_content += '\t\t\trequest.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += f'\t\t\trequest.body() = {message_name_snake_cased}_json;\n'
        output_content += f'\t\t\trequest.set(boost::beast::http::field::content_length, std::to_string(' \
                          f'{message_name_snake_cased}_json.size()));\n'
        output_content += "\t\t\trequest.prepare_payload();\n"
        output_content += "\n\t\t\tboost::asio::ip::tcp::socket socket(io_context);\n"
        output_content += "\t\t\tboost::asio::connect(socket, result.begin(), result.end());\n"
        output_content += "\t\t\tboost::beast::http::write(socket, request);\n\n"
        output_content += "\t\t\tboost::beast::flat_buffer buffer;\n"
        output_content += "\t\t\tboost::beast::http::response<boost::beast::http::dynamic_body> response;\n"
        output_content += "\t\t\tboost::beast::http::read(socket, buffer, response);\n"
        output_content += f"\t\t\tstd::string {message_name_snake_cased}_recieved_json = boost::beast::" \
                          f"buffers_to_string(response.body().data());\n\n"
        output_content += "\t\t\ttry {\n"
        output_content += "\t\t\t\tsocket.shutdown(boost::asio::ip::tcp::socket::shutdown_both);\n"
        output_content += "\t\t\t\tsocket.close();\n"
        output_content += "\t\t\t} catch (const boost::system::system_error& exception) {\n"
        output_content += '\t\t\t\tstd::cerr << "Error: " << exception.what() << std::endl;\n'
        output_content += "\t\t\t}\n\n"
        output_content += f"\t\t\tstd::string modified_{message_name_snake_cased}_json;\n"
        output_content += f'\t\t\tfor (int i = 0; i < {message_name_snake_cased}_recieved_json.size(); ++i) {{\n'
        output_content += f"\t\t\t\tif ({message_name_snake_cased}_recieved_json[i] == '_' && (i + 1 < " \
                          f"{message_name_snake_cased}_recieved_json.size()) && {message_name_snake_cased}" \
                          f"_recieved_json[i + 1] == 'i' && {message_name_snake_cased}_recieved_json[i + 2] == 'd') {{\n"
        output_content += "\t\t\t\t\t// Skip the underscore if `_id` is detected\n"
        output_content += "\t\t\t\t\t// Do nothing, and let the loop increment i automatically\n"
        output_content += "\t\t\t\t} else {\n"
        output_content += "\t\t\t\t\t// Copy the character to the modified json\n"
        output_content += f"\t\t\t\t\tmodified_{message_name_snake_cased}_json += {message_name_snake_cased}_recieved" \
                          f"_json[i];\n"
        output_content += "\t\t\t\t}\n\t\t\t}\n\n"
        output_content += f"\t\t\tstatus =  MarketDataJSONCodec::decode_{message_name_snake_cased}(" \
                          f"{message_name_snake_cased}, modified_{message_name_snake_cased}_json);\n"
        output_content += "\t\t} else {\n"
        output_content += f"\t\t\treturn false;\n"
        output_content += "\t\t}\n"
        output_content += "\t\treturn status;\n"
        output_content += "\t}\n\n"

        return output_content

    @staticmethod
    def generate_create_all_client(package_name: str, message_name: str, message_name_snake_cased: str, class_name: str):

        output_content: str = ""

        output_content += f'\t[[nodiscard]] bool create_{message_name_snake_cased}_client ({package_name}::' \
                          f'{message_name}List {message_name_snake_cased}_recieved_list, const {package_name}::' \
                          f'{message_name}List &{message_name_snake_cased}_list) const {{\n'
        output_content += f"\t\tstd::string {message_name_snake_cased}_json;\n"
        output_content += f"\t\tbool status = {class_name}JSONCodec::encode_{message_name_snake_cased}_list(" \
                          f"{message_name_snake_cased}_list, {message_name_snake_cased}_json);\n"
        output_content += "\t\tif (status) {\n"
        output_content += '\t\t\tboost::asio::io_context io_context;\n'
        output_content += "\t\t\tboost::asio::ip::tcp::resolver resolver(io_context);\n"
        output_content += "\t\t\tauto result = resolver.resolve(host_, port_);\n\n"
        output_content += f"\t\t\tboost::beast::http::request<boost::beast::http::string_body> request{{boost::" \
                          f"beast::http::verb::post, create_all_{message_name_snake_cased}_client_url, 11}};\n"
        output_content += "\t\t\trequest.set(boost::beast::http::field::host, host_);\n"
        output_content += "\t\t\trequest.set(boost::beast::http::field::user_agent, BOOST_BEAST_VERSION_STRING);\n"
        output_content += '\t\t\trequest.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += f'\t\t\trequest.body() = {message_name_snake_cased}_json;\n'
        output_content += f'\t\t\trequest.set(boost::beast::http::field::content_length, std::to_string(' \
                          f'{message_name_snake_cased}_json.size()));\n'
        output_content += "\t\t\trequest.prepare_payload();\n"
        output_content += "\n\t\t\tboost::asio::ip::tcp::socket socket(io_context);\n"
        output_content += "\t\t\tboost::asio::connect(socket, result.begin(), result.end());\n"
        output_content += "\t\t\tboost::beast::http::write(socket, request);\n\n"
        output_content += "\t\t\tboost::beast::flat_buffer buffer;\n"
        output_content += "\t\t\tboost::beast::http::response<boost::beast::http::dynamic_body> response;\n"
        output_content += "\t\t\tboost::beast::http::read(socket, buffer, response);\n"
        output_content += f"\t\t\tstd::string {message_name_snake_cased}_recieved_json = boost::beast::" \
                          f"buffers_to_string(response.body().data());\n\n"
        output_content += "\t\ttry {\n"
        output_content += "\t\t\tsocket.shutdown(boost::asio::ip::tcp::socket::shutdown_both);\n"
        output_content += "\t\t\tsocket.close();\n"
        output_content += "\t\t} catch (const boost::system::system_error& exception) {\n"
        output_content += '\t\t\tstd::cerr << "Error: " << exception.what() << std::endl;\n'
        output_content += "\t\t}\n\n"
        output_content += f"\t\t\tstd::string modified_{message_name_snake_cased}_json;\n"
        output_content += f'\t\t\tfor (int i = 0; i < {message_name_snake_cased}_recieved_json.size(); ++i) {{\n'
        output_content += f"\t\t\t\tif ({message_name_snake_cased}_recieved_json[i] == '_' && (i + 1 < " \
                          f"{message_name_snake_cased}_recieved_json.size()) && {message_name_snake_cased}" \
                          f"_recieved_json[i + 1] == 'i' && {message_name_snake_cased}_recieved_json[i + 2] == 'd') {{\n"
        output_content += "\t\t\t\t\t// Skip the underscore if `_id` is detected\n"
        output_content += "\t\t\t\t\t// Do nothing, and let the loop increment i automatically\n"
        output_content += "\t\t\t\t} else {\n"
        output_content += "\t\t\t\t\t// Copy the character to the modified json\n"
        output_content += f"\t\t\t\t\tmodified_{message_name_snake_cased}_json += {message_name_snake_cased}_recieved" \
                          f"_json[i];\n"
        output_content += "\t\t\t\t}\n\t\t\t}\n\n"
        output_content += f"\t\t\tstatus =  MarketDataJSONCodec::decode_{message_name_snake_cased}_list(" \
                          f"{message_name_snake_cased}_recieved_list, modified_{message_name_snake_cased}_json);\n"
        output_content += "\t\t} else {\n"
        output_content += f"\t\t\treturn false;\n"
        output_content += "\t\t}\n"
        output_content += "\t\treturn status;\n"
        output_content += "\t}\n\n"

        return output_content

    @staticmethod
    def generate_delete_client(message_name_snake_cased: str):

        output_content: str = ""

        output_content += f'\t[[nodiscard]] std::string delete_{message_name_snake_cased}_client (const ' \
                          f'std::string &{message_name_snake_cased}_id) const {{\n'
        output_content += '\t\tboost::asio::io_context io_context;\n'
        output_content += "\t\tboost::asio::ip::tcp::resolver resolver(io_context);\n"
        output_content += "\t\tauto result = resolver.resolve(host_, port_);\n\n"
        output_content += f"\t\tboost::beast::http::request<boost::beast::http::string_body> request{{boost::" \
                          f"beast::http::verb::delete_, delete_{message_name_snake_cased}_client_url + '/' + " \
                          f"{message_name_snake_cased}_id, 11}};\n"
        output_content += "\t\trequest.set(boost::beast::http::field::host, host_);\n"
        output_content += "\t\trequest.set(boost::beast::http::field::user_agent, BOOST_BEAST_VERSION_STRING);\n"
        output_content += "\n\t\tboost::asio::ip::tcp::socket socket(io_context);\n"
        output_content += "\t\tboost::asio::connect(socket, result.begin(), result.end());\n"
        output_content += "\t\tboost::beast::http::write(socket, request);\n\n"
        output_content += "\t\tboost::beast::flat_buffer buffer;\n"
        output_content += "\t\tboost::beast::http::response<boost::beast::http::dynamic_body> response;\n"
        output_content += "\t\tboost::beast::http::read(socket, buffer, response);\n"
        output_content += f"\t\tstd::string {message_name_snake_cased} = boost::beast::buffers_to_string" \
                          f"(response.body().data());\n\n"
        output_content += "\t\ttry {\n"
        output_content += "\t\t\tsocket.shutdown(boost::asio::ip::tcp::socket::shutdown_both);\n"
        output_content += "\t\t\tsocket.close();\n"
        output_content += "\t\t} catch (const boost::system::system_error& exception) {\n"
        output_content += '\t\t\tstd::cerr << "Error: " << exception.what() << std::endl;\n'
        output_content += "\t\t}\n\n"
        output_content += f"\t\treturn {message_name_snake_cased};\n"
        output_content += "\t}\n\n"

        return output_content

    @staticmethod
    def generate_put_client(package_name: str, message_name: str, message_name_snake_cased: str, class_name: str):

        output_content: str = ""

        output_content += f'\t[[nodiscard]] bool put_{message_name_snake_cased}_client ({package_name}::' \
                          f'{message_name} &{message_name_snake_cased}) const {{\n'
        output_content += '\t\tboost::asio::io_context io_context;\n'
        output_content += "\t\tboost::asio::ip::tcp::resolver resolver(io_context);\n"
        output_content += f"\t\tstd::string {message_name_snake_cased}_json;\n"
        output_content += f"\t\tbool status = {class_name}JSONCodec::encode_{message_name_snake_cased}(" \
                          f"{message_name_snake_cased}, {message_name_snake_cased}_json, true);\n"
        output_content += f"\t\tif (status) {{\n"
        output_content += f'\t\t\tsize_t pos = {message_name_snake_cased}_json.find("id");\n'
        output_content += f'\t\t\twhile (pos != std::string::npos) {{\n'
        output_content += f"\t\t\t\t// Check if there's no underscore before `id`\n"
        output_content += f"\t\t\t\tif (pos == 0 || {message_name_snake_cased}_json[pos - 1] != '_' && (!std::isalpha" \
                          f"({message_name_snake_cased}_json[pos - 1]))) {{\n"
        output_content += f"\t\t\t\t\t// Insert the underscore before `id`\n"
        output_content += f'\t\t\t\t\t{message_name_snake_cased}_json.insert(pos, "_");\n'
        output_content += f"\t\t\t\t\t// Move the search position to the end of the inserted underscore\n"
        output_content += f"\t\t\t\t\tpos += 1;\n"
        output_content += "\t\t\t\t}\n"
        output_content += "\t\t\t\t// Find the next occurrence of `id`\n"
        output_content += f'\t\t\t\tpos = {message_name_snake_cased}_json.find("id", pos + 1);\n'
        output_content += "\t\t\t}\n\n"
        output_content += "\t\t\tauto result = resolver.resolve(host_, port_);\n\n"
        output_content += f"\t\t\tboost::beast::http::request<boost::beast::http::string_body> request{{boost::" \
                          f"beast::http::verb::put, put_{message_name_snake_cased}_client_url, 11}};\n"
        output_content += "\t\t\trequest.set(boost::beast::http::field::host, host_);\n"
        output_content += "\t\t\trequest.set(boost::beast::http::field::user_agent, BOOST_BEAST_VERSION_STRING);\n"
        output_content += '\t\t\trequest.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += f'\t\t\trequest.body() = {message_name_snake_cased}_json;\n'
        output_content += f'\t\t\trequest.set(boost::beast::http::field::content_length, std::to_string(' \
                          f'{message_name_snake_cased}_json.size()));\n'
        output_content += "\t\t\trequest.prepare_payload();\n"
        output_content += "\n\t\t\tboost::asio::ip::tcp::socket socket(io_context);\n"
        output_content += "\t\t\tboost::asio::connect(socket, result.begin(), result.end());\n"
        output_content += "\t\t\tboost::beast::http::write(socket, request);\n\n"
        output_content += "\t\t\tboost::beast::flat_buffer buffer;\n"
        output_content += "\t\t\tboost::beast::http::response<boost::beast::http::dynamic_body> response;\n"
        output_content += "\t\t\tboost::beast::http::read(socket, buffer, response);\n"
        output_content += f"\t\t\tstd::string {message_name_snake_cased}_recieved_json = boost::beast::buffers_to_string" \
                          f"(response.body().data());\n\n"
        output_content += "\t\t\ttry {\n"
        output_content += "\t\t\t\tsocket.shutdown(boost::asio::ip::tcp::socket::shutdown_both);\n"
        output_content += "\t\t\t\tsocket.close();\n"
        output_content += "\t\t\t} catch (const boost::system::system_error& exception) {\n"
        output_content += '\t\t\t\tstd::cerr << "Error: " << exception.what() << std::endl;\n'
        output_content += "\t\t\t}\n\n"
        output_content += f"\t\t\tstd::string modified_{message_name_snake_cased}_json;\n"
        output_content += f'\t\t\tfor (int i = 0; i < {message_name_snake_cased}_recieved_json.size(); ++i) {{\n'
        output_content += f"\t\t\t\tif ({message_name_snake_cased}_recieved_json[i] == '_' && (i + 1 < " \
                          f"{message_name_snake_cased}_recieved_json.size()) && {message_name_snake_cased}" \
                          f"_recieved_json[i + 1] == 'i' && {message_name_snake_cased}_recieved_json[i + 2] == 'd') {{\n"
        output_content += "\t\t\t\t\t// Skip the underscore if `_id` is detected\n"
        output_content += "\t\t\t\t\t// Do nothing, and let the loop increment i automatically\n"
        output_content += "\t\t\t\t} else {\n"
        output_content += "\t\t\t\t\t// Copy the character to the modified json\n"
        output_content += f"\t\t\t\t\tmodified_{message_name_snake_cased}_json += {message_name_snake_cased}" \
                          f"_recieved_json[i];\n"
        output_content += "\t\t\t\t}\n\t\t\t}\n\n"
        output_content += f"\t\t\tstatus =  MarketDataJSONCodec::decode_{message_name_snake_cased}(" \
                          f"{message_name_snake_cased}, modified_{message_name_snake_cased}_json);\n"
        output_content += "\t\t} else {\n"
        output_content += "\t\t\treturn false;\n"
        output_content += "\t\t}\n"
        output_content += f"\t\treturn status;\n"
        output_content += "\t}\n\n"

        return output_content

    @staticmethod
    def generate_patch_client(package_name: str, message_name: str, message_name_snake_cased: str, class_name: str):

        output_content: str = ""

        output_content += f'\t[[nodiscard]] bool patch_{message_name_snake_cased}_client ({package_name}::' \
                          f'{message_name} &{message_name_snake_cased}) const {{\n'
        output_content += '\t\tboost::asio::io_context io_context;\n'
        output_content += "\t\tboost::asio::ip::tcp::resolver resolver(io_context);\n"
        output_content += f"\t\tstd::string {message_name_snake_cased}_json;\n"
        output_content += f"\t\tbool status = {class_name}JSONCodec::encode_{message_name_snake_cased}(" \
                          f"{message_name_snake_cased}, {message_name_snake_cased}_json);\n"
        output_content += f"\t\tif (status) {{\n"
        output_content += f'\t\t\tsize_t pos = {message_name_snake_cased}_json.find("id");\n'
        output_content += f'\t\t\twhile (pos != std::string::npos) {{\n'
        output_content += f"\t\t\t\t// Check if there's no underscore before `id`\n"
        output_content += f"\t\t\t\tif (pos == 0 || {message_name_snake_cased}_json[pos - 1] != '_' && (!std::isalpha" \
                          f"({message_name_snake_cased}_json[pos - 1]))) {{\n"
        output_content += f"\t\t\t\t\t// Insert the underscore before `id`\n"
        output_content += f'\t\t\t\t\t{message_name_snake_cased}_json.insert(pos, "_");\n'
        output_content += f"\t\t\t\t\t// Move the search position to the end of the inserted underscore\n"
        output_content += f"\t\t\t\t\tpos += 1;\n"
        output_content += "\t\t\t\t}\n"
        output_content += "\t\t\t\t// Find the next occurrence of `id`\n"
        output_content += f'\t\t\t\tpos = {message_name_snake_cased}_json.find("id", pos + 1);\n'
        output_content += "\t\t\t}\n\n"
        output_content += "\t\t\tauto result = resolver.resolve(host_, port_);\n\n"
        output_content += f"\t\t\tboost::beast::http::request<boost::beast::http::string_body> request{{boost::" \
                          f"beast::http::verb::patch, patch_{message_name_snake_cased}_client_url, 11}};\n"
        output_content += "\t\t\trequest.set(boost::beast::http::field::host, host_);\n"
        output_content += "\t\t\trequest.set(boost::beast::http::field::user_agent, BOOST_BEAST_VERSION_STRING);\n"
        output_content += '\t\t\trequest.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += f'\t\t\trequest.body() = {message_name_snake_cased}_json;\n'
        output_content += f'\t\t\trequest.set(boost::beast::http::field::content_length, std::to_string(' \
                          f'{message_name_snake_cased}_json.size()));\n'
        output_content += "\t\t\trequest.prepare_payload();\n"
        output_content += "\n\t\t\tboost::asio::ip::tcp::socket socket(io_context);\n"
        output_content += "\t\t\tboost::asio::connect(socket, result.begin(), result.end());\n"
        output_content += "\t\t\tboost::beast::http::write(socket, request);\n\n"
        output_content += "\t\t\tboost::beast::flat_buffer buffer;\n"
        output_content += "\t\t\tboost::beast::http::response<boost::beast::http::dynamic_body> response;\n"
        output_content += "\t\t\tboost::beast::http::read(socket, buffer, response);\n"
        output_content += f"\t\t\tstd::string {message_name_snake_cased}_recieved_json = boost::beast::buffers_to_string" \
                          f"(response.body().data());\n\n"
        output_content += "\t\t\ttry {\n"
        output_content += "\t\t\t\tsocket.shutdown(boost::asio::ip::tcp::socket::shutdown_both);\n"
        output_content += "\t\t\t\tsocket.close();\n"
        output_content += "\t\t\t} catch (const boost::system::system_error& exception) {\n"
        output_content += '\t\t\t\tstd::cerr << "Error: " << exception.what() << std::endl;\n'
        output_content += "\t\t\t}\n\n"
        output_content += f"\t\t\tstd::string modified_{message_name_snake_cased}_json;\n"
        output_content += f'\t\t\tfor (int i = 0; i < {message_name_snake_cased}_recieved_json.size(); ++i) {{\n'
        output_content += f"\t\t\t\tif ({message_name_snake_cased}_recieved_json[i] == '_' && (i + 1 < " \
                          f"{message_name_snake_cased}_recieved_json.size()) && {message_name_snake_cased}" \
                          f"_recieved_json[i + 1] == 'i' && {message_name_snake_cased}_recieved_json[i + 2] == 'd') {{\n"
        output_content += "\t\t\t\t\t// Skip the underscore if `_id` is detected\n"
        output_content += "\t\t\t\t\t// Do nothing, and let the loop increment i automatically\n"
        output_content += "\t\t\t\t} else {\n"
        output_content += "\t\t\t\t\t// Copy the character to the modified json\n"
        output_content += f"\t\t\t\t\tmodified_{message_name_snake_cased}_json += {message_name_snake_cased}" \
                          f"_recieved_json[i];\n"
        output_content += "\t\t\t\t}\n\t\t\t}\n\n"
        output_content += f"\t\t\tstatus =  MarketDataJSONCodec::decode_{message_name_snake_cased}(" \
                          f"{message_name_snake_cased}, modified_{message_name_snake_cased}_json);\n"
        output_content += "\t\t} else {\n"
        output_content += "\t\t\treturn false;\n"
        output_content += "\t\t}\n"
        output_content += f"\t\treturn status;\n"
        output_content += "\t}\n\n"

        return output_content

    def output_file_generate_handler(self, file: protogen.File):
        self.get_all_root_message(file.messages)
        self.get_field_names(self.root_message_list)

        file_name: str = str(file.proto.name).split(".")[0]
        package_name: str = str(file.proto.package)
        class_name_list: List[str] = package_name.split('_')
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content: str = ""

        output_content += self.header_generate_handler(file_name, class_name_snake_cased)

        for message in self.root_message_list:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            if CppWebCLientPlugin.is_option_enabled(message, CppWebCLientPlugin.flux_msg_executor_options):
                output_content += self.generate_client_url(message_name_snake_cased, class_name_snake_cased)

        output_content += f"\nclass {class_name}WebClient {{\n"
        output_content += "public:\n"
        output_content += f'\t{class_name}WebClient(std::string &host, std::string &port) : host_(std::move(host)), ' \
                          f'port_(std::move(port)) {{}}\n\n'

        for message in self.root_message_list:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            if CppWebCLientPlugin.is_option_enabled(message, CppWebCLientPlugin.flux_msg_executor_options) and \
               CppWebCLientPlugin.is_option_enabled(message, CppWebCLientPlugin.flux_msg_executor_options):
                output_content += self.generate_get_client(package_name, message_name, message_name_snake_cased,
                                                           class_name)
                output_content += self.generate_get_all_client(package_name, message_name, message_name_snake_cased,
                                                               class_name)
                output_content += self.generate_create_client(package_name, message_name, message_name_snake_cased,
                                                              class_name)
                output_content += self.generate_create_all_client(package_name, message_name, message_name_snake_cased,
                                                                  class_name)
                output_content += self.generate_patch_client(package_name, message_name, message_name_snake_cased,
                                                             class_name)
                output_content += self.generate_put_client(package_name, message_name, message_name_snake_cased,
                                                           class_name)
                output_content += self.generate_delete_client(message_name_snake_cased)
        output_content += "private:\n"
        output_content += "\tconst std::string host_;\n"
        output_content += "\tconst std::string port_;\n"
        output_content += "};\n"

        output_file_name = f"{class_name_snake_cased}_web_client.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppWebCLientPlugin)