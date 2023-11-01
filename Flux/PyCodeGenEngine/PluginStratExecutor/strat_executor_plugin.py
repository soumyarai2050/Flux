#!/usr/bin/env python
import json
import logging
from typing import List, Callable, Tuple, Dict
import os
import time

from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import (convert_camel_case_to_specific_case,
                                                       convert_to_capitalized_camel_case)
from FluxPythonUtils.scripts.utility_functions import parse_to_int


class StratExecutorPlugin(BaseProtoPlugin):
    """
    Plugin to generate strat executor helping scripts
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.ws_manager_required_messages: List[protogen.Message] = []
        self.ws_manager_required_top_lvl_messages: List[protogen.Message] = []
        self.get_cache_key_required_messages = []
        self.get_log_key_required_messages = []
        self.get_cache_key_required_msg_to_key_count_dict: Dict[protogen.Message, int] = {}
        self.beanie_pydantic_model_dir_name = "Pydentic"
        self.beanie_fastapi_model_dir_name = "FastApi"
        self.file_name = ""
        self.file_name_cap_camel_cased = ""
        self.model_file_name = ""
        self.ws_data_manager_file_name: str = ""
        self.base_strat_cache_file_name: str = ""
        self.base_strat_cache_class_name: str = ""
        self.base_trading_cache_file_name: str = ""
        self.base_trading_cache_class_name: str = ""
        self.key_handler_file_name: str = ""


    @staticmethod
    def _clean_string_key_val(key: str):
        if key[1] == "\'" and key[-1] == "\'":
            # removing extra escape chars from string
            return f"'{key[2:-2]}'"
        else:
            return key

    @staticmethod
    def get_executor_key_sequence_list_of_model(message: protogen.Message) -> List[List[str]] | None:
        if BaseProtoPlugin.is_option_enabled(message, BaseProtoPlugin.flux_msg_executor_options):
            option_dict = \
                BaseProtoPlugin.get_complex_option_value_from_proto(message, BaseProtoPlugin.flux_msg_executor_options)
            key_sequence_option_val: List[str] | str | None = \
                option_dict.get(BaseProtoPlugin.executor_option_executor_key_sequence_field)
            if key_sequence_option_val is not None:
                return_list = []
                for key_seq in key_sequence_option_val:
                    key_sequence_option_val_hyphen_sep = key_seq.split("-")
                    for index, key_sequence_option_val in enumerate(key_sequence_option_val_hyphen_sep):
                        key_sequence_option_val_hyphen_sep[index] = \
                            StratExecutorPlugin._clean_string_key_val(key_sequence_option_val)
                    return_list.append(key_sequence_option_val_hyphen_sep)
                return return_list
            # else not required: other cases are acceptable and None will be returned since no
            # key_sequence_option_val is found to be processed or if key_sequence_option_val is
            # present but key_counts_option_val is not then default value 1 is used as key_counts
        return None

    @staticmethod
    def get_log_key_sequence_list_of_model(message: protogen.Message):
        if BaseProtoPlugin.is_option_enabled(message, BaseProtoPlugin.flux_msg_executor_options):
            option_dict = \
                BaseProtoPlugin.get_complex_option_value_from_proto(message, BaseProtoPlugin.flux_msg_executor_options)
            log_key_sequence_option_val: List[str] | str | None = \
                option_dict.get(BaseProtoPlugin.executor_option_log_key_sequence_field)
            if log_key_sequence_option_val is not None:
                key_sequence_option_val_hyphen_sep = log_key_sequence_option_val.split("-")
                for index, key_sequence_option_val in enumerate(key_sequence_option_val_hyphen_sep):
                    key_sequence_option_val_hyphen_sep[index] = \
                        StratExecutorPlugin._clean_string_key_val(key_sequence_option_val)
                return key_sequence_option_val_hyphen_sep
            # else not required: returning None if log_key_sequence_option_val not found
        return None

    def set_data_members(self, file: protogen.File):
        file_name_snake_cased = convert_camel_case_to_specific_case(self.file_name)
        self.ws_data_manager_file_name = f"{file_name_snake_cased}_ws_data_manager"
        self.base_strat_cache_file_name = f"{file_name_snake_cased}_base_strat_cache"
        self.base_strat_cache_class_name = f"{self.file_name_cap_camel_cased}BaseStratCache"
        self.base_trading_cache_file_name = f"{file_name_snake_cased}_base_trading_cache"
        self.base_trading_cache_class_name = f"{self.file_name_cap_camel_cased}BaseTradingCache"
        self.model_file_name = f"{file_name_snake_cased}_beanie_model"
        self.key_handler_file_name = f"{file_name_snake_cased}_key_handler"
        for message in file.messages:
            if StratExecutorPlugin.is_option_enabled(message, StratExecutorPlugin.flux_msg_executor_options):
                option_value_dict = \
                    StratExecutorPlugin.get_complex_option_value_from_proto(
                        message, StratExecutorPlugin.flux_msg_executor_options)
                if option_value_dict.get(StratExecutorPlugin.executor_option_is_websocket_model_field):
                    self.ws_manager_required_messages.append(message)
                if option_value_dict.get(StratExecutorPlugin.executor_option_is_top_lvl_model_field):
                    self.ws_manager_required_top_lvl_messages.append(message)
                if option_value_dict.get(StratExecutorPlugin.executor_option_executor_key_sequence_field):
                    self.get_cache_key_required_messages.append(message)
                if option_value_dict.get(StratExecutorPlugin.executor_option_log_key_sequence_field):
                    self.get_log_key_required_messages.append(message)
                if (key_count := option_value_dict.get(StratExecutorPlugin.executor_option_executor_key_count_field)) is None:
                    self.get_cache_key_required_msg_to_key_count_dict[message] = 1
                else:
                    try:
                        key_count = int(key_count)
                    except ValueError as e:
                        err_str = f"key_count {key_count} for message {message.proto.name} is of type " \
                                  f"{type(key_count)} is not parsable in integer, exception: {e}"
                        logging.exception(err_str)
                        raise Exception(err_str)
                    if int(key_count) > 2:
                        err_str = "Unsupported: current implementation only handles 1 or 2 keys, " \
                                  f"received request for {key_count} for message {message.proto.name}"
                        logging.exception(err_str)
                        raise Exception(err_str)
                    else:
                        self.get_cache_key_required_msg_to_key_count_dict[message] = key_count

    def data_manager_model_based_handler_for_top_lvl_content(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        content_str = f'\tdef handle_{message_name_snake_cased}_get_all_ws(self, ' \
                      f'{message_name_snake_cased}_: {message_name}BaseModel | {message_name}, **kwargs):\n'
        content_str += f"\t\twith self.{message_name_snake_cased}_ws_get_all_cont.single_obj_lock:\n"
        content_str += f"\t\t\t{message_name_snake_cased}_tuple = " \
                       f"self.trading_cache.get_{message_name_snake_cased}()\n"
        content_str += f"\t\t\tif {message_name_snake_cased}_tuple is None or " \
                       f"{message_name_snake_cased}_tuple[0] is None:\n"
        content_str += f"\t\t\t\tself.trading_cache.set_{message_name_snake_cased}({message_name_snake_cased}_)\n"
        content_str += "\t\t\t\tkwargs = {'"+f"{message_name_snake_cased}_"+"': "+f"{message_name_snake_cased}_"+"}\n"
        content_str += f"\t\t\t\tself.underlying_handle_{message_name_snake_cased}_ws(**kwargs)\n"
        content_str += f"\t\t\t\tif self.{message_name_snake_cased}_ws_get_all_cont.notify:\n"
        content_str += f"\t\t\t\t\tself.strat_cache.notify_all()\n"
        content_str += f'\t\t\t\tlogging.info(f"Added '+f'{message_name_snake_cased}' + \
                       ' with id: {'+f'{message_name_snake_cased}'+'_.id}")\n'
        content_str += f"\t\t\telse:\n"
        option_value_dict = \
            StratExecutorPlugin.get_complex_option_value_from_proto(
                message, StratExecutorPlugin.flux_msg_executor_options)
        is_repeated = option_value_dict.get(StratExecutorPlugin.executor_option_is_repeated_field)
        if is_repeated:
            content_str += f"\t\t\t\t{message_name_snake_cased}_list, _ = {message_name_snake_cased}_tuple\n"
            content_str += f"\t\t\t\t{message_name_snake_cased} = {message_name_snake_cased}_list[-1]\n"
        else:
            content_str += f"\t\t\t\t{message_name_snake_cased}, _ = {message_name_snake_cased}_tuple\n"
        content_str += f"\t\t\t\tif {message_name_snake_cased}.id == {message_name_snake_cased}_.id:\n"
        content_str += f"\t\t\t\t\tself.trading_cache.set_{message_name_snake_cased}({message_name_snake_cased}_)\n"
        content_str += f"\t\t\t\t\tif self.{message_name_snake_cased}_ws_get_all_cont.notify:\n"
        content_str += f"\t\t\t\t\t\tself.strat_cache.notify_all()\n"
        content_str += '\t\t\t\t\tlogging.debug(f"updated ' + f'{message_name_snake_cased}' + \
                       ' with id: {' + f'{message_name_snake_cased}' + '_.id}")\n'
        content_str += f"\t\t\t\telse:\n"
        content_str += f'\t\t\t\t\tlogging.error(f"received non unique ' + f'{message_name_snake_cased}' + \
                       ', current id: "\n'
        content_str += '\t\t\t\t\t              f"{' + f'{message_name_snake_cased}' + \
                       '.id} found: {' + f'{message_name_snake_cased}' + '_.id};;;"\n'
        content_str += '\t\t\t\t\t              f"current ' + f'{message_name_snake_cased}' + \
                       ': {' + f'{message_name_snake_cased}' + '}, "\n'
        content_str += '\t\t\t\t\t              f"found ' + f'{message_name_snake_cased}' + \
                       ': {' + f'{message_name_snake_cased}' + '_} ")\n'
        return content_str

    def data_manager_model_based_handler_for_non_top_lvl_content(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        content_str = f'\tdef handle_{message_name_snake_cased}_get_all_ws(self, ' \
                      f'{message_name_snake_cased}_: {message_name}BaseModel | {message_name}, **kwargs):\n'
        content_str += "\t\twith self.strat_cache.re_ent_lock:\n"
        content_str += f"\t\t\tself.strat_cache.set_{message_name_snake_cased}({message_name_snake_cased}_)\n"
        content_str += '\t\tkwargs = {' + f'"{message_name_snake_cased}_"' + f': {message_name_snake_cased}_' + '}\n'
        content_str += f"\t\tself.underlying_handle_{message_name_snake_cased}_ws(**kwargs)\n"
        content_str += f"\t\tif self.{message_name_snake_cased}_ws_get_all_cont.notify:\n"
        content_str += f"\t\t\tself.strat_cache.notify_semaphore.release()\n"
        content_str += (f'\t\tlogging.debug(f"Updated {message_name_snake_cased} cache;;;'
                        f'{message_name_snake_cased}_: ') + '{' + f'{message_name_snake_cased}' + '_}' + '")\n'
        return content_str

    def data_manager_model_based_handler_content(self, message: protogen.Message) -> str:
        is_top_lvl = message in self.ws_manager_required_top_lvl_messages
        if is_top_lvl:
            content_str = self.data_manager_model_based_handler_for_top_lvl_content(message)
        else:
            content_str = self.data_manager_model_based_handler_for_non_top_lvl_content(message)
        return content_str

    def ws_data_manager_file_content(self, file: protogen.File) -> str:
        content_str = "# python imports\n"
        content_str += "from threading import Thread\n"
        content_str += "from typing import Callable, Type\n\n"
        content_str += "# Project imports\n"
        base_strat_cache_import_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR",
                                                                     self.base_strat_cache_file_name)
        content_str += f"from {base_strat_cache_import_path} import {self.base_strat_cache_class_name}\n"
        base_trading_cache_import_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR",
                                                                       self.base_trading_cache_file_name)
        content_str += \
            f"from {base_trading_cache_import_path} import {self.base_trading_cache_class_name}\n"
        key_handler_import_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.key_handler_file_name)
        key_handler_class_name = convert_to_capitalized_camel_case(self.key_handler_file_name)
        content_str += \
            f"from {key_handler_import_path} import {key_handler_class_name}\n"
        file_name = str(file.proto.name).split(".")[0]
        ws_client_file_name = f"{self.beanie_fastapi_model_dir_name}.{file_name}_ws_client"
        ws_client_import_path = self.import_path_from_os_path("OUTPUT_DIR",
                                                              f"{ws_client_file_name}")
        file_name_camel_cased = convert_to_capitalized_camel_case(file_name)
        content_str += f'from {ws_client_import_path} import {file_name_camel_cased}WSClient\n'

        model_file_name = f"{self.beanie_pydantic_model_dir_name}.{file_name}_model_imports"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", model_file_name)
        content_str += f'from {model_file_path} import *\n\n\n'

        file_name = str(file.proto.name).split(".")[0]
        file_name_camel_cased = convert_to_capitalized_camel_case(file_name)
        file_name_camel_cased = file_name_camel_cased[0].upper() + file_name_camel_cased[1:]
        content_str += f"class {file_name_camel_cased}DataManager({file_name_camel_cased}WSClient):\n"
        content_str += f"\tdef __init__(self, host: str, port: int, strat_cache: {self.base_strat_cache_class_name}):\n"
        content_str += f"\t\tsuper().__init__(host, port)\n"
        content_str += "\t\tself.strat_cache = strat_cache\n"
        content_str += \
            f"\t\tself.trading_cache: {self.base_trading_cache_class_name} = {self.base_trading_cache_class_name}()\n"
        for message in self.ws_manager_required_messages:
            message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
            option_dict = \
                StratExecutorPlugin.get_complex_option_value_from_proto(message,
                                                                        StratExecutorPlugin.flux_msg_executor_options)
            notify_all_option_val = option_dict.get(StratExecutorPlugin.executor_option_enable_notify_all_field)
            content_str += (f'\t\tself.{message_name_snake_cased}_ws_get_all_cont = '
                            f'self.{message_name_snake_cased}_ws_get_all_client({notify_all_option_val})\n')
        content_str += "\n"
        content_str += "\tdef __del__(self):\n"
        content_str += '\t\t"""\n'
        content_str += '\t\tideally create join-able WS thread; set exit in WS static var & ' \
                       'upon exit state detection, WS thread can\n'
        content_str += '\t\tcancel pending tasks, subsequently return to join. This helps terminate ' \
                       'the program gracefully\n'
        content_str += '\t\t"""\n\n'
        for message in self.ws_manager_required_messages:
            message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
            content_str += f'\tdef underlying_handle_{message_name_snake_cased}_ws(self, **kwargs):\n'
            content_str += f'\t\tpass\n\n'
            content_str += self.data_manager_model_based_handler_content(message)
            content_str += f"\n"
        content_str += "\n"
        return content_str

    def _get_key_method_content(self, message_name_snake_cased: str, key_seq_list: List[str], key_str: str) -> str:
        output_str = f"\t\t{key_str}: str | None = None\n"
        output_str += "\t\tif "
        for key_seq in key_seq_list:
            if key_seq[0] != "'" and key_seq[-1] != "'":
                if key_seq != key_seq_list[0]:
                    output_str += " and "
                output_str += f"{message_name_snake_cased}.{key_seq} is not None"
            if key_seq == key_seq_list[-1]:
                output_str += ":\n"
        output_str += f"\t\t\t{key_str} = "
        for key_seq in key_seq_list:
            if key_seq[0] != "'" and key_seq[-1] != "'":
                output_str += "f'{"+f"{message_name_snake_cased}.{key_seq}"+"}'"
            else:
                output_str += f"{key_seq}"
            if key_seq != key_seq_list[-1]:
                output_str += " + '_' + "
            else:
                output_str += "\n"
        return output_str

    def get_key_method_content_for_cache(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        all_executor_key_seq_list = StratExecutorPlugin.get_executor_key_sequence_list_of_model(message)
        output_str = ""
        if all_executor_key_seq_list is not None:
            if len(all_executor_key_seq_list) == 1:
                output_str += "\t@staticmethod\n"
                output_str += f"\tdef get_key_from_{message_name_snake_cased}(" \
                              f"{message_name_snake_cased}: {message_name}BaseModel) -> str | None:\n"
                output_str += self._get_key_method_content(message_name_snake_cased, all_executor_key_seq_list[-1], "key")
                output_str += "\t\t# else not required - returning None (default value of key)\n"
                output_str += "\t\treturn key\n\n"
            elif len(all_executor_key_seq_list) == 2:
                output_str += "\t@staticmethod\n"
                output_str += f"\tdef get_key_from_{message_name_snake_cased}(" \
                              f"{message_name_snake_cased}: {message_name}BaseModel) -> Tuple[str | None, str | None]:\n"
                for index, key_seq_list in enumerate(all_executor_key_seq_list):
                    output_str += self._get_key_method_content(message_name_snake_cased, key_seq_list, f"key{index+1}")
                    output_str += "\t\telse:\n"
                    output_str += f'\t\t\traise Exception(f"get_key_from_{message_name_snake_cased}: did not find ' \
                                  f'{key_seq_list};;; ' \
                                  f'{message_name_snake_cased}: '+'{'+f'{message_name_snake_cased}'+'}")\n'
                output_str += "\t\treturn "
                for key_count in range(len(all_executor_key_seq_list)):
                    output_str += f"key{key_count+1}"
                    if key_count != len(all_executor_key_seq_list)-1:
                        output_str += ", "
                    else:
                        output_str += "\n\n"
        return output_str

    def get_key_method_content_for_log(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        log_executor_key_seq_list = StratExecutorPlugin.get_log_key_sequence_list_of_model(message)
        output_str = ""
        if log_executor_key_seq_list is not None:
            output_str += "\t@staticmethod\n"
            output_str += f"\tdef get_log_key_from_{message_name_snake_cased}(" \
                          f"{message_name_snake_cased}: {message_name} | {message_name}BaseModel | " \
                          f"{message_name}Optional) -> str | None:\n"
            output_str += self._get_key_method_content(message_name_snake_cased, log_executor_key_seq_list, "key")
            output_str += "\t\t# else not required - returning None (default value of key)\n"
            output_str += "\t\treturn key\n\n"
        return output_str

    def _strat_cache_get_model_interface_content(self, message: protogen.Message,
                                                 is_repeated: bool) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

        if is_repeated:
            extra_str = "s"
            output_str = f"\tdef get_{message_name_snake_cased}(self, date_time: DateTime | None = None) -> " \
                         f"Tuple[List[{message_name}BaseModel | {message_name}], DateTime] | None:\n"
        else:
            extra_str = ""
            output_str = f"\tdef get_{message_name_snake_cased}(self, date_time: DateTime | None = None) -> " \
                         f"Tuple[{message_name}BaseModel | {message_name}, DateTime] | None:\n"
        output_str += f"\t\tif date_time is None or date_time < " \
                      f"self._{message_name_snake_cased}{extra_str}_update_date_time:\n"
        output_str += f"\t\t\tif self._{message_name_snake_cased}{extra_str} is not None:\n"
        output_str += f"\t\t\t\treturn self._{message_name_snake_cased}{extra_str}, " \
                      f"self._{message_name_snake_cased}{extra_str}_update_date_time\n"
        output_str += f"\t\t\telse:\n"
        output_str += f"\t\t\t\treturn None\n"
        output_str += f"\t\telse:\n"
        output_str += f"\t\t\treturn None\n\n"
        return output_str

    def _strat_cache_set_model_interface_content(self, message: protogen.Message, is_repeated: bool) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

        if is_repeated:
            extra_str = "s"
        else:
            extra_str = ""

        output_str = f"\tdef set_{message_name_snake_cased}(self, " \
                     f"{message_name_snake_cased}: {message_name}BaseModel | {message_name}) -> DateTime:\n"
        if is_repeated:
            output_str += f"\t\tif self._{message_name_snake_cased}{extra_str} is None:\n"
            output_str += f"\t\t\tself._{message_name_snake_cased}{extra_str} = list()\n"
            output_str += f"\t\tself._{message_name_snake_cased}{extra_str}.append({message_name_snake_cased})\n"
        else:
            output_str += f"\t\tself._{message_name_snake_cased} = {message_name_snake_cased}\n"
        output_str += f"\t\tself._{message_name_snake_cased}{extra_str}_update_date_time = DateTime.utcnow()\n"
        output_str += f"\t\treturn self._{message_name_snake_cased}{extra_str}_update_date_time\n\n"
        return output_str

    def base_strat_cache_file_content(self, file: protogen.File) -> str:
        output_str = "# primary imports\n"
        output_str += "from threading import RLock, Lock, Semaphore\n"
        output_str += "from typing import Dict, Tuple, Optional, ClassVar, List\n"
        output_str += "from pendulum import DateTime\n\n"
        output_str += "# project imports\n"
        file_name = str(file.proto.name).split(".")[0]
        model_file_name = f"{self.beanie_pydantic_model_dir_name}.{file_name}_model_imports"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", model_file_name)
        output_str += f'from {model_file_path} import *\n\n\n'
        output_str += f"class {self.base_strat_cache_class_name}:\n"
        output_str += f"\tstrat_cache_dict: Dict[str, '{self.base_strat_cache_class_name}'] = dict()\n"
        output_str += "\tadd_to_strat_cache_rlock: RLock = RLock()\n\n"
        output_str += "\tdef __init__(self):\n"
        output_str += "\t\tself.re_ent_lock: RLock = RLock()\n"
        output_str += "\t\tself.notify_semaphore = Semaphore()\n"
        output_str += "\t\tself.stopped = True  # used by consumer thread to stop processing\n\n"
        for message in self.ws_manager_required_messages:
            if message not in self.ws_manager_required_top_lvl_messages:
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                option_value_dict = \
                    StratExecutorPlugin.get_complex_option_value_from_proto(
                        message, StratExecutorPlugin.flux_msg_executor_options)
                is_repeated = option_value_dict.get(StratExecutorPlugin.executor_option_is_repeated_field)

                if is_repeated:
                    output_str += \
                        (f"\t\tself._{message_name_snake_cased}s: "
                         f"List[{message_name}BaseModel | {message_name}] | None = None\n")
                    output_str += \
                        f"\t\tself._{message_name_snake_cased}s_update_date_time: DateTime = DateTime.utcnow()\n\n"
                else:
                    output_str += (f"\t\tself._{message_name_snake_cased}: "
                                   f"{message_name}BaseModel | {message_name} | None = None\n")
                    output_str += \
                        f"\t\tself._{message_name_snake_cased}_update_date_time: DateTime = DateTime.utcnow()\n\n"

        output_str += "\t@classmethod\n"
        output_str += "\tdef notify_all(cls):\n"
        output_str += "\t\tfor strat_cache in cls.strat_cache_dict.values():\n"
        output_str += "\t\t\tstrat_cache.notify_semaphore.release()\n\n"
        output_str += "\t@classmethod\n"
        output_str += f"\tdef add(cls, key: str, strat_cache_: '{self.base_strat_cache_class_name}'):\n"
        output_str += "\t\twith cls.add_to_strat_cache_rlock:\n"
        output_str += "\t\t\tstrat_cache: cls | None = cls.strat_cache_dict.get(key)\n"
        output_str += "\t\t\tif strat_cache is None:\n"
        output_str += "\t\t\t\tcls.strat_cache_dict[key] = strat_cache_\n"
        output_str += "\t\t\telse:\n"
        output_str += '\t\t\t\terror_str: str = f"Existing StratCache found for add StratCache request, key: {key};;; ' \
                      'existing_cache: {strat_cache}, strat_cache send to add: {strat_cache_}"\n'
        output_str += "\t\t\t\tlogging.error(error_str)\n"
        output_str += "\t\t\t\traise Exception(error_str)\n\n"
        output_str += "\t@classmethod\n"
        output_str += "\tdef pop(cls, key1: str, key2: str):\n"
        output_str += "\t\twith cls.add_to_strat_cache_rlock:\n"
        output_str += "\t\t\tcls.strat_cache_dict.pop(key1)\n"
        output_str += "\t\t\tcls.strat_cache_dict.pop(key2)\n\n"
        output_str += "\t@classmethod\n"
        output_str += \
            f"\tdef get(cls, key1: str, key2: str | None = None) -> Optional['{self.base_strat_cache_class_name}']:\n"
        output_str += f"\t\tstrat_cache: cls = cls.strat_cache_dict.get(key1)\n"
        output_str += f"\t\tif strat_cache is None and key2 is not None:\n"
        output_str += f"\t\t\tstrat_cache: cls = cls.strat_cache_dict.get(key2)\n"
        output_str += f"\t\treturn strat_cache\n\n"
        output_str += f"\t@classmethod\n"
        output_str += f"\tdef guaranteed_get_by_key(cls, key1, key2) -> '{self.base_strat_cache_class_name}':\n"
        output_str += f"\t\tstrat_cache: cls = cls.get(key1)\n"
        output_str += f"\t\tif strat_cache is None:\n"
        output_str += f"\t\t\twith cls.add_to_strat_cache_rlock:\n"
        output_str += f"\t\t\t\tstrat_cache2: cls = cls.get(key2)\n"
        output_str += f"\t\t\t\tif strat_cache2 is None:  # key2 is guaranteed None, key1 maybe None\n"
        output_str += f"\t\t\t\t\tstrat_cache1: cls = cls.get(key1)\n"
        output_str += f"\t\t\t\t\tif strat_cache1 is None:  # DCLP (maybe apply SM-DCLP)  " \
                      f"# both key-1 and key-1 are none - add\n"
        output_str += f"\t\t\t\t\t\tstrat_cache = cls()\n"
        output_str += f"\t\t\t\t\t\tcls.add(key1, strat_cache)\n"
        output_str += f"\t\t\t\t\t\tcls.add(key2, strat_cache)\n"
        output_str += '\t\t\t\t\t\tlogging.info(f"Created strat_cache for key: {key1} {key2}")\n'
        output_str += '\t\t\t\t\telse:\n'
        output_str += '\t\t\t\t\t\tcls.add(key2, strat_cache1)  # add key1 found cache to key2\n'
        output_str += '\t\t\t\telse:  # key2 is has cache, key1 maybe None\n'
        output_str += '\t\t\t\t\tstrat_cache1: cls = cls.get(key1)\n'
        output_str += '\t\t\t\t\tif strat_cache1 is None:\n'
        output_str += '\t\t\t\t\t\tcls.add(key1, strat_cache2) # add key2 found cache to key1\n'
        output_str += '\t\t\t\t\t\tstrat_cache = strat_cache2\n'
        output_str += '\t\treturn strat_cache\n\n'

        for message in self.ws_manager_required_messages:

            option_value_dict = \
                StratExecutorPlugin.get_complex_option_value_from_proto(
                    message, StratExecutorPlugin.flux_msg_executor_options)
            is_repeated = option_value_dict.get(StratExecutorPlugin.executor_option_is_repeated_field)

            if message not in self.ws_manager_required_top_lvl_messages:
                output_str += self._strat_cache_get_model_interface_content(message, is_repeated)
                output_str += self._strat_cache_set_model_interface_content(message, is_repeated)

        return output_str

    def base_trading_cache_file_content(self, file: protogen.File):
        output_str = "# primary imports\n"
        output_str += "from typing import Tuple, List\n"
        output_str += "from pendulum import DateTime\n\n"
        output_str += "# project imports\n"
        file_name = str(file.proto.name).split(".")[0]
        model_file_name = f"{self.beanie_pydantic_model_dir_name}.{file_name}_model_imports"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", model_file_name)
        output_str += f'from {model_file_path} import *\n\n\n'
        trading_cache_class_name = f"{self.file_name_cap_camel_cased}BaseTradingCache"
        output_str += f"class {trading_cache_class_name}:\n\n"
        output_str += "\tdef __init__(self):\n"
        if self.ws_manager_required_top_lvl_messages:
            for message in self.ws_manager_required_messages:
                if message in self.ws_manager_required_top_lvl_messages:
                    message_name = message.proto.name
                    message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                    option_value_dict = \
                        StratExecutorPlugin.get_complex_option_value_from_proto(
                            message, StratExecutorPlugin.flux_msg_executor_options)
                    is_repeated = option_value_dict.get(StratExecutorPlugin.executor_option_is_repeated_field)

                    if is_repeated:
                        output_str += \
                            f"\t\tself._{message_name_snake_cased}s: List[{message_name}BaseModel] | None = None\n"
                        output_str += \
                            f"\t\tself._{message_name_snake_cased}s_update_date_time: DateTime = DateTime.utcnow()\n\n"
                    else:
                        output_str += f"\t\tself._{message_name_snake_cased}: {message_name}BaseModel | None = None\n"
                        output_str += \
                            f"\t\tself._{message_name_snake_cased}_update_date_time: DateTime = DateTime.utcnow()\n\n"

            for message in self.ws_manager_required_messages:
                if message in self.ws_manager_required_top_lvl_messages:

                    option_value_dict = \
                        StratExecutorPlugin.get_complex_option_value_from_proto(
                            message, StratExecutorPlugin.flux_msg_executor_options)
                    is_repeated = option_value_dict.get(StratExecutorPlugin.executor_option_is_repeated_field)

                    output_str += self._strat_cache_get_model_interface_content(message, is_repeated)
                    # output_str += self._trading_cache_set_model_interface_content(message, is_repeated)
                    output_str += self._strat_cache_set_model_interface_content(message, is_repeated)
        else:
            output_str += "\t\tpass\n"
        return output_str

    def keys_handler_file_content(self, file: protogen.File) -> str:
        output_str = "# python standard imports\n"
        output_str += "from typing import List, Tuple\n"
        file_class_name = f"{self.file_name_cap_camel_cased}KeyHandler"
        file_name = str(file.proto.name).split(".")[0]
        model_file_name = f"{self.beanie_pydantic_model_dir_name}.{file_name}_model_imports"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", model_file_name)
        output_str += f'from {model_file_path} import *\n\n\n'
        output_str += f"class {file_class_name}:\n"
        output_str += f"\tdef __init__(self):\n"
        output_str += f"\t\tpass\n\n"
        if self.get_cache_key_required_messages:
            output_str += f"\t# Get Key methods for Cache\n"
            for message in self.get_cache_key_required_messages:
                output_str += self.get_key_method_content_for_cache(message)
        if self.get_log_key_required_messages:
            output_str += f"\t# Get Key methods for Logs\n"
            for message in self.get_log_key_required_messages:
                output_str += self.get_key_method_content_for_log(message)
        return output_str

    def output_file_generate_handler(self, file: protogen.File):
        self.file_name = str(file.proto.name).split(".")[0]
        self.file_name_cap_camel_cased = convert_to_capitalized_camel_case(self.file_name)
        self.set_data_members(file)

        for dep_file in file.dependencies:
            self.set_data_members(dep_file)

        output_dict: Dict[str, str] = {
            self.ws_data_manager_file_name + f".py": self.ws_data_manager_file_content(file),
            self.base_strat_cache_file_name + f".py": self.base_strat_cache_file_content(file),
            self.key_handler_file_name + ".py": self.keys_handler_file_content(file),
            self.base_trading_cache_file_name + ".py": self.base_trading_cache_file_content(file)
        }

        return output_dict


if __name__ == "__main__":
    main(StratExecutorPlugin)
