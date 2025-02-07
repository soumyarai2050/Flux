# standard imports
import json
import os
import threading
import time
import copy
import math
import shutil
import sys
import stat
import subprocess
from typing import Set
import ctypes
import mmap
import requests

# 3rd party imports
import posix_ipc
from sqlalchemy.testing.plugin.plugin_base import logging
from filelock import FileLock

# project imports
# below import is required to symbol_cache to work - SymbolCacheContainer must import from base_plan_cache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_plan_cache import SymbolCacheContainer, SymbolCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_routes_callback_imports import (
    StreetBookServiceRoutesCallback)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    get_symbol_side_key, get_symbol_side_snapshot_log_key, all_service_up_check,
    email_book_service_http_client, get_consumable_participation_qty,
    get_plan_brief_log_key, get_new_plan_limits, get_new_plan_status,
    log_book_service_http_client, post_book_service_http_client, get_default_max_notional,
    get_default_max_open_single_leg_notional, get_default_max_net_filled_notional,
    get_simulator_config_file_path)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.executor_config_loader import ( EXECUTOR_PROJECT_DIR,
    host, EXECUTOR_PROJECT_DATA_DIR, executor_config_yaml_dict, main_config_yaml_path, EXECUTOR_PROJECT_SCRIPTS_DIR)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_book_helper import OTHER_TERMINAL_STATES, \
    NON_FILLED_TERMINAL_STATES, get_pair_plan_id_from_cmd_argv
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    compute_max_single_leg_notional, get_premium)
from FluxPythonUtils.scripts.utility_functions import (
    avg_of_new_val_sum_to_avg, find_free_port, except_n_log_alert, handle_http_response, HTTPRequestType,
    handle_refresh_configurable_data_members, set_package_logger_level, parse_to_int, YAMLConfigurationManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import (
    SecurityRecordManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.service_state import ServiceState
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    create_md_shell_script, MDShellEnvData, is_ongoing_plan, guaranteed_call_pair_plan_client,
    pair_plan_client_call_log_str, UpdateType, CURRENT_PROJECT_DIR as PAIR_STRAT_ENGINE_DIR)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.barter_simulator import (
    BarterSimulator, BarteringLinkBase)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.log_barter_simulator import LogBarterSimulator
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.plan_cache import PlanCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_key_handler import (
    EmailBookServiceKeyHandler)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_client import (
    StreetBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.aggregate import (
    get_chore_total_sum_of_last_n_sec, get_symbol_side_snapshot_from_symbol_side, get_plan_brief_from_symbol,
    get_open_chore_snapshots_for_symbol, get_symbol_overview_from_symbol, get_last_n_sec_total_barter_qty,
    get_market_depths, get_last_n_sec_first_n_last_barter)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.generated.ORMModel.post_book_service_model_imports import (
    ContactStatusUpdatesContainer)
from FluxPythonUtils.scripts.ws_reader import WSReader
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.ORMModel.photo_book_service_model_imports import (
    PlanViewBaseModel)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import (
    photo_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book import (
    StreetBook, BarteringDataManager, get_bartering_link, MarketDepth)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_book_service_routes_callback_base_native_override import BaseBookServiceRoutesCallbackBaseNativeOverride
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.StreetBook.street_book_service_key_handler import StreetBookServiceKeyHandler
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_book_helper import (
    chore_has_terminal_state)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.aggregate import get_objs_from_symbol
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.phone_book_n_street_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.dept_book_n_mobile_book_n_street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.mobile_book_n_street_book_n_basket_book_core_msgspec_model import *


class FirstLastBarterCont(MsgspecBaseModel):
    id: int | None = msgspec.field(default=None)
    first: LastBarterOptional | None = None
    last: LastBarterOptional | None = None

    @classmethod
    def dec_hook(cls, type: Type, obj: Any):
        if type == DateTime and isinstance(obj, int):
            return get_pendulum_dt_from_epoch(obj)
        else:
            return super().dec_hook(type, obj)

    @classmethod
    def enc_hook(cls, obj: Any):
        if isinstance(obj, DateTime):
            return get_epoch_from_pendulum_dt(obj)
        elif isinstance(obj, datetime.datetime):
            return get_epoch_from_standard_dt(obj)
        elif isinstance(obj, Timestamp):
            return get_epoch_from_pandas_timestamp(obj)


def get_pair_plan_id_n_recovery_info_from_cmd_argv():
    pair_plan_id = get_pair_plan_id_from_cmd_argv()

    is_crash_recovery: bool = False
    if len(sys.argv) == 4:
        try:
            is_crash_recovery = bool(parse_to_int(sys.argv[2]))
        except ValueError as e:
            err_str_ = (f"Provided cmd argument is_crash_recovery is not valid type, "
                        f"must be numeric, exception: {e}")
            logging.error(err_str_)
            raise Exception(err_str_)
    try:
        return parse_to_int(pair_plan_id), is_crash_recovery
    except ValueError as e:
        err_str_ = (f"Provided cmd argument pair_plan_id is not valid type, "
                    f"must be numeric, exception: {e}")
        logging.error(err_str_)
        raise Exception(err_str_)


class StreetBookServiceRoutesCallbackBaseNativeOverride(BaseBookServiceRoutesCallbackBaseNativeOverride,
                                                           StreetBookServiceRoutesCallback):
    KeyHandler: Type[StreetBookServiceKeyHandler] = StreetBookServiceKeyHandler
    underlying_read_plan_brief_http: Callable[..., Any] | None = None
    underlying_get_symbol_overview_from_symbol_query_http: Callable[..., Any] | None = None
    underlying_create_plan_limits_http: Callable[..., Any] | None = None
    underlying_delete_plan_limits_http: Callable[..., Any] | None = None
    underlying_create_plan_status_http: Callable[..., Any] | None = None
    underlying_update_plan_status_http: Callable[..., Any] | None = None
    underlying_get_executor_check_snapshot_query_http: Callable[..., Any] | None = None
    underlying_create_plan_brief_http: Callable[..., Any] | None = None
    underlying_read_symbol_side_snapshot_http: Callable[..., Any] | None = None
    underlying_create_symbol_side_snapshot_http: Callable[..., Any] | None = None
    underlying_partial_update_symbol_overview_http: Callable[..., Any] | None = None
    underlying_read_plan_limits_by_id_http: Callable[..., Any] | None = None
    underlying_read_symbol_overview_http: Callable[..., Any] | None = None
    underlying_get_top_of_book_from_symbol_query_http: Callable[..., Any] | None = None
    underlying_read_chore_snapshot_http: Callable[..., Any] | None = None
    underlying_get_last_n_sec_total_barter_qty_query_http: Callable[..., Any] | None = None
    underlying_partial_update_symbol_side_snapshot_http: Callable[..., Any] | None = None
    underlying_partial_update_cancel_chore_http: Callable[..., Any] | None = None
    underlying_partial_update_plan_status_http: Callable[..., Any] | None = None
    underlying_get_open_chore_count_query_http: Callable[..., Any] | None = None
    underlying_partial_update_plan_brief_http: Callable[..., Any] | None = None
    underlying_delete_symbol_side_snapshot_http: Callable[..., Any] | None = None
    underlying_read_last_barter_http: Callable[..., Any] | None = None
    underlying_is_plan_ongoing_query_http: Callable[..., Any] | None = None
    underlying_delete_plan_brief_http: Callable[..., Any] | None = None
    underlying_create_cancel_chore_http: Callable[..., Any] | None = None
    underlying_read_market_depth_http: Callable[..., Any] | None = None
    underlying_read_plan_status_http: Callable[..., Any] | None = None
    underlying_read_plan_status_by_id_http: Callable[..., Any] | None = None
    underlying_read_cancel_chore_http: Callable[..., Any] | None = None
    underlying_read_plan_limits_http: Callable[..., Any] | None = None
    underlying_delete_plan_status_http: Callable[..., Any] | None = None
    underlying_barter_simulator_place_cxl_chore_query_http: Callable[..., Any] | None = None
    underlying_create_chore_journal_http: Callable[..., Any] | None = None
    underlying_create_fills_journal_http: Callable[..., Any] | None = None

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_routes_imports import (
            underlying_read_plan_brief_http, underlying_get_symbol_overview_from_symbol_query_http,
            residual_compute_shared_lock, journal_shared_lock,
            underlying_create_plan_limits_http, underlying_delete_plan_limits_http,
            underlying_create_plan_status_http, underlying_update_plan_status_http,
            underlying_get_executor_check_snapshot_query_http, underlying_create_plan_brief_http,
            underlying_read_symbol_side_snapshot_http, underlying_create_symbol_side_snapshot_http,
            underlying_partial_update_symbol_overview_http, underlying_read_plan_limits_by_id_http,
            underlying_read_symbol_overview_http, underlying_create_cancel_chore_http,
            underlying_read_top_of_book_http, underlying_get_top_of_book_from_symbol_query_http,
            underlying_read_chore_snapshot_http, underlying_read_chore_journal_http,
            underlying_get_last_n_sec_total_barter_qty_query_http, underlying_partial_update_cancel_chore_http,
            get_underlying_account_cumulative_fill_qty_query_http, underlying_create_chore_snapshot_http,
            underlying_update_chore_snapshot_http, underlying_partial_update_symbol_side_snapshot_http,
            underlying_partial_update_plan_status_http, underlying_get_open_chore_count_query_http,
            underlying_partial_update_plan_brief_http, underlying_delete_symbol_side_snapshot_http,
            underlying_read_fills_journal_http,
            underlying_read_last_barter_http, underlying_create_chore_journal_http,
            underlying_delete_plan_brief_http, underlying_read_market_depth_http, underlying_read_plan_status_http,
            underlying_read_plan_status_by_id_http, underlying_read_cancel_chore_http,
            underlying_read_plan_limits_http, underlying_delete_plan_status_http,
            underlying_barter_simulator_place_cxl_chore_query_http, underlying_create_fills_journal_http,
            underlying_read_symbol_overview_by_id_http,
            underlying_get_symbol_side_underlying_account_cumulative_fill_qty_query_http)

        cls.residual_compute_shared_lock = residual_compute_shared_lock
        cls.journal_shared_lock = journal_shared_lock
        cls.underlying_read_plan_brief_http = underlying_read_plan_brief_http
        cls.underlying_get_symbol_overview_from_symbol_query_http = (
            underlying_get_symbol_overview_from_symbol_query_http)
        cls.underlying_create_plan_limits_http = underlying_create_plan_limits_http
        cls.underlying_delete_plan_limits_http = underlying_delete_plan_limits_http
        cls.underlying_create_plan_status_http = underlying_create_plan_status_http
        cls.underlying_update_plan_status_http = underlying_update_plan_status_http
        cls.underlying_get_executor_check_snapshot_query_http = underlying_get_executor_check_snapshot_query_http
        cls.underlying_create_plan_brief_http = underlying_create_plan_brief_http
        cls.underlying_read_symbol_side_snapshot_http = underlying_read_symbol_side_snapshot_http
        cls.underlying_create_symbol_side_snapshot_http = underlying_create_symbol_side_snapshot_http
        cls.underlying_partial_update_symbol_overview_http = underlying_partial_update_symbol_overview_http
        cls.underlying_read_plan_limits_by_id_http = underlying_read_plan_limits_by_id_http
        cls.underlying_read_symbol_overview_http = underlying_read_symbol_overview_http
        cls.underlying_read_symbol_overview_by_id_http = underlying_read_symbol_overview_by_id_http
        cls.underlying_read_top_of_book_http = underlying_read_top_of_book_http
        cls.underlying_get_top_of_book_from_symbol_query_http = underlying_get_top_of_book_from_symbol_query_http
        cls.underlying_read_chore_snapshot_http = underlying_read_chore_snapshot_http
        cls.underlying_read_chore_journal_http = underlying_read_chore_journal_http
        cls.underlying_get_last_n_sec_total_barter_qty_query_http = underlying_get_last_n_sec_total_barter_qty_query_http
        cls.get_underlying_account_cumulative_fill_qty_query_http = (
            get_underlying_account_cumulative_fill_qty_query_http)
        cls.underlying_create_chore_snapshot_http = underlying_create_chore_snapshot_http
        cls.underlying_update_chore_snapshot_http = underlying_update_chore_snapshot_http
        cls.underlying_partial_update_symbol_side_snapshot_http = underlying_partial_update_symbol_side_snapshot_http
        cls.underlying_partial_update_cancel_chore_http = underlying_partial_update_cancel_chore_http
        cls.underlying_partial_update_plan_status_http = underlying_partial_update_plan_status_http
        cls.underlying_get_open_chore_count_query_http = underlying_get_open_chore_count_query_http
        cls.underlying_partial_update_plan_brief_http = underlying_partial_update_plan_brief_http
        cls.underlying_delete_symbol_side_snapshot_http = underlying_delete_symbol_side_snapshot_http
        cls.underlying_get_symbol_side_underlying_account_cumulative_fill_qty_query_http = (
            underlying_get_symbol_side_underlying_account_cumulative_fill_qty_query_http)
        cls.underlying_read_fills_journal_http = underlying_read_fills_journal_http
        cls.underlying_read_last_barter_http = underlying_read_last_barter_http
        cls.underlying_delete_plan_brief_http = underlying_delete_plan_brief_http
        cls.underlying_create_cancel_chore_http = underlying_create_cancel_chore_http
        cls.underlying_read_market_depth_http = underlying_read_market_depth_http
        cls.underlying_read_plan_status_http = underlying_read_plan_status_http
        cls.underlying_read_plan_status_by_id_http = underlying_read_plan_status_by_id_http
        cls.underlying_read_cancel_chore_http = underlying_read_cancel_chore_http
        cls.underlying_read_plan_limits_http = underlying_read_plan_limits_http
        cls.underlying_delete_plan_status_http = underlying_delete_plan_status_http
        cls.underlying_barter_simulator_place_cxl_chore_query_http = (
            underlying_barter_simulator_place_cxl_chore_query_http)
        cls.underlying_create_chore_journal_http = underlying_create_chore_journal_http
        cls.underlying_create_fills_journal_http = underlying_create_fills_journal_http

    def __init__(self):
        pair_plan_id, is_crash_recovery = get_pair_plan_id_n_recovery_info_from_cmd_argv()
        self.pair_plan_id = pair_plan_id
        self.is_crash_recovery = is_crash_recovery
        super().__init__()      # super init needs pair_plan_id in set_log_simulator_file_name_n_path
        self.orig_intra_day_bot: int | None = None
        self.orig_intra_day_sld: int | None = None
        # since this init is called before db_init
        self.db_name: str = f"street_book_{self.pair_plan_id}"
        os.environ["DB_NAME"] = self.db_name
        self.plan_leg_1: PlanLeg | None = None  # will be set by once all_service_up test passes
        self.plan_leg_2: PlanLeg | None = None  # will be set by once all_service_up test passes
        self.leg1_symbol_cache: SymbolCache | None = None  # will be set by once all_service_up test passes
        self.leg2_symbol_cache: SymbolCache | None = None  # will be set by once all_service_up test passes
        # restricted variable: don't overuse this will be extended to multi-currency support
        self.port: int | None = None  # will be set by app_launch_pre
        self.updated_simulator_config_file = False
        self.web_client = None
        self.project_config_yaml_path = main_config_yaml_path
        self.mobile_book_swagger_ui_json_path = (EXECUTOR_PROJECT_DIR.parent / "mobile_book" /
                                                 "generated" / "CppSwggerUiJson" / "mobile_book_swagger.json")
        self.executor_config_yaml_dict = executor_config_yaml_dict
        self.config_yaml_last_modified_timestamp = os.path.getmtime(self.project_config_yaml_path)
        self.total_barter_qty_by_aggregated_window_first_n_lst_barters: bool = (
            executor_config_yaml_dict.get("total_barter_qty_by_aggregated_window_first_n_lst_barters"))
        self.min_refresh_interval: int = parse_to_int(executor_config_yaml_dict.get("min_refresh_interval"))
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        self.exch_to_market_depth_lvl_dict = executor_config_yaml_dict.get("exch_to_market_depth_lvl", {})
        self.ports_cache_file_path: PurePath | None = EXECUTOR_PROJECT_DATA_DIR / "ports_cache_file.txt"
        self.ports_cache_lock_file_path: PurePath | None = EXECUTOR_PROJECT_DATA_DIR / "ports_cache_lock_file.txt.lock"
        self.cpp_port: int | None = None

    def set_log_simulator_file_name_n_path(self):
        self.simulate_config_yaml_file_path = (get_simulator_config_file_path(self.pair_plan_id))
        self.log_dir_path = PurePath(__file__).parent.parent / "log"
        self.log_simulator_file_name = f"log_simulator_{self.pair_plan_id}_logs_{self.datetime_fmt_str}.log"
        self.log_simulator_file_path = (PurePath(__file__).parent.parent / "log" /
                                        f"log_simulator_{self.pair_plan_id}_logs_{self.datetime_fmt_str}.log")

    @property
    def derived_class_type(self):
        return StreetBookServiceRoutesCallbackBaseNativeOverride

    ##################
    # Start-Up Methods
    ##################

    def get_pair_plan_loaded_plan_cache(self, pair_plan):
        key_leg_1, key_leg_2 = EmailBookServiceKeyHandler.get_key_from_pair_plan(pair_plan)
        plan_cache: PlanCache = PlanCache.guaranteed_get_by_key(key_leg_1, key_leg_2)
        with plan_cache.re_ent_lock:
            plan_cache.set_pair_plan(pair_plan)
        return plan_cache

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up, then create contact limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair plans at startup/re-start
        """
        plan_key: str | None = None
        service_up_no_warn_retry: int = 5
        try:
            error_prefix = "_app_launch_pre_thread_func: "
            static_data_service_state: ServiceState = ServiceState(
                error_prefix=error_prefix + "static_data_service failed, exception: ")
            symbol_overview_for_symbol_exists: bool = False
            should_sleep: bool = False
            while True:
                if self.plan_cache and not plan_key:
                    plan_key = self.plan_cache.get_key()
                if should_sleep:
                    time.sleep(self.min_refresh_interval)
                service_up_flag_env_var = os.environ.get(f"street_book_{self.port}")

                if service_up_flag_env_var == "1":
                    # validate essential services are up, if so, set service ready state to true
                    # static data and md service are considered essential
                    if (self.all_services_up and static_data_service_state.ready and
                            self.usd_fx is not None and symbol_overview_for_symbol_exists and
                            self.bartering_data_manager is not None):
                        if not self.service_ready:
                            self.service_ready = True
                            # creating required models for this plan
                            try:
                                if not self._check_n_create_related_models_for_plan():  # throws if SO close px missing
                                    self.service_ready = False
                                else:
                                    logging.debug(f"Service Marked Ready for: {plan_key}")
                            except Exception as exp:
                                logging.exception(f"_check_n_create_related_models_for_plan failed with {exp=}; making"
                                                  f" self.service_ready=False")
                                self.service_ready = False
                    else:
                        warn: str = (f"plan executor service is not up yet for {plan_key};;;{self.all_services_up=}, "
                                     f"{static_data_service_state.ready=}, {self.usd_fx=}, "
                                     f"{symbol_overview_for_symbol_exists=}, {self.bartering_data_manager=}")
                        if service_up_no_warn_retry <= 0:
                            logging.warning(warn)
                        else:
                            logging.debug(f"{service_up_no_warn_retry=}, {warn}")
                            service_up_no_warn_retry -= 1
                    if not self.all_services_up:
                        try:
                            if all_service_up_check(self.web_client):
                                # starting bartering_data_manager and street_book
                                try:
                                    pair_plan = email_book_service_http_client.get_pair_plan_client(
                                        self.pair_plan_id)
                                except Exception as exp:
                                    logging.exception(f"get_pair_plan_client failed for {plan_key};;; {exp=}")
                                    continue

                                self.plan_leg_1 = pair_plan.pair_plan_params.plan_leg1
                                self.plan_leg_2 = pair_plan.pair_plan_params.plan_leg2

                                # creating config file for this server run if not exists
                                code_gen_projects_dir = PurePath(__file__).parent.parent.parent.parent
                                temp_config_file_path = (code_gen_projects_dir / "template_yaml_configs" /
                                                         "server_config.yaml")
                                dest_config_file_path = self.simulate_config_yaml_file_path
                                shutil.copy(temp_config_file_path, dest_config_file_path)

                                # setting simulate_config_file_name
                                BarteringLinkBase.simulate_config_yaml_path = self.simulate_config_yaml_file_path
                                LogBarterSimulator.executor_port = self.port
                                BarteringLinkBase.reload_executor_configs()

                                # setting partial_run to True and assigning port to pair_plan
                                pair_plan.port = self.port
                                pair_plan.server_ready_state = 1   # indicates to ui - executor server has started

                                try:
                                    updated_pair_plan = email_book_service_http_client.put_pair_plan_client(pair_plan)
                                except Exception as exp:
                                    logging.exception(f"put_pair_plan_client failed for {plan_key};;;"
                                                      f"{exp=}, {pair_plan=}")
                                    continue
                                else:
                                    self.leg1_symbol_cache = (
                                        SymbolCacheContainer.add_symbol_cache_for_symbol(self.plan_leg_1.sec.sec_id))
                                    self.leg2_symbol_cache = (
                                        SymbolCacheContainer.add_symbol_cache_for_symbol(self.plan_leg_2.sec.sec_id))

                                    logging.info(f"Creating bartering_data_manager for {plan_key=}")
                                    self.plan_cache: PlanCache = self.get_pair_plan_loaded_plan_cache(
                                        updated_pair_plan)
                                    # Setting asyncio_loop for StreetBook
                                    StreetBook.asyncio_loop = self.asyncio_loop
                                    BarteringDataManager.asyncio_loop = self.asyncio_loop
                                    self.bartering_data_manager = BarteringDataManager(StreetBook.executor_trigger,
                                                                                   self.plan_cache)
                                    logging.debug(f"Created bartering_data_manager for {plan_key=};;;{pair_plan=}")
                                logging.debug(f"Marked pair_plan.server_ready_state to 1 for {plan_key=}")

                                self.all_services_up = True
                                logging.debug(f"Marked all_services_up True for {plan_key=}")
                                should_sleep = False
                            else:
                                should_sleep = True
                        except Exception as exp:
                            logging.error(f"unexpected: all_service_up_check threw exception for {plan_key=}, "
                                          f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                          f";;;{exp=}", exc_info=True)
                    else:
                        should_sleep = True
                        # any periodic refresh code goes here
                        if self.usd_fx is None:
                            try:
                                if not self.update_fx_symbol_overview_dict_from_http():
                                    logging.error(f"Can't find any symbol_overview with {PlanCache.usd_fx_symbol=};"
                                                  f"for {plan_key=}, retrying in next periodic cycle")
                            except Exception as exp:
                                logging.exception(f"update_fx_symbol_overview_dict_from_http failed for {plan_key=} "
                                                  f"with exception: {exp=}")

                        # service loop: manage all sub-services within their private try-catch to allow high level
                        # service to remain partially operational even if some sub-service is not available for any reason
                        if not static_data_service_state.ready:
                            try:
                                self.static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)
                                if self.static_data is not None:
                                    # creating and running so_shell script
                                    pair_plan = self.plan_cache.get_pair_plan_obj()
                                    self.create_n_run_so_shell_script(pair_plan)
                                    static_data_service_state.ready = True
                                    logging.debug(
                                        f"Marked static_data_service_state.ready True for {plan_key=}")
                                    # we just got static data - no need to sleep - force no sleep
                                    should_sleep = False
                                else:
                                    raise Exception(
                                        f"self.static_data did init to None for {plan_key=}, unexpected!!")
                            except Exception as exp:
                                static_data_service_state.handle_exception(exp)
                        else:
                            # refresh static data periodically (maybe more in future)
                            try:
                                self.static_data_periodic_refresh()
                            except Exception as exp:
                                static_data_service_state.handle_exception(exp)
                                static_data_service_state.ready = False  # forces re-init in next iteration

                        if not symbol_overview_for_symbol_exists:
                            # updating symbol_overviews
                            leg1_symbol_overview = self.leg1_symbol_cache.so
                            leg2_symbol_overview = self.leg2_symbol_cache.so
                            if leg1_symbol_overview is not None and leg2_symbol_overview is not None:
                                symbol_overview_for_symbol_exists = True
                            else:
                                run_coro = (
                                    StreetBookServiceRoutesCallbackBaseNativeOverride.
                                    underlying_read_symbol_overview_http())
                                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

                                # block for task to finish
                                try:
                                    symbol_overview_list = future.result()
                                except Exception as e:
                                    logging.exception(f"underlying_read_symbol_overview_http "
                                                      f"failed for {plan_key=} with exception: {e}")
                                else:
                                    for symbol_overview in symbol_overview_list:
                                        # updating symbol_cache
                                        self.plan_cache.handle_set_symbol_overview_in_symbol_cache(symbol_overview)

                                leg1_symbol_overview = self.leg1_symbol_cache.so
                                leg2_symbol_overview = self.leg2_symbol_cache.so
                                if leg1_symbol_overview is not None and leg2_symbol_overview is not None:
                                    symbol_overview_for_symbol_exists = True
                                else:
                                    symbol_overview_for_symbol_exists = False

                        # Reconnecting lost ws connections in WSReader
                        for ws_cont in WSReader.ws_cont_list:
                            if ws_cont.force_disconnected and not ws_cont.expired:
                                new_ws_cont = WSReader(ws_cont.uri, ws_cont.ModelClassType,
                                                       ws_cont.ModelClassTypeList, ws_cont.callback)
                                new_ws_cont.new_register_to_run()
                                ws_cont.expired = True

                        if self.service_ready:
                            try:
                                # Gets all open chores, updates residuals and raises pause to plan if req
                                run_coro = self.cxl_expired_open_chores()
                                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

                                # block for task to finish
                                try:
                                    future.result()
                                except Exception as exp:
                                    logging.exception(f"cxl_expired_open_chores failed for {plan_key=} with "
                                                      f"{exp=}")

                            except Exception as exp:
                                logging.exception(f"periodic open chore check failed for {plan_key=}, periodic chore "
                                                  f"state checks will not be honored and retried in next periodic cycle"
                                                  f";;;{exp=}")

                            if self.bartering_data_manager and self.bartering_data_manager.street_book_thread and not \
                                    self.bartering_data_manager.street_book_thread.is_alive():
                                self.bartering_data_manager.street_book_thread.join(timeout=20)
                                logging.warning(f"street_book_thread is not alive anymore - returning from "
                                                f"_app_launch_pre_thread_func for {plan_key=} executor {self.port=}")
                                return

                        # Updating data-members synced with config file update
                        last_modified_timestamp = os.path.getmtime(main_config_yaml_path)
                        if self.config_yaml_last_modified_timestamp != last_modified_timestamp:
                            self.config_yaml_last_modified_timestamp = last_modified_timestamp

                            handle_refresh_configurable_data_members(self, self.config_key_to_data_member_name_dict,
                                                                     str(main_config_yaml_path))
                else:
                    should_sleep = True
        except Exception as e:
            error_str = (f"unexpected! _app_launch_pre_thread_func caught outer exception: {e}, for {plan_key=}; "
                         f"executor {self.port=}, thread going down;;;")
            logging.exception(error_str)
        finally:
            logging.warning(f"_app_launch_pre_thread_func, thread going down, for {plan_key=} executor "
                            f"{self.port=}")

    def get_free_port_for_md(self) -> int:
        # must be called after taking file lock
        while True:
            port_ = find_free_port()
            if os.path.exists(self.ports_cache_file_path):
                with open(self.ports_cache_file_path, "r") as f:
                    ports = f.readlines()
                    if str(port_) + '\n' in ports:      # each port is string with '\n' at the end in ports list
                        continue    # finding port again if port already used in some other plan
                    # else not required: all good - new port found

                with open(self.ports_cache_file_path, "a") as f:
                    f.write(str(port_) + "\n")
                    return port_

            else:
                with open(str(self.ports_cache_file_path), 'w') as f:
                    f.write(str(port_) + "\n")
                    return port_

    def update_simulate_config_yaml(self, pair_plan: PairPlan):
        if not self.updated_simulator_config_file:
            mongo_server = executor_config_yaml_dict.get("mongo_server")

            simulate_config_yaml_file_data = YAMLConfigurationManager.load_yaml_configurations(
                self.simulate_config_yaml_file_path, load_as_str=True)
            with FileLock(self.ports_cache_lock_file_path):
                self.cpp_port = self.get_free_port_for_md()
            simulate_config_yaml_file_data += "\n\n"
            simulate_config_yaml_file_data += f"leg_1_symbol: {self.plan_leg_1.sec.sec_id}\n"
            simulate_config_yaml_file_data += f"leg_1_feed_code: {self.plan_leg_1.exch_id}\n"
            simulate_config_yaml_file_data += f"leg_2_symbol: {self.plan_leg_2.sec.sec_id}\n"
            simulate_config_yaml_file_data += f"leg_2_feed_code: {self.plan_leg_2.exch_id}\n\n"
            simulate_config_yaml_file_data += f"mongo_server: {mongo_server}\n"
            simulate_config_yaml_file_data += f"http_ip: 127.0.0.1\n"
            simulate_config_yaml_file_data += f"swagger_ui_json_path: {str(self.mobile_book_swagger_ui_json_path)}\n"
            simulate_config_yaml_file_data += f"market_depth_level: {self.exch_to_market_depth_lvl_dict.get(self.plan_leg_1.exch_id)}\n"
            simulate_config_yaml_file_data += f"db_name: {self.db_name}\n\n"

            # Note: Publish policy
            # 0: None(cpp will not perform that particular operation on which it is set),
            # 1: Pre(cpp will perform that operation in main thread and then returns the control back),
            # 2: Post(cpp starts new thread and returns control back immediately,
            #    operation on which it is set is handled by the different thread)
            if not executor_config_yaml_dict.get("avoid_cpp_ws_update"):
                simulate_config_yaml_file_data += f"cpp_http_port: {self.cpp_port}\n"
                simulate_config_yaml_file_data += f"market_depth_ws_update_publish_policy: 2\n"
                simulate_config_yaml_file_data += f"top_of_book_ws_update_publish_policy: 2\n"
                simulate_config_yaml_file_data += f"last_barter_ws_update_publish_policy: 2\n"
                simulate_config_yaml_file_data += f"websocket_timeout: 300\n"

            if not executor_config_yaml_dict.get("avoid_cpp_shm_update"):
                simulate_config_yaml_file_data += f"cpp_shm_update_publish_policy: 1\n"

            if not executor_config_yaml_dict.get("avoid_cpp_db_update"):
                simulate_config_yaml_file_data += f"market_depth_db_update_publish_policy: 2\n"
                simulate_config_yaml_file_data += f"top_of_book_db_update_publish_policy: 2\n"
                simulate_config_yaml_file_data += f"last_barter_db_update_publish_policy: 2\n"

            if not executor_config_yaml_dict.get("avoid_cpp_http_update"):
                simulate_config_yaml_file_data += "project_name: street_book\n"
                simulate_config_yaml_file_data += "http_ip: 127.0.0.1\n"
                simulate_config_yaml_file_data += f"http_port: {self.port}\n"
                simulate_config_yaml_file_data += f"market_depth_http_update_publish_policy: 1\n"
                simulate_config_yaml_file_data += f"top_of_book_http_update_publish_policy: 1\n"
                simulate_config_yaml_file_data += f"last_barter_http_update_publish_policy: 1\n"

            YAMLConfigurationManager.update_yaml_configurations(
                simulate_config_yaml_file_data, str(self.simulate_config_yaml_file_path))
            os.environ["simulate_config_yaml_file"] = str(self.simulate_config_yaml_file_path)

            BarteringLinkBase.reload_executor_configs()

            # Setting MobileBookCache instances for this symbol pair
            pair_plan.cpp_port = self.cpp_port

            self.updated_simulator_config_file = True   # setting it true avoid updating config file again

    def app_launch_pre(self):
        StreetBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_routes()
        # to be called only after logger is initialized - to prevent getting overridden
        set_package_logger_level("filelock", logging.WARNING)
        if self.market.is_test_run:
            LogBarterSimulator.chore_create_async_callable = (
                StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_chore_journal_http)
            LogBarterSimulator.fill_create_async_callable = (
                StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_fills_journal_http)
            BarterSimulator.chore_create_async_callable = (
                StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_chore_journal_http)
            BarterSimulator.fill_create_async_callable = (
                StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_fills_journal_http)

        self.port = find_free_port()
        self.web_client = StreetBookServiceHttpClient.set_or_get_if_instance_exists(host, self.port)

        app_launch_pre_thread = threading.Thread(target=self._app_launch_pre_thread_func,
                                                 name="_app_launch_pre_thread_func", daemon=True)
        app_launch_pre_thread.start()
        logging.debug(f"Triggered server launch pre override for executor {self.port=}")

    def app_launch_post(self):
        logging.debug(f"Triggered server launch post override for executor {self.port=}")

        # making pair_plan server_ready_state field to 0
        try:
            # email_book_service_http_client.update_pair_plan_to_non_running_state_query_client(self.pair_plan_id)
            guaranteed_call_pair_plan_client(
                None, email_book_service_http_client.update_pair_plan_to_non_running_state_query_client,
                pair_plan_id=self.pair_plan_id)
        except Exception as e:
            if ('{"detail":"Id not Found: PairPlan ' + f'{self.pair_plan_id}' + '"}') in str(e):
                err_str_ = ("error occurred since pair_plan object got deleted, therefore can't update "
                            "is_running_state, symbol_side_key: "
                            f"{get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])}")
                logging.debug(err_str_)
            else:
                logging.exception(f"Some error occurred while updating is_running state of {self.pair_plan_id=} "
                                  f"while shutting executor server, symbol_side_key: "
                                  f"{get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])}, "
                                  f"{e=}")
        finally:
            # removing md scripts
            try:
                so_file_path = EXECUTOR_PROJECT_SCRIPTS_DIR / f"ps_id_{self.pair_plan_id}_so.sh"
                if os.path.exists(so_file_path):
                    os.remove(so_file_path)
            except Exception as e:
                err_str_ = f"Something went wrong while deleting so shell script, exception: {e}"
                logging.exception(err_str_)


    @staticmethod
    def create_n_run_so_shell_script(pair_plan):
        # creating run_symbol_overview.sh file
        run_symbol_overview_file_path = EXECUTOR_PROJECT_SCRIPTS_DIR / f"ps_id_{pair_plan.id}_so.sh"

        subscription_data = \
            [
                (pair_plan.pair_plan_params.plan_leg1.sec.sec_id,
                 str(pair_plan.pair_plan_params.plan_leg1.sec.sec_id_source)),
                (pair_plan.pair_plan_params.plan_leg2.sec.sec_id,
                 str(pair_plan.pair_plan_params.plan_leg2.sec.sec_id_source))
            ]
        db_name = os.environ["DB_NAME"]
        exch_code = "SS" if pair_plan.pair_plan_params.plan_leg1.exch_id == "SSE" else "SZ"

        md_shell_env_data: MDShellEnvData = (
            MDShellEnvData(subscription_data=subscription_data, host=pair_plan.host,
                           port=pair_plan.port, db_name=db_name, exch_code=exch_code,
                           project_name="street_book"))

        create_md_shell_script(md_shell_env_data, run_symbol_overview_file_path, "SO",
                               instance_id=str(pair_plan.id))
        os.chmod(run_symbol_overview_file_path, stat.S_IRWXU)
        subprocess.Popen([f"{run_symbol_overview_file_path}"])

    async def _compute_n_update_max_notionals(self, stored_plan_limits_obj: PlanLimits,
                                              updated_plan_limits_obj: PlanLimits,
                                              stored_plan_status_obj: PlanStatus) -> bool:
        ret_val = False
        symbol: str = self.plan_leg_1.sec.sec_id
        side: Side = self.plan_leg_1.side
        cb_symbol: str = self.plan_leg_1.sec.sec_id
        eqt_symbol: str = self.plan_leg_2.sec.sec_id
        cb_close_px: float | None = None
        eqt_close_px: float | None = None
        symbol_overview_list: List[SymbolOverview] = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_overview_http()
        symbol_overview: SymbolOverview
        for symbol_overview in symbol_overview_list:
            if symbol_overview.symbol == cb_symbol:
                cb_close_px = symbol_overview.closing_px
            else:
                eqt_close_px = symbol_overview.closing_px
        # send None for self.orig_intra_day_bot/sld to force re-compute intraday based on current bot/sld snapshot
        # 1st time at process start self.orig_intra_day_bot/sld is None to force compute
        computed_max_single_leg_notional, self.orig_intra_day_bot, self.orig_intra_day_sld = \
            compute_max_single_leg_notional(self.static_data, updated_plan_limits_obj.eligible_brokers, cb_symbol,
                                            eqt_symbol, side, self.usd_fx, cb_close_px, eqt_close_px,
                                            self.orig_intra_day_bot, self.orig_intra_day_sld)
        if math.isclose(computed_max_single_leg_notional, updated_plan_limits_obj.max_single_leg_notional) and \
                math.isclose(computed_max_single_leg_notional, stored_plan_limits_obj.max_single_leg_notional):
            return False  # no action as no change
        if get_default_max_notional() < computed_max_single_leg_notional:
            # not allowed to go above default max CB Notional
            logging.warning(f"blocked assignment of computed CB notional: {computed_max_single_leg_notional:,} as it "
                            f"breaches default max_single_leg_notional: {get_default_max_notional():,}, setting to "
                            f"default max_single_leg_notional instead, symbol_side_key: "
                            f"{get_symbol_side_key([(symbol, side)])}")
            computed_max_single_leg_notional = get_default_max_notional()

        acquired_notional: float = (stored_plan_limits_obj.max_single_leg_notional -
                                    stored_plan_status_obj.balance_notional)
        # check for user assigned max_single_leg_notional
        if not math.isclose(stored_plan_limits_obj.max_single_leg_notional,
                            updated_plan_limits_obj.max_single_leg_notional):
            if computed_max_single_leg_notional > updated_plan_limits_obj.max_single_leg_notional:
                computed_max_single_leg_notional = updated_plan_limits_obj.max_single_leg_notional
            else:
                logging.warning(
                    f"blocked assignment of UI input CB notional: {updated_plan_limits_obj.max_single_leg_notional:,}"
                    f" as it breaches available computed max_single_leg_notional: {computed_max_single_leg_notional:,},"
                    f" setting to computed_max_single_leg_notional instead, symbol_side_key: "
                    f"{get_symbol_side_key([(symbol, side)])}")

        # warn if computed max cb notional > .5% current max cb notional [else not an alert-worthy change: log info]
        if (computed_max_single_leg_notional > updated_plan_limits_obj.max_single_leg_notional and
                 not math.isclose(computed_max_single_leg_notional, updated_plan_limits_obj.max_single_leg_notional)):
            warn_str_: str = (f"increased computed max_single_leg_notional to: {computed_max_single_leg_notional:,}, "
                              f"note: this exceeds older max_single_leg_notional: "
                              f"{updated_plan_limits_obj.max_single_leg_notional:,}, for symbol_side: "
                              f"{get_symbol_side_key([(symbol, side)])}")
            if (abs(computed_max_single_leg_notional - updated_plan_limits_obj.max_open_single_leg_notional) >
                    (0.005 * updated_plan_limits_obj.max_single_leg_notional)):
                logging.warning(warn_str_)
            else:
                logging.info(warn_str_)

        balance_notional: float = computed_max_single_leg_notional - acquired_notional
        updated_plan_status_obj = PlanStatusOptional(id=stored_plan_status_obj.id, balance_notional=balance_notional)
        # collect pair_plan_tuple before marking it done (for today) - update plan status balance notional
        pair_plan_tuple = self.plan_cache.get_pair_plan()
        await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_plan_status_http(
            updated_plan_status_obj.to_json_dict(excclude_none=True))
        if balance_notional < 0 or math.isclose(balance_notional, 0):
            if pair_plan_tuple is not None:
                pair_plan, _ = pair_plan_tuple
                if is_ongoing_plan(pair_plan):
                    updated_pair_plan_obj: PairPlanBaseModel = \
                        PairPlanBaseModel(id=pair_plan.id, plan_state=PlanState.PlanState_PAUSED)
                    email_book_service_http_client.patch_pair_plan_client(
                        updated_pair_plan_obj.to_json_dict(exclude_none=True))
                    logging.critical(f"pausing plan! new computed {balance_notional=} found <= 0; "
                                     f"as current {acquired_notional=:,} >= new "
                                     f"{computed_max_single_leg_notional=:,};;;old balance_notional: "
                                     f"{stored_plan_status_obj.balance_notional:,} old max_single_leg_notional: "
                                     f"{stored_plan_limits_obj.max_single_leg_notional:,} "
                                     f"for symbol-side: {get_symbol_side_key([(symbol, side)])}")
                # else not required - not an ongoing plan
            else:
                err_str_ = ("Unexpected: Can't find pair_plan object in plan_cache - can't update "
                            "plan_state to PlanState_PAUSED")
                logging.error(err_str_)

        # now update max_single_leg_notional
        if not math.isclose(computed_max_single_leg_notional, stored_plan_limits_obj.max_single_leg_notional):
            updated_plan_limits_obj.max_single_leg_notional = computed_max_single_leg_notional
            ret_val = True
        else:
            updated_plan_limits_obj.max_single_leg_notional = stored_plan_limits_obj.max_single_leg_notional

        # max_open_single_leg_notional
        computed_max_open_single_leg_notional = computed_max_single_leg_notional
        if get_default_max_open_single_leg_notional() < computed_max_open_single_leg_notional:
            # not allowed to go above default max_open_single_leg_notional
            logging.warning(f"blocked assignment of {computed_max_open_single_leg_notional=:,} as it breaches "
                            f"default max_open_single_leg_notional: {get_default_max_open_single_leg_notional():,}, "
                            f"setting to default max_open_single_leg_notional "
                            f"instead, symbol_side_key: {get_symbol_side_key([(symbol, side)])}")
            computed_max_open_single_leg_notional = get_default_max_open_single_leg_notional()

        # check for user assigned max_open_single_leg_notional
        if not math.isclose(stored_plan_limits_obj.max_open_single_leg_notional,
                            updated_plan_limits_obj.max_open_single_leg_notional):
            if computed_max_open_single_leg_notional > updated_plan_limits_obj.max_open_single_leg_notional:
                computed_max_open_single_leg_notional = updated_plan_limits_obj.max_open_single_leg_notional
            else:
                logging.warning(
                    f"blocked assignment of user desired {updated_plan_limits_obj.max_open_single_leg_notional=:,.0f}"
                    f" as it breaches available {computed_max_open_single_leg_notional=:,}, setting to "
                    f"computed_max_open_single_leg_notional instead, "
                    f"symbol_side_key: {get_symbol_side_key([(symbol, side)])}")

        # max_net_filled_notional
        computed_max_net_filled_notional = computed_max_single_leg_notional
        if get_default_max_net_filled_notional() < computed_max_net_filled_notional:
            # not allowed to go above default max_net_filled_notional
            logging.warning(f"blocked assignment of {computed_max_net_filled_notional=:,} as it breaches "
                            f"default max_net_filled_notional: {get_default_max_net_filled_notional():,}, "
                            f"setting to default max_net_filled_notional "
                            f"instead, symbol_side_key: {get_symbol_side_key([(symbol, side)])}")
            computed_max_net_filled_notional = get_default_max_net_filled_notional()

        # check for user assigned max_net_filled_notional
        if not math.isclose(stored_plan_limits_obj.max_net_filled_notional,
                            updated_plan_limits_obj.max_net_filled_notional):
            if computed_max_net_filled_notional > updated_plan_limits_obj.max_net_filled_notional:
                computed_max_net_filled_notional = updated_plan_limits_obj.max_net_filled_notional
            else:
                logging.warning(
                    f"blocked assignment of user desired {updated_plan_limits_obj.max_net_filled_notional=:,}"
                    f" as it breaches available {computed_max_net_filled_notional=:,}, setting to "
                    f"computed_max_net_filled_notional instead, "
                    f"symbol_side_key: {get_symbol_side_key([(symbol, side)])}")

        # now update max_open_single_leg_notional and max_net_filled_notional
        updated_plan_limits_obj.max_open_single_leg_notional = computed_max_open_single_leg_notional
        updated_plan_limits_obj.max_net_filled_notional = computed_max_net_filled_notional
        return ret_val

    def _compute_n_set_max_notionals(self, plan_limits_obj: PlanLimits) -> None:
        symbol: str = self.plan_leg_1.sec.sec_id
        side: Side = self.plan_leg_1.side
        cb_symbol: str = self.plan_leg_1.sec.sec_id
        eqt_symbol: str = self.plan_leg_2.sec.sec_id
        cb_close_px: float | None = None
        eqt_close_px: float | None = None
        existing_symbol_overviews: List[SymbolOverview] = []
        # load symbol overview
        run_coro = StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_overview_http()
        future = asyncio.run_coroutine_threadsafe(run_coro, StreetBook.asyncio_loop)
        # block for task to finish
        try:
            existing_symbol_overviews = future.result()
        except Exception as e:
            logging.exception(f"underlying_read_symbol_overview_http failed with exception: {e}")
        symbol_overview: SymbolOverview
        for symbol_overview in existing_symbol_overviews:
            if symbol_overview.symbol == cb_symbol:
                cb_close_px = symbol_overview.closing_px
            else:
                eqt_close_px = symbol_overview.closing_px
        # send None instead of self.orig_intra_day_sum to force re-compute intraday [1st time its None to force compute]
        computed_max_single_leg_notional, self.orig_intra_day_bot, self.orig_intra_day_sld = (
            compute_max_single_leg_notional(self.static_data, plan_limits_obj.eligible_brokers, cb_symbol, eqt_symbol,
                                            side, self.usd_fx, cb_close_px, eqt_close_px, self.orig_intra_day_bot,
                                            self.orig_intra_day_sld))
        if math.isclose(computed_max_single_leg_notional, plan_limits_obj.max_single_leg_notional):
            return  # no action as no change
        if get_default_max_notional() < computed_max_single_leg_notional:
            # not allowed to go above default max CB Notional
            logging.warning(f"blocked assignment of computed CB notional: {computed_max_single_leg_notional:,} as it "
                            f"breaches default max_single_leg_notional: {get_default_max_notional():,}, setting to "
                            f"default max_single_leg_notional instead, symbol_side_key: "
                            f"{get_symbol_side_key([(symbol, side)])}")
            computed_max_single_leg_notional = get_default_max_notional()
        # for both if/else computed_max_single_leg_notional is now good to replace max_single_leg_notional
        plan_limits_obj.max_single_leg_notional = computed_max_single_leg_notional
        if computed_max_single_leg_notional < plan_limits_obj.max_open_single_leg_notional:
            plan_limits_obj.max_open_single_leg_notional = computed_max_single_leg_notional
        if computed_max_single_leg_notional < plan_limits_obj.max_net_filled_notional:
            plan_limits_obj.max_net_filled_notional = computed_max_single_leg_notional

    def _apply_restricted_security_check_n_alert(self, sec_id: str) -> bool:
        # restricted security check
        check_passed: bool = True
        if self.static_data is None:
            logging.error(f"unable to conduct restricted security check static data not available yet, "
                          f"symbol_side_key: "
                          f"{get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])}")
            check_passed = False
        elif self.static_data.is_restricted(sec_id):
            logging.error(f"restricted security check failed: {sec_id}, symbol_side_key: "
                          f"{get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])}")
            check_passed = False
        return check_passed

    async def _compute_n_update_average_premium(self, plan_status_obj: PlanStatus):
        conv_px: float | None = None
        symbol_overview_list: List[SymbolOverview] = await (
            StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_overview_http())
        for symbol_overview in symbol_overview_list:
            if symbol_overview.symbol == self.plan_leg_1.sec.sec_id:
                conv_px = symbol_overview.conv_px
                break
        if conv_px is None:
            logging.error(f"no conv_px price found for symbol_side_key: "
                          f"{get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])}")
        average_premium: float
        cb_px: float = plan_status_obj.avg_fill_buy_px if (
                self.plan_leg_1.side == Side.BUY) else plan_status_obj.avg_fill_sell_px
        eqt_px: float = plan_status_obj.avg_fill_buy_px if (
                self.plan_leg_1.side == Side.SELL) else plan_status_obj.avg_fill_sell_px
        if (conv_px is None or cb_px is None or eqt_px is None or math.isclose(conv_px, 0) or
                math.isclose(cb_px, 0) or math.isclose(eqt_px, 0)):
            average_premium = 0
        else:
            average_premium = get_premium(conv_px, eqt_px, cb_px)
        plan_status_obj.average_premium = average_premium

    def _check_n_create_default_plan_limits(self):
        run_coro = (
            StreetBookServiceRoutesCallbackBaseNativeOverride.
            underlying_read_plan_limits_http())
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            plan_limits_list = future.result()
        except Exception as e:
            logging.exception(f"underlying_read_symbol_overview_http "
                              f"failed with exception: {e}")
        else:

            if not plan_limits_list:
                eligible_brokers: List[Broker] | None = None
                try:
                    dismiss_filter_contact_limit_broker_obj_list = (
                        email_book_service_http_client.get_dismiss_filter_contact_limit_brokers_query_client(
                            self.plan_leg_1.sec.sec_id, self.plan_leg_2.sec.sec_id))
                    if dismiss_filter_contact_limit_broker_obj_list:
                        eligible_brokers = dismiss_filter_contact_limit_broker_obj_list[0].brokers
                    else:
                        err_str_ = ("Http Query get_dismiss_filter_contact_limit_brokers_query returned empty list, "
                                    "expected dismiss_filter_contact_limit_broker_obj_list obj with brokers list")
                        logging.error(err_str_)
                except Exception as e:
                    err_str_ = (f"Exception occurred while fetching filtered broker from contact_status - "
                                f"will retry plan_limits create: exception: {e}")
                    logging.error(err_str_)
                    return

                plan_limits = get_new_plan_limits(eligible_brokers)
                plan_limits.id = self.pair_plan_id  # syncing id with pair_plan which triggered this server
                self._compute_n_set_max_notionals(plan_limits)

                run_coro = StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_plan_limits_http(
                    plan_limits)
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

                # block for task to finish
                try:
                    created_plan_limits: PlanLimits = future.result()
                except Exception as e:
                    logging.exception(f"underlying_create_plan_limits_http failed, ignoring create plan_limits, "
                                      f"exception: {e}")
                    return

                logging.debug(f"Created plan_limits with {plan_limits.id=};;;{plan_limits=}")

                return created_plan_limits
            else:
                if len(plan_limits_list) > 1:
                    err_str_: str = ("Unexpected: Found multiple PlanLimits in single executor - ignoring "
                                     "plan_cache update for plan_limits - symbol_side_key: "
                                     f"{get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])};;; "
                                     f"plan_limits_list: {plan_limits_list}")
                    logging.error(err_str_)
                else:
                    self.bartering_data_manager.handle_plan_limits_get_all_ws(plan_limits_list[0])
                return plan_limits_list[0]

    async def _check_n_remove_plan_limits(self):
        plan_limits_tuple = self.plan_cache.get_plan_limits()

        if plan_limits_tuple is not None:
            plan_limits, _ = plan_limits_tuple
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_plan_limits_http(
                plan_limits.id)
        # ignore if plan_limits doesn't exist - happens when plan is in SNOOZED at the time of this call

    def _check_n_create_or_update_plan_status(self, plan_limits: PlanLimits):
        run_coro = (
            StreetBookServiceRoutesCallbackBaseNativeOverride.
            underlying_read_plan_status_http())
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            plan_status_list = future.result()
        except Exception as e:
            logging.exception(f"underlying_read_symbol_overview_http "
                              f"failed with exception: {e}")
        else:
            if not plan_status_list:  # When plan is newly created or reloaded after unloading from collection
                plan_status = get_new_plan_status(plan_limits)
                plan_status.id = self.pair_plan_id  # syncing id with pair_plan which triggered this server

                run_coro = (
                    StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_plan_status_http(
                        plan_status))
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

                # block for task to finish
                try:
                    created_plan_status: PlanStatus = future.result()
                except Exception as e:
                    logging.exception(f"underlying_create_plan_status_http failed: ignoring create plan_status, "
                                      f"exception: {e}")
                    return

                logging.debug(f"Created {plan_status = }")
                return created_plan_status
            else:  # When plan is restarted
                if len(plan_status_list) > 1:
                    err_str_: str = (
                        "Unexpected: Found multiple PlanStatus in single executor - ignoring plan_cache update"
                        f"for plan_status - symbol_side_key: "
                        f"{get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])};;; "
                        f"plan_status_list: {plan_status_list}")
                    logging.error(err_str_)
                else:
                    self.bartering_data_manager.handle_plan_status_get_all_ws(plan_status_list[0])
                return plan_status_list[0]

    async def _check_n_remove_plan_status(self):
        async with PlanStatus.reentrant_lock:
            plan_status_tuple = self.plan_cache.get_plan_status()

            if plan_status_tuple:
                plan_status, _ = plan_status_tuple
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_plan_status_http(
                    plan_status.id)
            # ignore if plan_limits doesn't exist - happens when plan is in SNOOZED at the time of this call

    def get_consumable_concentration_from_source(self, symbol: str, plan_limits: PlanLimits):
        security_float: float | None = self.static_data.get_security_float_from_ticker(symbol)
        if security_float is None or security_float <= 0:
            logging.error(f"concentration check will fail for {symbol}, invalid security float found in static data: "
                          f"{security_float}")
            consumable_concentration = 0
        else:
            consumable_concentration = \
                int((security_float / 100) * plan_limits.max_concentration)
        return consumable_concentration

    async def _check_n_create_plan_brief_for_active_pair_plan(self, plan_limits: PlanLimits, hedge_ratio: float):
        symbol = self.plan_leg_1.sec.sec_id
        side = self.plan_leg_1.side
        plan_brief_tuple = self.plan_cache.get_plan_brief()

        if plan_brief_tuple is not None:
            # all fine if plan_brief already exists: happens in some crash recovery
            return
        else:
            # If no plan_brief exists for this symbol
            consumable_open_chores = plan_limits.max_open_chores_per_side
            leg1_consumable_notional = plan_limits.max_single_leg_notional
            leg2_consumable_notional = plan_limits.max_single_leg_notional * hedge_ratio
            leg_consumable_open_notional = plan_limits.max_open_single_leg_notional

        residual_qty = 0
        all_bkr_cxlled_qty = 0
        open_notional = 0
        open_qty = 0

        buy_side_bartering_brief: PairSideBarteringBrief | None = None
        sell_side_bartering_brief: PairSideBarteringBrief | None = None

        for sec, side in [(self.plan_leg_1.sec, self.plan_leg_1.side), (self.plan_leg_2.sec, self.plan_leg_2.side)]:
            symbol = sec.sec_id
            consumable_concentration = self.get_consumable_concentration_from_source(symbol, plan_limits)

            participation_period_chore_qty_sum = 0
            consumable_cxl_qty = 0
            applicable_period_second = plan_limits.market_barter_volume_participation.applicable_period_seconds
            executor_check_snapshot_list = \
                await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                       underlying_get_executor_check_snapshot_query_http(symbol, side,
                                                                         applicable_period_second))
            if len(executor_check_snapshot_list) == 1:
                indicative_consumable_participation_qty = \
                    get_consumable_participation_qty(
                        executor_check_snapshot_list,
                        plan_limits.market_barter_volume_participation.max_participation_rate)
            else:
                logging.error("Received unexpected length of executor_check_snapshot_list from query "
                              f"{len(executor_check_snapshot_list)}, expected 1, symbol_side_key: "
                              f"{get_symbol_side_key([(symbol, side)])}, likely bug in "
                              f"get_executor_check_snapshot_query pre implementation")
                indicative_consumable_participation_qty = 0
            indicative_consumable_residual = plan_limits.residual_restriction.max_residual
            consumable_notional = leg1_consumable_notional if symbol == self.plan_leg_1.sec.sec_id else \
                leg2_consumable_notional
            sec_pair_side_bartering_brief_obj = \
                PairSideBarteringBrief(security=sec,
                                     side=side,
                                     last_update_date_time=DateTime.utcnow(),
                                     consumable_open_chores=consumable_open_chores,
                                     consumable_notional=consumable_notional,
                                     consumable_open_notional=leg_consumable_open_notional,
                                     consumable_concentration=consumable_concentration,
                                     participation_period_chore_qty_sum=participation_period_chore_qty_sum,
                                     consumable_cxl_qty=consumable_cxl_qty,
                                     indicative_consumable_participation_qty=indicative_consumable_participation_qty,
                                     residual_qty=residual_qty,
                                     indicative_consumable_residual=indicative_consumable_residual,
                                     all_bkr_cxlled_qty=all_bkr_cxlled_qty,
                                     open_notional=open_notional, open_qty=open_qty)
            if Side.BUY == side:
                if buy_side_bartering_brief is None:
                    buy_side_bartering_brief = sec_pair_side_bartering_brief_obj
                else:
                    logging.error(f"expected buy_side_bartering_brief to be None, found: {buy_side_bartering_brief}")
            elif Side.SELL == side:
                if sell_side_bartering_brief is None:
                    sell_side_bartering_brief = sec_pair_side_bartering_brief_obj
                else:
                    logging.error(f"expected sell_side_bartering_brief to be None, found: {sell_side_bartering_brief}")

        plan_brief_obj: PlanBrief = PlanBrief(id=plan_limits.id,
                                                 pair_buy_side_bartering_brief=buy_side_bartering_brief,
                                                 pair_sell_side_bartering_brief=sell_side_bartering_brief,
                                                 consumable_nett_filled_notional=plan_limits.max_net_filled_notional)
        created_underlying_plan_brief = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_plan_brief_http(
                plan_brief_obj)
        logging.debug(f"Created plan brief in post call of update plan_status to active of "
                      f"key: {get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])};;; "
                      f"{plan_limits=}, {created_underlying_plan_brief=}")

    async def _check_n_create_symbol_snapshot_for_active_pair_plan(self):
        # before running this server
        pair_symbol_side_list = [
            (self.plan_leg_1.sec, self.plan_leg_1.side),
            (self.plan_leg_2.sec, self.plan_leg_2.side)
        ]

        for security, side in pair_symbol_side_list:
            if security is not None and side is not None:

                symbol_side_snapshots_tuple = self.plan_cache.get_symbol_side_snapshot_from_symbol(security.sec_id)

                if symbol_side_snapshots_tuple is None:
                    symbol_side_snapshot_obj = SymbolSideSnapshot(id=SymbolSideSnapshot.next_id(),
                                                                  security=security,
                                                                  side=side, avg_px=0, total_qty=0,
                                                                  total_filled_qty=0, avg_fill_px=0.0,
                                                                  total_fill_notional=0.0, last_update_fill_qty=0,
                                                                  last_update_fill_px=0, total_cxled_qty=0,
                                                                  avg_cxled_px=0,
                                                                  total_cxled_notional=0,
                                                                  last_update_date_time=DateTime.utcnow(),
                                                                  chore_count=0)
                    created_symbol_side_snapshot: SymbolSideSnapshot = \
                        await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                               underlying_create_symbol_side_snapshot_http(symbol_side_snapshot_obj))
                    logging.debug(f"Created SymbolSideSnapshot with key: "
                                  f"{get_symbol_side_snapshot_log_key(created_symbol_side_snapshot)};;;"
                                  f"{created_symbol_side_snapshot=}")
                # else not required: all fine if symbol_side_snapshot already exists: happens in some crash recovery
            else:
                # Ignore symbol side snapshot creation and logging if any of security and side is None
                logging.debug(f"Received either security or side as None from config of this start_executor for "
                              f"{self.port = }, likely populated by phone_book before launching this server, "
                              f"{security = }, {side = }")

    async def _check_n_force_publish_symbol_overview_for_active_plan(self) -> None:

        symbols_list = [self.plan_leg_1.sec.sec_id, self.plan_leg_2.sec.sec_id]

        async with SymbolOverview.reentrant_lock:
            for symbol in symbols_list:
                symbol_overview_obj_tuple = self.plan_cache.get_symbol_overview_from_symbol(symbol)

                if symbol_overview_obj_tuple is not None:
                    symbol_overview_obj, _ = symbol_overview_obj_tuple
                    if not symbol_overview_obj.force_publish:
                        updated_symbol_overview = {"_id": symbol_overview_obj.id, "force_publish": True}
                        await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                               underlying_partial_update_symbol_overview_http(updated_symbol_overview))
                    # else not required: happens in some crash recovery

    def _check_n_create_related_models_for_plan(self) -> bool:
        plan_limits = self._check_n_create_default_plan_limits()
        if plan_limits is not None:
            plan_status = self._check_n_create_or_update_plan_status(plan_limits)

            if plan_status is not None:
                pair_plan_tuple = self.plan_cache.get_pair_plan()
                if pair_plan_tuple is not None:
                    pair_plan, _ = pair_plan_tuple
                    if pair_plan.server_ready_state < 2:
                        pair_plan.server_ready_state = 2   # indicates to ui that executor server is ready

                        self.update_simulate_config_yaml(pair_plan)

                        plan_state = None
                        if pair_plan.plan_state == PlanState.PlanState_SNOOZED:
                            pair_plan.plan_state = PlanState.PlanState_READY
                            # plan_state = PlanState.PlanState_READY
                        # else not required: If it's not startup for reload or new plan creation then avoid

                        # setting pair_plan's legs' company name
                        pair_plan.pair_plan_params.plan_leg1.company = self.leg1_symbol_cache.so.company
                        pair_plan.pair_plan_params.plan_leg2.company = self.leg2_symbol_cache.so.company

                        try:
                            email_book_service_http_client.put_pair_plan_client(pair_plan)
                            logging.debug(f"pair_plan's server_ready_state set to 2, {pair_plan=}")
                            return True
                        except Exception as e:
                            logging.exception("patch_pair_plan_client failed while setting server_ready_state "
                                              f"to 2, retrying in next startup refresh: exception: {e}")
                    # else not required: not updating if already server_ready_state == 2
                else:
                    err_str_ = ("Unexpected: Can't find pair_plan object in plan_cache - "
                                "retrying in next startup refresh")
                    logging.error(err_str_)
        return False

    async def load_plan_cache(self):
        # updating plan_brief
        plan_brief_list: List[PlanBrief] = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_brief_http()
        for plan_brief in plan_brief_list:
            self.bartering_data_manager.handle_plan_brief_get_all_ws(plan_brief)

        if self.is_crash_recovery:

            # updating chore_journals
            chore_journals: List[ChoreJournal] = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_journal_http()
            for chore_journal in chore_journals:
                self.bartering_data_manager.handle_recovery_chore_journal(chore_journal)

            # updating chore_snapshots
            chore_snapshots: List[ChoreSnapshot] = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_snapshot_http()
            for chore_snapshot in chore_snapshots:
                self.bartering_data_manager.handle_chore_snapshot_get_all_ws(chore_snapshot)

            # updating symbol_side_snapshot
            symbol_side_snapshots: List[SymbolSideSnapshot] = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_side_snapshot_http()
            for symbol_side_snapshot in symbol_side_snapshots:
                self.bartering_data_manager.handle_symbol_side_snapshot_get_all_ws(symbol_side_snapshot)

            # updating cancel_chores
            cancel_chores: List[CancelChore] = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_cancel_chore_http()
            for cancel_chore in cancel_chores:
                self.bartering_data_manager.handle_recovery_cancel_chore(cancel_chore)

    def get_hedge_ratio(self) -> float | None:
        """
        assumes await self.load_plan_cache() is invoked prior to this call (only once at startup)
        Returns: hedge ratio from pair plan or 1
        """
        pair_plan: PairPlanBaseModel | PairPlan | None = self.plan_cache.get_pair_plan_obj()
        if not pair_plan:
            err_str_ = (f"Can't find any pair_plan in cache to create related models for active plan, "
                        f"ignoring model creations, symbol_side_key: "
                        f"{get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])}")
            logging.error(err_str_)
            return
        hedge_ratio = 1
        if pair_plan.pair_plan_params:
            hedge_ratio = pair_plan.pair_plan_params.hedge_ratio
            if not hedge_ratio:
                logging.warning(f"hedge_ratio not found in pair_plan.pair_plan_params, defaulting to 1 for: "
                                f"{get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])};;;"
                                f"pair_plan.pair_plan_params: {pair_plan.pair_plan_params}")
                hedge_ratio = 1
        return hedge_ratio

    async def _create_related_models_for_active_plan(self) -> None:
        # updating plan_cache
        await self.load_plan_cache()
        hedge_ratio: float = self.get_hedge_ratio()
        plan_limits_tuple = self.plan_cache.get_plan_limits()

        if plan_limits_tuple is not None:
            plan_limits, _ = plan_limits_tuple

            # creating plan_brief for both leg securities
            await self._check_n_create_plan_brief_for_active_pair_plan(plan_limits, hedge_ratio)
            # creating symbol_side_snapshot for both leg securities if not already exists
            await self._check_n_create_symbol_snapshot_for_active_pair_plan()
            # changing symbol_overview force_publish to True if exists
            await self._check_n_force_publish_symbol_overview_for_active_plan()
        else:
            err_str_ = (
                "Can't find any plan_limits in cache to create related models for active plan, "
                "ignoring model creations, symbol_side_key: "
                f"{get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])}")
            logging.error(err_str_)
            return

        logging.info(f"Updated Plan to active: "
                     f"{get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])}")

    async def read_all_ui_layout_pre(self):
        await self.read_all_ui_layout_pre_handler()

    ############################
    # Limit Check update methods
    ############################
    def check_consumable_cxl_qty(self, updated_plan_status: PlanStatusBaseModel, plan_limits: PlanLimits,
                                 symbol_side_snapshot_: SymbolSideSnapshot,
                                 single_side_bartering_brief: PairSideBarteringBrief, side: Side):
        if single_side_bartering_brief.all_bkr_cxlled_qty > 0:
            if (consumable_cxl_qty := single_side_bartering_brief.consumable_cxl_qty) < 0:
                err_str_ = (f"Consumable cxl qty can't be < 0, currently is {consumable_cxl_qty} "
                            f"for symbol {single_side_bartering_brief.security.sec_id} and side {side} - pausing "
                            f"this plan")
                alert_brief: str = err_str_
                alert_details: str = f"{updated_plan_status=}, {plan_limits=}, {symbol_side_snapshot_=}"
                logging.critical(f"{alert_brief}, symbol_side_snapshot_key: "
                                 f"{get_symbol_side_snapshot_log_key(symbol_side_snapshot_)};;;{alert_details}")
                return False  # check failed - caller should pause plan
            # else not required: if consumable_cxl_qty is allowed then ignore
        # else not required: if there is not even a single chore of {side} then consumable_cxl_qty will
        # become 0 in that case too, so ignore if all_bkr_cxlled_qty is 0
        return True  # check passed

    async def _pause_plan_if_limits_breached(self, updated_plan_status: PlanStatusBaseModel,
                                              plan_limits: PlanLimits, plan_brief_: PlanBrief,
                                              symbol_side_snapshot_: SymbolSideSnapshot, is_cxl: bool = False):
        pause_plan: bool = False
        if (residual_notional := updated_plan_status.residual.residual_notional) is not None:
            if residual_notional > (max_residual := plan_limits.residual_restriction.max_residual):
                alert_brief: str = (f"{residual_notional=} > {max_residual=} - "
                                    f"pausing this plan")
                alert_details: str = f"{updated_plan_status=}, {plan_limits=}"
                logging.critical(f"{alert_brief}, symbol_side_snapshot_key: "
                                 f"{get_symbol_side_snapshot_log_key(symbol_side_snapshot_)};;; {alert_details}")
                pause_plan = True
            # else not required: if residual is in control then nothing to do

        if not pause_plan and is_cxl and (
                symbol_side_snapshot_.chore_count > plan_limits.cancel_rate.waived_initial_chores):
            symbol = symbol_side_snapshot_.security.sec_id
            side = symbol_side_snapshot_.side
            min_notional_condition_met: bool = False
            if (plan_limits.cancel_rate.waived_min_rolling_period_seconds and
                    plan_limits.cancel_rate.waived_min_rolling_notional and
                    plan_limits.cancel_rate.waived_min_rolling_notional > 0):
                last_n_sec_chore_qty = await self.get_last_n_sec_chore_qty(
                    symbol, side, plan_limits.cancel_rate.waived_min_rolling_period_seconds)
                logging.debug(f"_update_plan_status_from_fill_journal: {last_n_sec_chore_qty=}, {symbol=}, {side=}")
                if (last_n_sec_chore_qty * self.get_usd_px(symbol_side_snapshot_.avg_px, symbol) >
                        plan_limits.cancel_rate.waived_min_rolling_notional):
                    min_notional_condition_met = True
            else:
                min_notional_condition_met = True  # min notional condition not imposed
            if min_notional_condition_met:
                if symbol_side_snapshot_.side == Side.BUY:
                    pause_plan = not (self.check_consumable_cxl_qty(updated_plan_status, plan_limits,
                                                                     symbol_side_snapshot_,
                                                                     plan_brief_.pair_buy_side_bartering_brief,
                                                                     Side.BUY))
                else:
                    pause_plan = not (self.check_consumable_cxl_qty(updated_plan_status, plan_limits,
                                                                     symbol_side_snapshot_,
                                                                     plan_brief_.pair_sell_side_bartering_brief,
                                                                     Side.SELL))
        # else not required: no further pause_plan eval needed
        if pause_plan:
            self.pause_plan()

    ####################################
    # Get specific Data handling Methods
    ####################################

    def _get_last_barter_px_n_symbol_tuples_from_tob(
            self, current_leg_tob_obj: TopOfBookBaseModel,
            other_leg_tob_obj: TopOfBookBaseModel) -> Tuple[Tuple[float, str], Tuple[float, str]]:
        return ((current_leg_tob_obj.last_barter.px, current_leg_tob_obj.symbol),
                (other_leg_tob_obj.last_barter.px, other_leg_tob_obj.symbol))

    def get_cached_top_of_book_from_symbol(self, symbol: str):
        if self.plan_leg_1.sec.sec_id == symbol:
            return self.leg1_symbol_cache.top_of_book
        else:
            return self.leg2_symbol_cache.top_of_book

    def __get_residual_obj(self, side: Side, plan_brief: PlanBrief) -> Residual | None:
        if side == Side.BUY:
            residual_qty = plan_brief.pair_buy_side_bartering_brief.residual_qty
            other_leg_residual_qty = plan_brief.pair_sell_side_bartering_brief.residual_qty
            top_of_book_obj = \
                self.get_cached_top_of_book_from_symbol(plan_brief.pair_buy_side_bartering_brief.security.sec_id)
            other_leg_top_of_book = \
                self.get_cached_top_of_book_from_symbol(plan_brief.pair_sell_side_bartering_brief.security.sec_id)
        else:
            residual_qty = plan_brief.pair_sell_side_bartering_brief.residual_qty
            other_leg_residual_qty = plan_brief.pair_buy_side_bartering_brief.residual_qty
            top_of_book_obj = \
                self.get_cached_top_of_book_from_symbol(plan_brief.pair_sell_side_bartering_brief.security.sec_id)
            other_leg_top_of_book = \
                self.get_cached_top_of_book_from_symbol(plan_brief.pair_buy_side_bartering_brief.security.sec_id)

        if top_of_book_obj is None or other_leg_top_of_book is None:
            logging.error(f"Received both leg's TOBs as {top_of_book_obj} and {other_leg_top_of_book}, "
                          f"plan_brief_key: {get_plan_brief_log_key(plan_brief)}")
            return None

        # since unit value is used make function
        current_leg_tob_data, other_leg_tob_data = (
            self._get_last_barter_px_n_symbol_tuples_from_tob(top_of_book_obj, other_leg_top_of_book))
        current_leg_last_barter_px, current_leg_tob_symbol = current_leg_tob_data
        other_leg_last_barter_px, other_leg_tob_symbol = other_leg_tob_data
        residual_notional = abs((residual_qty * self.get_usd_px(current_leg_last_barter_px,
                                                                current_leg_tob_symbol)) -
                                (other_leg_residual_qty * self.get_usd_px(other_leg_last_barter_px,
                                                                          other_leg_tob_symbol)))
        if side == Side.BUY:
            if (residual_qty * self.get_usd_px(top_of_book_obj.last_barter.px,
                                               top_of_book_obj.symbol)) > \
                    (other_leg_residual_qty * self.get_usd_px(other_leg_top_of_book.last_barter.px,
                                                              other_leg_top_of_book.symbol)):
                residual_security = plan_brief.pair_buy_side_bartering_brief.security
            else:
                residual_security = plan_brief.pair_sell_side_bartering_brief.security
        else:
            if (residual_qty * top_of_book_obj.last_barter.px) > \
                    (other_leg_residual_qty * other_leg_top_of_book.last_barter.px):
                residual_security = plan_brief.pair_sell_side_bartering_brief.security
            else:
                residual_security = plan_brief.pair_buy_side_bartering_brief.security

        if residual_notional > 0:
            updated_residual = Residual(security=residual_security, residual_notional=residual_notional)
            return updated_residual
        else:
            updated_residual = Residual(security=residual_security, residual_notional=0)
            return updated_residual

    async def get_last_n_sec_chore_qty(self, symbol: str, side: Side, last_n_sec: int) -> int | None:
        last_n_sec_chore_qty: int | None = None
        if last_n_sec == 0:
            symbol_side_snapshots_tuple = self.plan_cache.get_symbol_side_snapshot_from_symbol(symbol)
            if symbol_side_snapshots_tuple is not None:
                symbol_side_snapshot, _ = symbol_side_snapshots_tuple
                last_n_sec_chore_qty = symbol_side_snapshot.total_qty
            else:
                err_str_ = f"Received symbol_side_snapshots_tuple as None from plan_cache, symbol_side_key: " \
                           f"{get_symbol_side_key([(symbol, side)])}"
                logging.exception(err_str_)
        else:
            agg_objs = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_snapshot_http(
                    get_chore_total_sum_of_last_n_sec(symbol, last_n_sec), self.get_generic_read_route())

            if len(agg_objs) > 0:
                last_n_sec_chore_qty = agg_objs[-1].last_n_sec_total_qty
            else:
                last_n_sec_chore_qty = 0
                err_str_ = "received empty list of aggregated objects from aggregation on ChoreSnapshot to " \
                           f"get {last_n_sec=} total chore sum, symbol_side_key: " \
                           f"{get_symbol_side_key([(symbol, side)])}"
                logging.debug(err_str_)
        logging.debug(f"Received {last_n_sec_chore_qty=}, {last_n_sec=}, for {get_symbol_side_key([(symbol, side)])}")
        return last_n_sec_chore_qty

    async def get_last_n_sec_barter_qty(self, symbol: str, side: Side) -> int | None:
        plan_limits_tuple = self.plan_cache.get_plan_limits()

        last_n_sec_barter_qty: int | None = None
        if plan_limits_tuple is not None:
            plan_limits, _ = plan_limits_tuple

            if plan_limits is not None:
                applicable_period_seconds = plan_limits.market_barter_volume_participation.applicable_period_seconds
                last_n_sec_market_barter_vol_obj_list = \
                    await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                           underlying_get_last_n_sec_total_barter_qty_query_http(symbol, applicable_period_seconds))
                if last_n_sec_market_barter_vol_obj_list:
                    last_n_sec_barter_qty = last_n_sec_market_barter_vol_obj_list[0].last_n_sec_barter_vol
                    logging.debug(
                        f"Received {last_n_sec_barter_qty=}, {applicable_period_seconds=}, for "
                        f"{get_symbol_side_key([(symbol, side)])}")
                else:
                    logging.error(f"could not receive any last_n_sec_market_barter_vol_obj to get last_n_sec_barter_qty "
                                  f"for symbol_side_key: {get_symbol_side_key([(symbol, side)])}, likely bug in "
                                  f"get_last_n_sec_total_barter_qty_query pre impl")
        else:
            err_str_ = (
                "Can't find any plan_limits in cache to get last_n_sec barter qty, "
                "ignoring model creations, symbol_side_key: "
                f"{get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])}")
            logging.error(err_str_)
        return last_n_sec_barter_qty

    ######################################
    # Plan lvl models update pre handling
    ######################################

    async def create_admin_control_pre(self, admin_control_obj: AdminControl):
        match admin_control_obj.command_type:
            case CommandType.RESET_STATE:
                from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_msgspec_database \
                    import document_models
                for document_model in document_models:
                    document_model._cache_obj_id_to_obj_dict = {}
            case other_:
                logging.error(f"create_admin_control_pre failed. unrecognized command_type: {other_}")

    async def _update_plan_limits_pre(self, stored_plan_limits_obj: PlanLimits,
                                       updated_plan_limits_obj: PlanLimits):
        stored_plan_status_obj: PlanStatus = await (
            StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_status_by_id_http(
                stored_plan_limits_obj.id))
        await self._compute_n_update_max_notionals(stored_plan_limits_obj, updated_plan_limits_obj,
                                                   stored_plan_status_obj)

    async def update_plan_limits_pre(self, stored_plan_limits_obj: PlanLimits,
                                      updated_plan_limits_obj: PlanLimits):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_plan_limits_pre not ready - service is not initialized yet, " \
                       f"symbol_side_key: {get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        await self._update_plan_limits_pre(stored_plan_limits_obj, updated_plan_limits_obj)
        if updated_plan_limits_obj.plan_limits_update_seq_num is None:
            updated_plan_limits_obj.plan_limits_update_seq_num = 0
        updated_plan_limits_obj.plan_limits_update_seq_num += 1
        return updated_plan_limits_obj

    async def partial_update_plan_limits_pre(self, stored_plan_limits_dict: Dict,
                                              updated_plan_limits_obj_json: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_plan_limits_pre not ready - service is not initialized yet, " \
                       f"symbol_side_key: {get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        original_eligible_brokers = []
        if (eligible_brokers := updated_plan_limits_obj_json.get("eligible_brokers")) is not None:
            original_eligible_brokers = copy.deepcopy(eligible_brokers)

        updated_obj_dict = compare_n_patch_dict(
            copy.deepcopy(stored_plan_limits_dict), updated_plan_limits_obj_json)
        stored_plan_limits_obj = PlanLimitsOptional.from_dict(stored_plan_limits_dict)
        updated_plan_limits_obj = PlanLimitsOptional.from_dict(updated_obj_dict)
        await self._update_plan_limits_pre(stored_plan_limits_obj, updated_plan_limits_obj)
        updated_plan_limits_obj_json = updated_plan_limits_obj.to_dict(exclude_none=True)
        updated_plan_limits_obj_json["eligible_brokers"] = original_eligible_brokers

        if stored_plan_limits_obj.plan_limits_update_seq_num is None:
            stored_plan_limits_obj.plan_limits_update_seq_num = 0
        updated_plan_limits_obj_json[
            "plan_limits_update_seq_num"] = stored_plan_limits_obj.plan_limits_update_seq_num + 1
        return updated_plan_limits_obj_json

    async def _update_plan_status_pre(self, updated_plan_status_obj: PlanStatus):
        await self._compute_n_update_average_premium(updated_plan_status_obj)

    async def update_plan_status_pre(self, updated_plan_status_obj: PlanStatus):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_plan_status_pre not ready - service is not initialized yet, " \
                       f"symbol_side_key: {get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        await self._update_plan_status_pre(updated_plan_status_obj)

        if updated_plan_status_obj.plan_status_update_seq_num is None:
            updated_plan_status_obj.plan_status_update_seq_num = 0
        updated_plan_status_obj.plan_status_update_seq_num += 1
        updated_plan_status_obj.last_update_date_time = DateTime.utcnow()

        return updated_plan_status_obj

    async def handle_plan_activate_query_pre(self, handle_plan_activate_class_type: Type[HandlePlanActivate]):
        await self._create_related_models_for_active_plan()
        return []

    async def partial_update_plan_status_pre(self, stored_plan_status_obj_json: Dict[str, Any],
                                              updated_plan_status_obj_json: Dict[str, Any]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_plan_status_pre not ready - service is not initialized yet, " \
                       f"symbol_side_key: {get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        updated_obj_dict = compare_n_patch_dict(copy.deepcopy(stored_plan_status_obj_json),
                                                         updated_plan_status_obj_json)
        updated_plan_status_obj = PlanStatus.from_dict(updated_obj_dict)
        await self._update_plan_status_pre(updated_plan_status_obj)
        updated_plan_status_obj_json = updated_plan_status_obj.to_dict(exclude_none=True)

        plan_status_update_seq_num = stored_plan_status_obj_json.get("plan_status_update_seq_num")
        if plan_status_update_seq_num is None:
            plan_status_update_seq_num = 0
        updated_plan_status_obj_json[
            "plan_status_update_seq_num"] = plan_status_update_seq_num + 1
        updated_plan_status_obj_json["last_update_date_time"] = DateTime.utcnow()

        return updated_plan_status_obj_json

    ##############################
    # Chore Journal Update Methods
    ##############################

    async def create_chore_journal_pre(self, chore_journal_obj: ChoreJournal) -> None:
        await self.handle_create_chore_journal_pre(chore_journal_obj)

    async def create_chore_journal_post(self, chore_journal_obj: ChoreJournal):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_chore_journal_get_all_ws(chore_journal_obj)

        async with StreetBookServiceRoutesCallbackBaseNativeOverride.journal_shared_lock:
            res = await self._update_chore_snapshot_from_chore_journal(chore_journal_obj)
            is_cxl_after_cxl: bool = False
            if res is not None:
                if len(res) == 3:
                    chore_snapshot, plan_brief, contact_status_updates = res
                    # Updating and checking contact_limits in contact_manager
                    post_book_service_http_client.check_contact_limits_query_client(
                        self.pair_plan_id, chore_journal_obj, chore_snapshot, plan_brief, contact_status_updates)
                elif len(res) == 1:
                    is_cxl_after_cxl = res[0]
                    if not is_cxl_after_cxl:
                        logging.error(f"_update_chore_snapshot_from_chore_journal failed for key: "
                                      f"{StreetBookServiceRoutesCallbackBaseNativeOverride.get_chore_journal_log_key(chore_journal_obj)};;;{chore_journal_obj=}")
                    else:
                        logging.debug(f"_update_chore_snapshot_from_chore_journal detected cxl_after_cxl for key: "
                                      f"{StreetBookServiceRoutesCallbackBaseNativeOverride.get_chore_journal_log_key(chore_journal_obj)};;;{chore_journal_obj=}")
            else:
                logging.error(f"_update_chore_snapshot_from_chore_journal failed for key: "
                              f"{StreetBookServiceRoutesCallbackBaseNativeOverride.get_chore_journal_log_key(chore_journal_obj)};;;{chore_journal_obj=}")
            # signifies some unexpected exception occurred so complete update was not done,
            # therefore avoiding contact_limit checks too

    async def create_chore_snapshot_pre(self, chore_snapshot_obj: ChoreSnapshot):
        await self.handle_create_chore_snapshot_pre(chore_snapshot_obj)

    async def create_symbol_side_snapshot_pre(self, symbol_side_snapshot_obj: SymbolSideSnapshot):
        # updating security's sec_id_source to default value if sec_id_source is None
        if symbol_side_snapshot_obj.security.sec_id_source is None:
            symbol_side_snapshot_obj.security.sec_id_source = SecurityIdSource.TICKER

    async def _handle_post_chore_snapshot_update_tasks_in_chore_dod(self, chore_journal_obj: ChoreJournal,
                                                                    chore_snapshot: ChoreSnapshot):
        if chore_snapshot.chore_status != ChoreStatusType.OE_FILLED:
            symbol_side_snapshot = await self._create_update_symbol_side_snapshot_from_chore_journal(
                chore_journal_obj, chore_snapshot)
            if symbol_side_snapshot is not None:
                updated_plan_brief = (
                    await self._update_plan_brief_from_chore_or_fill(chore_journal_obj, chore_snapshot,
                                                                      symbol_side_snapshot))
                if updated_plan_brief is not None:
                    await self._update_plan_status_from_chore_journal(
                        chore_journal_obj, chore_snapshot, symbol_side_snapshot, updated_plan_brief)
                # else not required: if updated_plan_brief is None then it means some error occurred in
                # _update_plan_brief_from_chore which would have got added to alert already
                contact_status_updates: ContactStatusUpdatesContainer | None = (
                    await self._update_contact_status_from_chore_journal(
                        chore_journal_obj, chore_snapshot))

                return chore_snapshot, updated_plan_brief, contact_status_updates

            # else not required: if symbol_side_snapshot is None then it means some error occurred in
            # _create_update_symbol_side_snapshot_from_chore_journal which would have got added to
            # alert already

        # else not required: If CXL_ACK arrived after chore is fully filled then since we ignore
        # any update for this chore journal object, returns None to not update post barter engine too

    async def _handle_post_chore_snapshot_update_tasks_after_chore_journal_amend_applied(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        symbol_side_snapshot = \
            await self._create_update_symbol_side_snapshot_from_chore_journal(chore_journal_obj,
                                                                              chore_snapshot)
        if symbol_side_snapshot is not None:
            updated_plan_brief = (
                await self._update_plan_brief_from_chore_or_fill(chore_journal_obj,
                                                                  chore_snapshot,
                                                                  symbol_side_snapshot))
            if updated_plan_brief is not None:
                await self._update_plan_status_from_chore_journal(
                    chore_journal_obj, chore_snapshot, symbol_side_snapshot,
                    updated_plan_brief)
            # else not required: if updated_plan_brief is None then it means some error occurred in
            # _update_plan_brief_from_chore which would have got added to alert already
            contact_status_updates: ContactStatusUpdatesContainer = (
                await self._update_contact_status_from_chore_journal(
                    chore_journal_obj, chore_snapshot))
            return chore_snapshot, updated_plan_brief, contact_status_updates
        return None, None, None

    def update_chore_snapshot_pre_checks(self) -> bool:
        pair_plan = self.plan_cache.get_pair_plan_obj()

        if not is_ongoing_plan(pair_plan):
            # avoiding any update if plan is non-ongoing
            return False
        return True

    async def handle_post_chore_snapshot_update_tasks_for_new_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        symbol_side_snapshot = \
            await self._create_update_symbol_side_snapshot_from_chore_journal(chore_journal_obj,
                                                                              chore_snapshot)
        if symbol_side_snapshot is not None:
            updated_plan_brief = await self._update_plan_brief_from_chore_or_fill(chore_journal_obj,
                                                                                    chore_snapshot,
                                                                                    symbol_side_snapshot)
            if updated_plan_brief is not None:
                await self._update_plan_status_from_chore_journal(chore_journal_obj, chore_snapshot,
                                                                   symbol_side_snapshot, updated_plan_brief)
            # else not required: if updated_plan_brief is None then it means some error occurred in
            # _update_plan_brief_from_chore which would have got added to alert already
            contact_status_updates: ContactStatusUpdatesContainer | None = (
                await self._update_contact_status_from_chore_journal(
                    chore_journal_obj, chore_snapshot))

            return chore_snapshot, updated_plan_brief, contact_status_updates
        # else not require_create_update_symbol_side_snapshot_from_chore_journald: if symbol_side_snapshot
        # is None then it means some error occurred in _create_update_symbol_side_snapshot_from_chore_journal
        # which would have got added to alert already

    async def handle_post_chore_snapshot_update_tasks_for_ack_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot, None, None

    async def handle_post_chore_snapshot_update_tasks_for_cxl_unack_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot, None, None

    async def handle_post_chore_snapshot_update_tasks_for_cxl_rej_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot, None, None

    async def handle_post_chore_snapshot_update_tasks_for_int_rej_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        symbol_side_snapshot = \
            await self._create_update_symbol_side_snapshot_from_chore_journal(chore_journal_obj,
                                                                              chore_snapshot)
        if symbol_side_snapshot is not None:
            updated_plan_brief = (
                await self._update_plan_brief_from_chore_or_fill(chore_journal_obj, chore_snapshot,
                                                                  symbol_side_snapshot))
            if updated_plan_brief is not None:
                await self._update_plan_status_from_chore_journal(
                    chore_journal_obj, chore_snapshot, symbol_side_snapshot, updated_plan_brief)
            # else not required: if updated_plan_brief is None then it means some error occurred in
            # _update_plan_brief_from_chore which would have got added to alert already
            contact_status_updates: ContactStatusUpdatesContainer = (
                await self._update_contact_status_from_chore_journal(
                    chore_journal_obj, chore_snapshot))

            return chore_snapshot, updated_plan_brief, contact_status_updates
        # else not require_create_update_symbol_side_snapshot_from_chore_journald:
        # if symbol_side_snapshot is None then it means some error occurred in
        # _create_update_symbol_side_snapshot_from_chore_journal which would have
        # got added to alert already

    async def handle_post_chore_snapshot_update_tasks_for_lapse_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        symbol_side_snapshot = \
            await self._create_update_symbol_side_snapshot_from_chore_journal(chore_journal_obj,
                                                                              chore_snapshot)
        if symbol_side_snapshot is not None:
            updated_plan_brief = (
                await self._update_plan_brief_from_chore_or_fill(chore_journal_obj, chore_snapshot,
                                                                  symbol_side_snapshot))
            if updated_plan_brief is not None:
                await self._update_plan_status_from_chore_journal(
                    chore_journal_obj, chore_snapshot, symbol_side_snapshot, updated_plan_brief)
            # else not required: if updated_plan_brief is None then it means some error occurred in
            # _update_plan_brief_from_chore which would have got added to alert already
            contact_status_updates: ContactStatusUpdatesContainer = (
                await self._update_contact_status_from_chore_journal(
                    chore_journal_obj, chore_snapshot))
            return chore_snapshot, updated_plan_brief, contact_status_updates
        # else not require_create_update_symbol_side_snapshot_from_chore_journald:
        # if symbol_side_snapshot is None then it means some error occurred in
        # _create_update_symbol_side_snapshot_from_chore_journal which would have
        # got added to alert already

    async def handle_post_chore_snapshot_update_tasks_for_non_risky_amend_unack_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot, None, None

    async def handle_post_chore_snapshot_update_tasks_for_risky_amend_ack_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot, None, None

    async def handle_post_chore_snapshot_update_tasks_for_non_risky_amend_rej_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot, None, None

    async def _create_symbol_side_snapshot_for_new_chore(self,
                                                         new_chore_journal_obj: ChoreJournal) -> SymbolSideSnapshot:
        security = new_chore_journal_obj.chore.security
        side = new_chore_journal_obj.chore.side
        symbol_side_snapshot_obj = SymbolSideSnapshot(id=SymbolSideSnapshot.next_id(), security=security,
                                                      side=side,
                                                      avg_px=new_chore_journal_obj.chore.px,
                                                      total_qty=int(new_chore_journal_obj.chore.qty),
                                                      total_filled_qty=0, avg_fill_px=0,
                                                      total_fill_notional=0, last_update_fill_qty=0,
                                                      last_update_fill_px=0, total_cxled_qty=0,
                                                      avg_cxled_px=0, total_cxled_notional=0,
                                                      last_update_date_time=new_chore_journal_obj.chore_event_date_time,
                                                      chore_count=1)
        symbol_side_snapshot_obj = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_symbol_side_snapshot_http(
                symbol_side_snapshot_obj)
        return symbol_side_snapshot_obj

    def _set_avg_cxl_px(self, updated_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                        existing_symbol_side_snapshot: SymbolSideSnapshot):
        updated_symbol_side_snapshot.avg_cxled_px = (
            (self.get_local_px_or_notional(
                updated_symbol_side_snapshot.total_cxled_notional,
                existing_symbol_side_snapshot.security.sec_id) /
             updated_symbol_side_snapshot.total_cxled_qty)
            if updated_symbol_side_snapshot.total_cxled_qty != 0 else 0)

    def _handle_partial_cxl_qty_in_symbol_side_snapshot(self, updated_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                        existing_symbol_side_snapshot: SymbolSideSnapshot,
                                                        cxled_qty: int, cxled_px: float):
        # Doesn't return - updates passed object
        updated_symbol_side_snapshot.total_cxled_qty = (
                existing_symbol_side_snapshot.total_cxled_qty + cxled_qty)

        # cxled_px must be usd px when passed
        updated_symbol_side_snapshot.total_cxled_notional = (
                existing_symbol_side_snapshot.total_cxled_notional +
                (cxled_qty * cxled_px))
        self._set_avg_cxl_px(updated_symbol_side_snapshot, existing_symbol_side_snapshot)

    def _revert_partial_cxl_qty_in_symbol_side_snapshot(self, updated_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                        existing_symbol_side_snapshot: SymbolSideSnapshot,
                                                        cxled_qty: int, cxled_px: float):
        # Doesn't return - updates passed object
        updated_symbol_side_snapshot.total_cxled_qty = (
                existing_symbol_side_snapshot.total_cxled_qty - cxled_qty)

        # cxled_px must be usd px when passed
        updated_symbol_side_snapshot.total_cxled_notional = (
                existing_symbol_side_snapshot.total_cxled_notional -
                (cxled_qty * cxled_px))
        self._set_avg_cxl_px(updated_symbol_side_snapshot, existing_symbol_side_snapshot)

    def _handle_unfilled_cxl_in_symbol_side_snapshot(
            self, updated_symbol_side_snapshot_obj: SymbolSideSnapshotBaseModel,
            symbol_side_snapshot_obj: SymbolSideSnapshot, chore_snapshot_obj: ChoreSnapshot):
        unfilled_qty = self.get_residual_qty_post_chore_dod(chore_snapshot_obj)
        unfilled_notional = (
                unfilled_qty *
                self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                chore_snapshot_obj.chore_brief.security.sec_id))
        updated_symbol_side_snapshot_obj.total_cxled_qty = int(
            symbol_side_snapshot_obj.total_cxled_qty + unfilled_qty)
        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                symbol_side_snapshot_obj.total_cxled_notional + unfilled_notional)
        updated_symbol_side_snapshot_obj.avg_cxled_px = (
                self.get_local_px_or_notional(updated_symbol_side_snapshot_obj.total_cxled_notional,
                                              symbol_side_snapshot_obj.security.sec_id) /
                updated_symbol_side_snapshot_obj.total_cxled_qty) \
            if updated_symbol_side_snapshot_obj.total_cxled_qty != 0 else 0

    def update_symbol_side_snapshot_avg_px_post_amend(
            self, updated_symbol_side_snapshot_obj: SymbolSideSnapshotBaseModel,
            symbol_side_snapshot_obj: SymbolSideSnapshot,
            last_px: float, last_qty: int, amended_px: float, amended_qty: int | None = None):
        current_cumulative_notional = (symbol_side_snapshot_obj.avg_px *
                                       symbol_side_snapshot_obj.total_qty)
        # not calculating notional with usd px since avg_px is in local px
        old_chore_notional = last_qty * last_px
        if amended_qty:
            # chore qty is increased to amended qty if qty is amended up
            new_chore_notional = amended_qty * amended_px
            new_cumulative_notional = (
                    current_cumulative_notional - old_chore_notional + new_chore_notional)
            updated_symbol_side_snapshot_obj.avg_px = (
                    new_cumulative_notional / updated_symbol_side_snapshot_obj.total_qty)
        else:
            # chore qty stays unchanged if qty is amended dn
            new_chore_notional = last_qty * amended_px
            new_cumulative_notional = (
                    current_cumulative_notional - old_chore_notional + new_chore_notional)
            updated_symbol_side_snapshot_obj.avg_px = (
                    new_cumulative_notional / symbol_side_snapshot_obj.total_qty)

    async def _create_update_symbol_side_snapshot_from_chore_journal(
            self, chore_journal: ChoreJournal, chore_snapshot_obj: ChoreSnapshot) -> SymbolSideSnapshot | None:
        async with SymbolSideSnapshot.reentrant_lock:
            symbol_side_snapshot_objs = (
                self.plan_cache.get_symbol_side_snapshot_from_symbol(chore_journal.chore.security.sec_id))

            # If no symbol_side_snapshot for symbol-side of received chore_journal
            if symbol_side_snapshot_objs is None:
                if chore_journal.chore_event == ChoreEventType.OE_NEW:
                    created_symbol_side_snapshot = await self._create_symbol_side_snapshot_for_new_chore(chore_journal)
                    return created_symbol_side_snapshot
                else:
                    err_str_: str = (f"No OE_NEW detected for chore_journal_key: "
                                     f"{StreetBookServiceRoutesCallbackBaseNativeOverride.get_chore_journal_log_key(chore_journal)} "
                                     f"failed to create symbol_side_snapshot ;;; {chore_journal=}")
                    logging.error(err_str_)
                    return
            # If symbol_side_snapshot exists for chore_id from chore_journal
            else:
                symbol_side_snapshot_obj, _ = symbol_side_snapshot_objs
                updated_symbol_side_snapshot_obj = SymbolSideSnapshotBaseModel(id=symbol_side_snapshot_obj.id)
                match chore_journal.chore_event:
                    case ChoreEventType.OE_NEW:
                        updated_symbol_side_snapshot_obj.chore_count = symbol_side_snapshot_obj.chore_count + 1
                        if chore_journal.chore.px:
                            updated_symbol_side_snapshot_obj.avg_px = \
                                avg_of_new_val_sum_to_avg(symbol_side_snapshot_obj.avg_px,
                                                          chore_journal.chore.px,
                                                          updated_symbol_side_snapshot_obj.chore_count)
                        updated_symbol_side_snapshot_obj.total_qty = int(
                            symbol_side_snapshot_obj.total_qty + chore_journal.chore.qty)
                        updated_symbol_side_snapshot_obj.last_update_date_time = chore_journal.chore_event_date_time
                    case (ChoreEventType.OE_CXL_ACK | ChoreEventType.OE_UNSOL_CXL | ChoreEventType.OE_INT_REJ |
                          ChoreEventType.OE_BRK_REJ | ChoreEventType.OE_EXH_REJ):
                        self._handle_unfilled_cxl_in_symbol_side_snapshot(
                            updated_symbol_side_snapshot_obj, symbol_side_snapshot_obj, chore_snapshot_obj)
                        updated_symbol_side_snapshot_obj.last_update_date_time = chore_journal.chore_event_date_time

                    case ChoreEventType.OE_LAPSE:
                        lapsed_qty = chore_snapshot_obj.last_lapsed_qty
                        cxled_px = self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                   chore_snapshot_obj.chore_brief.security.sec_id)
                        self._handle_partial_cxl_qty_in_symbol_side_snapshot(
                            updated_symbol_side_snapshot_obj, symbol_side_snapshot_obj, lapsed_qty, cxled_px)
                        updated_symbol_side_snapshot_obj.last_update_date_time = chore_journal.chore_event_date_time

                    case ChoreEventType.OE_AMD_DN_UNACK | ChoreEventType.OE_AMD_UP_UNACK | ChoreEventType.OE_AMD_ACK:
                        chore_event = self.pending_amend_type(chore_journal, chore_snapshot_obj)

                        if chore_event is None:
                            # pending_amend_type must have logged error msg
                            return None

                        if chore_event == ChoreEventType.OE_AMD_DN_UNACK:
                            amend_dn_qty = chore_snapshot_obj.pending_amend_dn_qty
                            amend_dn_px = chore_snapshot_obj.pending_amend_dn_px

                            if amend_dn_px:
                                last_px = chore_snapshot_obj.chore_brief.px + amend_dn_px
                            else:
                                last_px = chore_snapshot_obj.chore_brief.px

                            if amend_dn_qty:
                                # putting amended dn qty to cxled_qty and updating notional and avg_cxled_px
                                cxled_px = self.get_usd_px(last_px,
                                                           chore_snapshot_obj.chore_brief.security.sec_id)
                                self._handle_partial_cxl_qty_in_symbol_side_snapshot(
                                    updated_symbol_side_snapshot_obj, symbol_side_snapshot_obj,
                                    amend_dn_qty, cxled_px)

                            if amend_dn_px:
                                last_px = chore_snapshot_obj.chore_brief.px + amend_dn_px
                                # same qty since amend_dn has no affect on qty
                                last_qty = chore_snapshot_obj.chore_brief.qty

                                self.update_symbol_side_snapshot_avg_px_post_amend(
                                    updated_symbol_side_snapshot_obj, symbol_side_snapshot_obj, last_px,
                                    last_qty, chore_snapshot_obj.chore_brief.px)
                        else:
                            amend_up_qty = chore_snapshot_obj.pending_amend_up_qty
                            amend_up_px = chore_snapshot_obj.pending_amend_up_px

                            updated_symbol_side_snapshot_obj.total_qty = (
                                    symbol_side_snapshot_obj.total_qty + amend_up_qty)
                            if amend_up_qty:
                                if chore_snapshot_obj.chore_status in [ChoreStatusType.OE_DOD,
                                                                       ChoreStatusType.OE_OVER_CXLED]:
                                    # AMD: handling amend_up post DOD/OVER_CXL - adding amended up qty to cxled_qty
                                    updated_symbol_side_snapshot_obj.total_cxled_qty = (
                                            symbol_side_snapshot_obj.total_cxled_qty + amend_up_qty)
                                    if not amend_up_px:
                                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                                                symbol_side_snapshot_obj.total_cxled_notional +
                                                (amend_up_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                                chore_snapshot_obj.chore_brief.
                                                                                security.sec_id)))
                                    else:
                                        last_px = chore_snapshot_obj.chore_brief.px - amend_up_px
                                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                                                symbol_side_snapshot_obj.total_cxled_notional +
                                                (amend_up_qty * self.get_usd_px(last_px,
                                                                                chore_snapshot_obj.chore_brief.
                                                                                security.sec_id)))
                                    updated_symbol_side_snapshot_obj.avg_cxled_px = (
                                        (self.get_local_px_or_notional(
                                            updated_symbol_side_snapshot_obj.total_cxled_notional,
                                            symbol_side_snapshot_obj.security.sec_id) /
                                         updated_symbol_side_snapshot_obj.total_cxled_qty)
                                        if updated_symbol_side_snapshot_obj.total_cxled_qty != 0 else 0)
                                # else not required: no cxl handling is required in amend up if chore is not DOD

                            if amend_up_px:
                                last_px = chore_snapshot_obj.chore_brief.px - amend_up_px
                                if amend_up_qty:
                                    last_qty = chore_snapshot_obj.chore_brief.qty - amend_up_qty
                                    amended_qty = chore_snapshot_obj.chore_brief.qty
                                else:
                                    last_qty = chore_snapshot_obj.chore_brief.qty - amend_up_qty
                                    amended_qty = None

                                self.update_symbol_side_snapshot_avg_px_post_amend(
                                    updated_symbol_side_snapshot_obj, symbol_side_snapshot_obj, last_px,
                                    last_qty, chore_snapshot_obj.chore_brief.px, amended_qty)

                        updated_symbol_side_snapshot_obj.last_update_date_time = chore_journal.chore_event_date_time

                    case ChoreEventType.OE_AMD_REJ:
                        chore_event = self.pending_amend_type(chore_journal, chore_snapshot_obj)

                        if chore_event is None:
                            # pending_amend_type must have logged error msg
                            return None

                        if chore_event == ChoreEventType.OE_AMD_DN_UNACK:
                            amend_dn_qty = chore_snapshot_obj.pending_amend_dn_qty
                            amend_dn_px = chore_snapshot_obj.pending_amend_dn_px

                            if amend_dn_qty:
                                # putting amended dn qty to cxled_qty and updating notional and avg_cxled_px
                                cxled_px = self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                           chore_snapshot_obj.chore_brief.security.sec_id)
                                self._revert_partial_cxl_qty_in_symbol_side_snapshot(
                                    updated_symbol_side_snapshot_obj, symbol_side_snapshot_obj,
                                    amend_dn_qty, cxled_px)

                            if amend_dn_px:
                                last_px = chore_snapshot_obj.chore_brief.px - amend_dn_px
                                # same qty since amend_dn has no affect on qty
                                last_qty = chore_snapshot_obj.chore_brief.qty

                                self.update_symbol_side_snapshot_avg_px_post_amend(
                                    updated_symbol_side_snapshot_obj, symbol_side_snapshot_obj, last_px,
                                    last_qty, chore_snapshot_obj.chore_brief.px)
                        else:
                            amend_up_qty = chore_snapshot_obj.pending_amend_up_qty
                            amend_up_px = chore_snapshot_obj.pending_amend_up_px

                            updated_symbol_side_snapshot_obj.total_qty = (
                                    symbol_side_snapshot_obj.total_qty - amend_up_qty)

                            if amend_up_px:
                                last_px = chore_snapshot_obj.chore_brief.px + amend_up_px
                                if amend_up_qty:
                                    last_qty = chore_snapshot_obj.chore_brief.qty + amend_up_qty
                                    amended_qty = chore_snapshot_obj.chore_brief.qty
                                else:
                                    last_qty = chore_snapshot_obj.chore_brief.qty
                                    amended_qty = None

                                self.update_symbol_side_snapshot_avg_px_post_amend(
                                    updated_symbol_side_snapshot_obj, symbol_side_snapshot_obj, last_px,
                                    last_qty, chore_snapshot_obj.chore_brief.px, amended_qty)

                        updated_symbol_side_snapshot_obj.last_update_date_time = chore_journal.chore_event_date_time

                    case other_:
                        err_str_ = f"Unsupported PlanEventType for symbol_side_snapshot update {other_} " \
                                   f"{StreetBookServiceRoutesCallbackBaseNativeOverride.get_chore_journal_log_key(chore_journal)}"
                        logging.error(err_str_)
                        return

                updated_symbol_side_snapshot_obj_dict = updated_symbol_side_snapshot_obj.to_dict(exclude_none=True)
                updated_symbol_side_snapshot_obj = \
                    await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                           underlying_partial_update_symbol_side_snapshot_http(updated_symbol_side_snapshot_obj_dict))
                return updated_symbol_side_snapshot_obj

    def _handle_cxl_qty_in_plan_status_buy_side(
            self, update_plan_status_obj: PlanStatus, chore_snapshot: ChoreSnapshot,
            chore_journal_obj: ChoreJournal, cxled_qty: int):
        update_plan_status_obj.total_open_buy_qty -= cxled_qty
        update_plan_status_obj.total_open_buy_notional -= \
            (cxled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                         chore_snapshot.chore_brief.security.sec_id))
        update_plan_status_obj.total_cxl_buy_qty += int(cxled_qty)
        update_plan_status_obj.total_cxl_buy_notional += \
            cxled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                        chore_snapshot.chore_brief.security.sec_id)
        update_plan_status_obj.avg_cxl_buy_px = (
            (self.get_local_px_or_notional(update_plan_status_obj.total_cxl_buy_notional,
                                           chore_journal_obj.chore.security.sec_id) / update_plan_status_obj.total_cxl_buy_qty)
            if update_plan_status_obj.total_cxl_buy_qty != 0 else 0)
        update_plan_status_obj.total_cxl_exposure = \
            update_plan_status_obj.total_cxl_buy_notional - \
            update_plan_status_obj.total_cxl_sell_notional

    def _handle_cxl_qty_in_plan_status_sell_side(
            self, update_plan_status_obj: PlanStatus, chore_snapshot: ChoreSnapshot,
            chore_journal_obj: ChoreJournal, cxled_qty: int):
        update_plan_status_obj.total_open_sell_qty -= cxled_qty
        update_plan_status_obj.total_open_sell_notional -= \
            (cxled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                         chore_snapshot.chore_brief.security.sec_id))
        update_plan_status_obj.total_cxl_sell_qty += int(cxled_qty)
        update_plan_status_obj.total_cxl_sell_notional += \
            cxled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                        chore_snapshot.chore_brief.security.sec_id)
        update_plan_status_obj.avg_cxl_sell_px = (
            (self.get_local_px_or_notional(update_plan_status_obj.total_cxl_sell_notional,
                                           chore_journal_obj.chore.security.sec_id) / update_plan_status_obj.total_cxl_sell_qty)
            if update_plan_status_obj.total_cxl_sell_qty != 0 else 0)
        update_plan_status_obj.total_cxl_exposure = \
            update_plan_status_obj.total_cxl_buy_notional - \
            update_plan_status_obj.total_cxl_sell_notional

    async def _update_plan_status_from_chore_journal(self, chore_journal_obj: ChoreJournal,
                                                      chore_snapshot: ChoreSnapshot,
                                                      symbol_side_snapshot: SymbolSideSnapshot,
                                                      plan_brief: PlanBrief):
        plan_limits_tuple = self.plan_cache.get_plan_limits()

        async with PlanStatus.reentrant_lock:
            plan_status_tuple = self.plan_cache.get_plan_status()

            if plan_limits_tuple is not None and plan_status_tuple is not None:
                plan_limits, _ = plan_limits_tuple
                update_plan_status_obj, _ = plan_status_tuple
                match chore_journal_obj.chore.side:
                    case Side.BUY:
                        match chore_journal_obj.chore_event:
                            case ChoreEventType.OE_NEW:
                                update_plan_status_obj.total_buy_qty += int(chore_journal_obj.chore.qty)
                                update_plan_status_obj.total_open_buy_qty += int(chore_journal_obj.chore.qty)
                                update_plan_status_obj.total_open_buy_notional += \
                                    chore_journal_obj.chore.qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                                  chore_snapshot.chore_brief.security.sec_id)
                            case (ChoreEventType.OE_CXL_ACK | ChoreEventType.OE_UNSOL_CXL | ChoreEventType.OE_INT_REJ |
                                  ChoreEventType.OE_BRK_REJ | ChoreEventType.OE_EXH_REJ):
                                total_buy_unfilled_qty = self.get_residual_qty_post_chore_dod(chore_snapshot)
                                self._handle_cxl_qty_in_plan_status_buy_side(
                                    update_plan_status_obj, chore_snapshot,
                                    chore_journal_obj, total_buy_unfilled_qty)
                            case ChoreEventType.OE_LAPSE:
                                lapse_qty = chore_snapshot.last_lapsed_qty
                                self._handle_cxl_qty_in_plan_status_buy_side(
                                    update_plan_status_obj, chore_snapshot, chore_journal_obj, lapse_qty)
                            case (ChoreEventType.OE_AMD_DN_UNACK | ChoreEventType.OE_AMD_UP_UNACK |
                                  ChoreEventType.OE_AMD_ACK):
                                pending_amend_type = self.pending_amend_type(chore_journal_obj, chore_snapshot)

                                if pending_amend_type == ChoreEventType.OE_AMD_DN_UNACK:
                                    amend_dn_px = chore_snapshot.pending_amend_dn_px
                                    amend_dn_qty = chore_snapshot.pending_amend_dn_qty

                                    if amend_dn_qty:
                                        if chore_snapshot.chore_status not in OTHER_TERMINAL_STATES:
                                            old_open_qty, new_open_qty, old_open_notional, new_open_notional = (
                                                self.get_old_n_new_open_qty_n_old_n_new_open_notional(
                                                    amend_dn_px, amend_dn_qty, pending_amend_type, chore_snapshot))
                                            update_plan_status_obj.total_open_buy_qty = (
                                                    update_plan_status_obj.total_open_buy_qty -
                                                    old_open_qty + new_open_qty)
                                            update_plan_status_obj.total_open_buy_notional = (
                                                    update_plan_status_obj.total_open_buy_notional -
                                                    old_open_notional + new_open_notional)

                                        update_plan_status_obj.total_cxl_buy_qty += amend_dn_qty
                                        if amend_dn_px:
                                            last_px = chore_snapshot.chore_brief.px + amend_dn_px
                                            update_plan_status_obj.total_cxl_buy_notional += \
                                                amend_dn_qty * self.get_usd_px(
                                                    last_px, chore_snapshot.chore_brief.security.sec_id)
                                        else:
                                            update_plan_status_obj.total_cxl_buy_notional += \
                                                amend_dn_qty * self.get_usd_px(
                                                    chore_snapshot.chore_brief.px,
                                                    chore_snapshot.chore_brief.security.sec_id)
                                        update_plan_status_obj.avg_cxl_buy_px = (
                                            (self.get_local_px_or_notional(
                                                update_plan_status_obj.total_cxl_buy_notional,
                                                chore_journal_obj.chore.security.sec_id) /
                                             update_plan_status_obj.total_cxl_buy_qty)
                                            if update_plan_status_obj.total_cxl_buy_qty != 0 else 0)

                                        update_plan_status_obj.total_cxl_exposure = \
                                            update_plan_status_obj.total_cxl_buy_notional - \
                                            update_plan_status_obj.total_cxl_sell_notional
                                    else:
                                        # if qty is not amended then px must be amended - else block will not
                                        # allow code to each here
                                        last_px = chore_snapshot.chore_brief.px + amend_dn_px
                                        old_open_notional = (
                                                update_plan_status_obj.total_open_buy_qty *
                                                self.get_usd_px(last_px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                                update_plan_status_obj.total_open_buy_qty *
                                                self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        update_plan_status_obj.total_open_buy_notional = (
                                                update_plan_status_obj.total_open_buy_notional - old_open_notional +
                                                new_open_notional)
                                else:
                                    amend_up_px = chore_snapshot.pending_amend_up_px
                                    amend_up_qty = chore_snapshot.pending_amend_up_qty

                                    if amend_up_qty:
                                        update_plan_status_obj.total_buy_qty += amend_up_qty
                                        if not chore_has_terminal_state(chore_snapshot):
                                            old_open_qty, new_open_qty, old_open_notional, new_open_notional = (
                                                self.get_old_n_new_open_qty_n_old_n_new_open_notional(
                                                    amend_up_px, amend_up_qty, pending_amend_type, chore_snapshot))

                                            update_plan_status_obj.total_open_buy_qty = (
                                                    update_plan_status_obj.total_open_buy_qty -
                                                    old_open_qty + new_open_qty)
                                            update_plan_status_obj.total_open_buy_notional = (
                                                    update_plan_status_obj.total_open_buy_notional -
                                                    old_open_notional + new_open_notional)

                                        # if chore is amended post DOD then adding amended up qty to cxled qty
                                        else:
                                            if chore_snapshot.chore_status in [ChoreStatusType.OE_DOD,
                                                                               ChoreStatusType.OE_OVER_CXLED]:
                                                if not amend_up_px:
                                                    additional_new_notional = (
                                                            amend_up_qty *
                                                            self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                            chore_snapshot.chore_brief.security.sec_id))
                                                else:
                                                    last_px = chore_snapshot.chore_brief.px - amend_up_px
                                                    additional_new_notional = (
                                                            amend_up_qty *
                                                            self.get_usd_px(last_px,
                                                                            chore_snapshot.chore_brief.security.sec_id))
                                                update_plan_status_obj.total_cxl_buy_qty += amend_up_qty
                                                update_plan_status_obj.total_cxl_buy_notional += additional_new_notional
                                                update_plan_status_obj.avg_cxl_buy_px = (
                                                    (self.get_local_px_or_notional(
                                                        update_plan_status_obj.total_cxl_buy_notional,
                                                        chore_journal_obj.chore.security.sec_id) /
                                                     update_plan_status_obj.total_cxl_buy_qty)
                                                    if update_plan_status_obj.total_cxl_buy_qty != 0 else 0)

                                                update_plan_status_obj.total_cxl_exposure = \
                                                    update_plan_status_obj.total_cxl_buy_notional - \
                                                    update_plan_status_obj.total_cxl_sell_notional
                                        # AMD: else not required: if chore is not DOD then amend up has no handling
                                        # for cxled qty

                                    else:
                                        # if qty is not amended then px must be amended - else block will not
                                        # allow code to each here
                                        last_px = chore_snapshot.chore_brief.px - amend_up_px
                                        old_open_notional = (
                                                update_plan_status_obj.total_open_buy_qty *
                                                self.get_usd_px(last_px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                                update_plan_status_obj.total_open_buy_qty *
                                                self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        update_plan_status_obj.total_open_buy_notional = (
                                                update_plan_status_obj.total_open_buy_notional - old_open_notional +
                                                new_open_notional)

                            case ChoreEventType.OE_AMD_REJ:
                                pending_amend_type = self.pending_amend_type(chore_journal_obj, chore_snapshot)

                                if pending_amend_type == ChoreEventType.OE_AMD_DN_UNACK:
                                    amend_dn_px = chore_snapshot.pending_amend_dn_px
                                    amend_dn_qty = chore_snapshot.pending_amend_dn_qty

                                    if amend_dn_qty:
                                        if chore_snapshot.chore_status not in NON_FILLED_TERMINAL_STATES:
                                            (amended_open_qty, reverted_open_qty, amended_open_notional, 
                                             reverted_open_notional) = (
                                                self.get_reverted_old_n_new_open_qty_n_old_n_new_open_notional(
                                                    amend_dn_px, amend_dn_qty, pending_amend_type, chore_snapshot))
                                            update_plan_status_obj.total_open_buy_qty = (
                                                    update_plan_status_obj.total_open_buy_qty -
                                                    amended_open_qty + reverted_open_qty)
                                            update_plan_status_obj.total_open_buy_notional = (
                                                    update_plan_status_obj.total_open_buy_notional -
                                                    amended_open_notional + reverted_open_notional)

                                        update_plan_status_obj.total_cxl_buy_qty -= amend_dn_qty
                                        if amend_dn_px:
                                            last_px = chore_snapshot.chore_brief.px
                                            update_plan_status_obj.total_cxl_buy_notional -= \
                                                amend_dn_qty * self.get_usd_px(
                                                    last_px, chore_snapshot.chore_brief.security.sec_id)
                                        else:
                                            update_plan_status_obj.total_cxl_buy_notional -= \
                                                amend_dn_qty * self.get_usd_px(
                                                    chore_snapshot.chore_brief.px,
                                                    chore_snapshot.chore_brief.security.sec_id)
                                        update_plan_status_obj.avg_cxl_buy_px = (
                                            (self.get_local_px_or_notional(
                                                update_plan_status_obj.total_cxl_buy_notional,
                                                chore_journal_obj.chore.security.sec_id) /
                                             update_plan_status_obj.total_cxl_buy_qty)
                                            if update_plan_status_obj.total_cxl_buy_qty != 0 else 0)

                                        update_plan_status_obj.total_cxl_exposure = \
                                            update_plan_status_obj.total_cxl_buy_notional - \
                                            update_plan_status_obj.total_cxl_sell_notional
                                    else:
                                        # if qty is not amended then px must be amended - else block will not
                                        # allow code to each here
                                        last_px = chore_snapshot.chore_brief.px
                                        old_open_notional = (
                                                update_plan_status_obj.total_open_buy_qty *
                                                self.get_usd_px(last_px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                                update_plan_status_obj.total_open_buy_qty *
                                                self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        update_plan_status_obj.total_open_buy_notional = (
                                                update_plan_status_obj.total_open_buy_notional - old_open_notional +
                                                new_open_notional)
                                else:
                                    amend_up_px = chore_snapshot.pending_amend_up_px
                                    amend_up_qty = chore_snapshot.pending_amend_up_qty

                                    if amend_up_qty:
                                        update_plan_status_obj.total_buy_qty -= amend_up_qty
                                        if chore_snapshot.chore_status not in NON_FILLED_TERMINAL_STATES:
                                            (amended_open_qty, reverted_open_qty, amended_open_notional,
                                             reverted_open_notional) = (
                                                self.get_reverted_old_n_new_open_qty_n_old_n_new_open_notional(
                                                    amend_up_px, amend_up_qty, pending_amend_type, chore_snapshot))

                                            update_plan_status_obj.total_open_buy_qty = (
                                                    update_plan_status_obj.total_open_buy_qty -
                                                    amended_open_qty + reverted_open_qty)
                                            update_plan_status_obj.total_open_buy_notional = (
                                                    update_plan_status_obj.total_open_buy_notional -
                                                    amended_open_notional + reverted_open_notional)

                                    else:
                                        # if qty is not amended then px must be amended - else block will not
                                        # allow code to each here
                                        last_px = chore_snapshot.chore_brief.px + amend_up_px
                                        old_open_notional = (
                                                update_plan_status_obj.total_open_buy_qty *
                                                self.get_usd_px(last_px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                                update_plan_status_obj.total_open_buy_qty *
                                                self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        update_plan_status_obj.total_open_buy_notional = (
                                                update_plan_status_obj.total_open_buy_notional - old_open_notional +
                                                new_open_notional)
                            case other_:
                                err_str_ = f"Unsupported Chore Event type {other_}, " \
                                           f"chore_journal_key: {StreetBookServiceRoutesCallbackBaseNativeOverride.get_chore_journal_log_key(chore_journal_obj)}"
                                logging.error(err_str_)
                                return
                        if update_plan_status_obj.total_open_buy_qty == 0:
                            update_plan_status_obj.avg_open_buy_px = 0
                        else:
                            update_plan_status_obj.avg_open_buy_px = \
                                (self.get_local_px_or_notional(update_plan_status_obj.total_open_buy_notional,
                                                               chore_journal_obj.chore.security.sec_id) /
                                 update_plan_status_obj.total_open_buy_qty)
                    case Side.SELL:
                        match chore_journal_obj.chore_event:
                            case ChoreEventType.OE_NEW:
                                update_plan_status_obj.total_sell_qty += int(chore_journal_obj.chore.qty)
                                update_plan_status_obj.total_open_sell_qty += int(chore_journal_obj.chore.qty)
                                update_plan_status_obj.total_open_sell_notional += \
                                    chore_journal_obj.chore.qty * self.get_usd_px(chore_journal_obj.chore.px,
                                                                                  chore_journal_obj.chore.security.sec_id)
                            case (ChoreEventType.OE_CXL_ACK | ChoreEventType.OE_UNSOL_CXL | ChoreEventType.OE_INT_REJ |
                                  ChoreEventType.OE_BRK_REJ | ChoreEventType.OE_EXH_REJ):
                                total_sell_unfilled_qty = self.get_residual_qty_post_chore_dod(chore_snapshot)
                                self._handle_cxl_qty_in_plan_status_sell_side(
                                    update_plan_status_obj, chore_snapshot,
                                    chore_journal_obj, total_sell_unfilled_qty)
                            case ChoreEventType.OE_LAPSE:
                                lapse_qty = chore_snapshot.last_lapsed_qty
                                self._handle_cxl_qty_in_plan_status_sell_side(
                                    update_plan_status_obj, chore_snapshot, chore_journal_obj, lapse_qty)
                            case (ChoreEventType.OE_AMD_DN_UNACK | ChoreEventType.OE_AMD_UP_UNACK |
                                  ChoreEventType.OE_AMD_ACK):
                                pending_amend_type = self.pending_amend_type(chore_journal_obj, chore_snapshot)

                                if pending_amend_type == ChoreEventType.OE_AMD_DN_UNACK:
                                    amend_dn_px = chore_snapshot.pending_amend_dn_px
                                    amend_dn_qty = chore_snapshot.pending_amend_dn_qty

                                    if amend_dn_qty:
                                        if chore_snapshot.chore_status not in OTHER_TERMINAL_STATES:
                                            old_open_qty, new_open_qty, old_open_notional, new_open_notional = (
                                                self.get_old_n_new_open_qty_n_old_n_new_open_notional(
                                                    amend_dn_px, amend_dn_qty, pending_amend_type, chore_snapshot))

                                            update_plan_status_obj.total_open_sell_qty = (
                                                    update_plan_status_obj.total_open_sell_qty -
                                                    old_open_qty + new_open_qty)
                                            update_plan_status_obj.total_open_sell_notional = (
                                                    update_plan_status_obj.total_open_sell_notional -
                                                    old_open_notional + new_open_notional)

                                        update_plan_status_obj.total_cxl_sell_qty += amend_dn_qty
                                        if amend_dn_px:
                                            last_px = chore_snapshot.chore_brief.px + amend_dn_px
                                            update_plan_status_obj.total_cxl_sell_notional += \
                                                amend_dn_qty * self.get_usd_px(
                                                    last_px, chore_snapshot.chore_brief.security.sec_id)
                                        else:
                                            update_plan_status_obj.total_cxl_sell_notional += \
                                                amend_dn_qty * self.get_usd_px(
                                                    chore_snapshot.chore_brief.px,
                                                    chore_snapshot.chore_brief.security.sec_id)

                                        update_plan_status_obj.avg_cxl_sell_px = (
                                            (self.get_local_px_or_notional(
                                                update_plan_status_obj.total_cxl_sell_notional,
                                                chore_journal_obj.chore.security.sec_id) /
                                             update_plan_status_obj.total_cxl_sell_qty)
                                            if update_plan_status_obj.total_cxl_sell_qty != 0 else 0)

                                        update_plan_status_obj.total_cxl_exposure = \
                                            update_plan_status_obj.total_cxl_buy_notional - \
                                            update_plan_status_obj.total_cxl_sell_notional

                                    else:
                                        # if qty is not amended then px must be amended - else block will not
                                        # allow code to each here
                                        last_px = chore_snapshot.chore_brief.px + amend_dn_px
                                        old_open_notional = (
                                                update_plan_status_obj.total_open_sell_qty *
                                                self.get_usd_px(last_px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                                update_plan_status_obj.total_open_sell_qty *
                                                self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        update_plan_status_obj.total_open_sell_notional = (
                                                update_plan_status_obj.total_open_sell_notional - old_open_notional +
                                                new_open_notional)
                                else:
                                    amend_up_px = chore_snapshot.pending_amend_up_px
                                    amend_up_qty = chore_snapshot.pending_amend_up_qty

                                    if amend_up_qty:
                                        update_plan_status_obj.total_sell_qty += amend_up_qty
                                        if not chore_has_terminal_state(chore_snapshot):
                                            old_open_qty, new_open_qty, old_open_notional, new_open_notional = (
                                                self.get_old_n_new_open_qty_n_old_n_new_open_notional(
                                                    amend_up_px, amend_up_qty, pending_amend_type, chore_snapshot))

                                            update_plan_status_obj.total_open_sell_qty = (
                                                    update_plan_status_obj.total_open_sell_qty -
                                                    old_open_qty + new_open_qty)
                                            update_plan_status_obj.total_open_sell_notional = (
                                                    update_plan_status_obj.total_open_sell_notional -
                                                    old_open_notional + new_open_notional)

                                        # if chore is amended post DOD then adding amended up qty to cxled qty
                                        else:
                                            if chore_snapshot.chore_status in [ChoreStatusType.OE_DOD,
                                                                               ChoreStatusType.OE_OVER_CXLED]:
                                                if not amend_up_px:
                                                    additional_new_notional = (
                                                            amend_up_qty *
                                                            self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                            chore_snapshot.chore_brief.security.sec_id))
                                                else:
                                                    last_px = chore_snapshot.chore_brief.px - amend_up_px
                                                    additional_new_notional = (
                                                            amend_up_qty *
                                                            self.get_usd_px(last_px,
                                                                            chore_snapshot.chore_brief.security.sec_id))
                                                update_plan_status_obj.total_cxl_sell_qty += amend_up_qty
                                                update_plan_status_obj.total_cxl_sell_notional += additional_new_notional
                                                update_plan_status_obj.avg_cxl_sell_px = (
                                                    (self.get_local_px_or_notional(
                                                        update_plan_status_obj.total_cxl_sell_notional,
                                                        chore_journal_obj.chore.security.sec_id) /
                                                     update_plan_status_obj.total_cxl_sell_qty)
                                                    if update_plan_status_obj.total_cxl_sell_qty != 0 else 0)

                                                update_plan_status_obj.total_cxl_exposure = \
                                                    update_plan_status_obj.total_cxl_buy_notional - \
                                                    update_plan_status_obj.total_cxl_sell_notional
                                        # AMD: else not required: if chore is not DOD then amend up has no handling
                                        # for cxled qty

                                    else:
                                        # if qty is not amended then px must be amended - else block will not
                                        # allow code to each here
                                        last_px = chore_snapshot.chore_brief.px - amend_up_px
                                        old_open_notional = (
                                                update_plan_status_obj.total_open_sell_qty *
                                                self.get_usd_px(last_px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                                update_plan_status_obj.total_open_sell_qty *
                                                self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        update_plan_status_obj.total_open_sell_notional = (
                                                update_plan_status_obj.total_open_sell_notional - old_open_notional +
                                                new_open_notional)
                            case ChoreEventType.OE_AMD_REJ:
                                pending_amend_type = self.pending_amend_type(chore_journal_obj, chore_snapshot)

                                if pending_amend_type == ChoreEventType.OE_AMD_DN_UNACK:
                                    amend_dn_px = chore_snapshot.pending_amend_dn_px
                                    amend_dn_qty = chore_snapshot.pending_amend_dn_qty

                                    if amend_dn_qty:
                                        if chore_snapshot.chore_status not in NON_FILLED_TERMINAL_STATES:
                                            (amended_open_qty, reverted_open_qty, amended_open_notional,
                                             reverted_open_notional) = (
                                                self.get_reverted_old_n_new_open_qty_n_old_n_new_open_notional(
                                                    amend_dn_px, amend_dn_qty, pending_amend_type, chore_snapshot))
                                            update_plan_status_obj.total_open_sell_qty = (
                                                    update_plan_status_obj.total_open_sell_qty -
                                                    amended_open_qty + reverted_open_qty)
                                            update_plan_status_obj.total_open_sell_notional = (
                                                    update_plan_status_obj.total_open_sell_notional -
                                                    amended_open_notional + reverted_open_notional)

                                        update_plan_status_obj.total_cxl_sell_qty -= amend_dn_qty
                                        if amend_dn_px:
                                            last_px = chore_snapshot.chore_brief.px
                                            update_plan_status_obj.total_cxl_sell_notional -= \
                                                amend_dn_qty * self.get_usd_px(
                                                    last_px, chore_snapshot.chore_brief.security.sec_id)
                                        else:
                                            update_plan_status_obj.total_cxl_sell_notional -= \
                                                amend_dn_qty * self.get_usd_px(
                                                    chore_snapshot.chore_brief.px,
                                                    chore_snapshot.chore_brief.security.sec_id)
                                        update_plan_status_obj.avg_cxl_sell_px = (
                                            (self.get_local_px_or_notional(
                                                update_plan_status_obj.total_cxl_sell_notional,
                                                chore_journal_obj.chore.security.sec_id) /
                                             update_plan_status_obj.total_cxl_sell_qty)
                                            if update_plan_status_obj.total_cxl_sell_qty != 0 else 0)

                                        update_plan_status_obj.total_cxl_exposure = \
                                            update_plan_status_obj.total_cxl_buy_notional - \
                                            update_plan_status_obj.total_cxl_sell_notional
                                    else:
                                        # if qty is not amended then px must be amended - else block will not
                                        # allow code to each here
                                        last_px = chore_snapshot.chore_brief.px
                                        old_open_notional = (
                                                update_plan_status_obj.total_open_sell_qty *
                                                self.get_usd_px(last_px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                                update_plan_status_obj.total_open_sell_qty *
                                                self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        update_plan_status_obj.total_open_sell_notional = (
                                                update_plan_status_obj.total_open_sell_notional - old_open_notional +
                                                new_open_notional)
                                else:
                                    amend_up_px = chore_snapshot.pending_amend_up_px
                                    amend_up_qty = chore_snapshot.pending_amend_up_qty

                                    if amend_up_qty:
                                        update_plan_status_obj.total_sell_qty -= amend_up_qty
                                        if chore_snapshot.chore_status not in NON_FILLED_TERMINAL_STATES:
                                            (amended_open_qty, reverted_open_qty, amended_open_notional,
                                             reverted_open_notional) = (
                                                self.get_reverted_old_n_new_open_qty_n_old_n_new_open_notional(
                                                    amend_up_px, amend_up_qty, pending_amend_type, chore_snapshot))

                                            update_plan_status_obj.total_open_sell_qty = (
                                                    update_plan_status_obj.total_open_sell_qty -
                                                    amended_open_qty + reverted_open_qty)
                                            update_plan_status_obj.total_open_sell_notional = (
                                                    update_plan_status_obj.total_open_sell_notional -
                                                    amended_open_notional + reverted_open_notional)

                                        # if chore is amended post DOD then adding amended up qty to cxled qty
                                        else:
                                            if amend_up_qty:
                                                last_px = chore_snapshot.chore_brief.px
                                                additional_new_notional = (
                                                        amend_up_qty *
                                                        self.get_usd_px(last_px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                                                update_plan_status_obj.total_cxl_sell_qty -= amend_up_qty
                                                update_plan_status_obj.total_cxl_sell_notional -= additional_new_notional
                                                update_plan_status_obj.avg_cxl_sell_px = (
                                                    (self.get_local_px_or_notional(
                                                        update_plan_status_obj.total_cxl_sell_notional,
                                                        chore_journal_obj.chore.security.sec_id) /
                                                     update_plan_status_obj.total_cxl_sell_qty)
                                                    if update_plan_status_obj.total_cxl_sell_qty != 0 else 0)

                                                update_plan_status_obj.total_cxl_exposure = \
                                                    update_plan_status_obj.total_cxl_buy_notional - \
                                                    update_plan_status_obj.total_cxl_sell_notional
                                        # AMD: else not required: if chore is not DOD then amend up has no handling
                                        # for cxled qty

                                    else:
                                        # if qty is not amended then px must be amended - else block will not
                                        # allow code to each here
                                        last_px = chore_snapshot.chore_brief.px + amend_up_px
                                        old_open_notional = (
                                                update_plan_status_obj.total_open_sell_qty *
                                                self.get_usd_px(last_px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                                update_plan_status_obj.total_open_sell_qty *
                                                self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                                        update_plan_status_obj.total_open_sell_notional = (
                                                update_plan_status_obj.total_open_sell_notional - old_open_notional +
                                                new_open_notional)
                            case other_:
                                err_str_ = f"Unsupported Chore Event type {other_} " \
                                           f"chore_journal_key: {StreetBookServiceRoutesCallbackBaseNativeOverride.get_chore_journal_log_key(chore_journal_obj)}"
                                logging.error(err_str_)
                                return
                        if update_plan_status_obj.total_open_sell_qty == 0:
                            update_plan_status_obj.avg_open_sell_px = 0
                        else:
                            update_plan_status_obj.avg_open_sell_px = \
                                self.get_local_px_or_notional(update_plan_status_obj.total_open_sell_notional,
                                                              chore_journal_obj.chore.security.sec_id) / \
                                update_plan_status_obj.total_open_sell_qty
                    case other_:
                        err_str_ = f"Unsupported Side Type {other_} received in chore_journal_key: " \
                                   f"{StreetBookServiceRoutesCallbackBaseNativeOverride.get_chore_journal_log_key(chore_journal_obj)} while updating plan_status;;; " \
                                   f"{chore_journal_obj = }"
                        logging.error(err_str_)
                        return
                update_plan_status_obj.total_chore_qty = \
                    int(update_plan_status_obj.total_buy_qty + update_plan_status_obj.total_sell_qty)
                update_plan_status_obj.total_open_exposure = (update_plan_status_obj.total_open_buy_notional -
                                                               update_plan_status_obj.total_open_sell_notional)
                if update_plan_status_obj.total_fill_buy_notional < update_plan_status_obj.total_fill_sell_notional:
                    update_plan_status_obj.balance_notional = \
                        plan_limits.max_single_leg_notional - update_plan_status_obj.total_fill_buy_notional
                else:
                    update_plan_status_obj.balance_notional = \
                        plan_limits.max_single_leg_notional - update_plan_status_obj.total_fill_sell_notional

                updated_residual = self.__get_residual_obj(chore_snapshot.chore_brief.side, plan_brief)
                if updated_residual is not None:
                    update_plan_status_obj.residual = updated_residual

                # Updating plan_state as paused if limits get breached
                is_cxl: bool = False
                if chore_journal_obj.chore_event == ChoreEventType.OE_CXL_ACK or (
                        chore_journal_obj.chore_event == ChoreEventType.OE_UNSOL_CXL):
                    is_cxl = True
                await self._pause_plan_if_limits_breached(update_plan_status_obj, plan_limits, plan_brief,
                                                           symbol_side_snapshot, is_cxl=is_cxl)

                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_update_plan_status_http(
                    update_plan_status_obj)
            else:
                logging.error(f"error: either tuple of plan_status or plan_limits received as None from cache;;; "
                              f"{plan_status_tuple = }, {plan_limits_tuple = }")
                return

    def _handle_cxled_qty_in_plan_brief(
            self, fetched_open_qty: int, fetched_open_notional: float, fetched_all_bkr_cxlled_qty: int,
            chore_snapshot: ChoreSnapshot, cxled_qty: int) -> Tuple[int, float, int]:
        open_qty = int(fetched_open_qty - cxled_qty)
        open_notional = (
                fetched_open_notional - (
                cxled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                            chore_snapshot.chore_brief.security.sec_id)))
        if fetched_all_bkr_cxlled_qty is None:
            all_bkr_cxlled_qty = int(cxled_qty)
        else:
            all_bkr_cxlled_qty = int(fetched_all_bkr_cxlled_qty + cxled_qty)
        return open_qty, open_notional, all_bkr_cxlled_qty

    def _get_amended_open_qty_n_notional(
            self, amend_px: float, amend_qty: int,
            chore_event: ChoreEventType, chore_snapshot: ChoreSnapshot,
            fetched_open_qty: int, fetched_open_notional: float):
        old_open_qty, new_open_qty, old_open_notional, new_open_notional = (
            self.get_old_n_new_open_qty_n_old_n_new_open_notional(
                amend_px, amend_qty, chore_event, chore_snapshot))

        open_qty = fetched_open_qty - old_open_qty + new_open_qty
        open_notional = fetched_open_notional - old_open_notional + new_open_notional
        return open_qty, open_notional

    def _get_reverted_open_qty_n_notional(
            self, amend_px: float, amend_qty: int,
            chore_event: ChoreEventType, chore_snapshot: ChoreSnapshot,
            fetched_open_qty: int, fetched_open_notional: float):
        amended_open_qty, reverted_open_qty, amended_open_notional, reverted_open_notional = (
            self.get_reverted_old_n_new_open_qty_n_old_n_new_open_notional(
                amend_px, amend_qty, chore_event, chore_snapshot))

        open_qty = fetched_open_qty - amended_open_qty + reverted_open_qty
        open_notional = fetched_open_notional - amended_open_notional + reverted_open_notional
        return open_qty, open_notional

    async def _update_plan_brief_from_chore_or_fill(self, chore_journal_or_fills_journal: ChoreJournal | FillsJournal,
                                                     chore_snapshot: ChoreSnapshot,
                                                     symbol_side_snapshot: SymbolSideSnapshot,
                                                     received_fill_after_dod: bool | None = None) -> PlanBrief | None:

        security = symbol_side_snapshot.security
        side = symbol_side_snapshot.side
        symbol = security.sec_id
        hedge_ratio: float = self.get_hedge_ratio()

        async with StreetBookServiceRoutesCallbackBaseNativeOverride.residual_compute_shared_lock:
            async with PlanBrief.reentrant_lock:
                plan_brief_tuple = self.plan_cache.get_plan_brief()

                plan_limits_tuple = self.plan_cache.get_plan_limits()

                if plan_brief_tuple is not None:
                    plan_brief_obj, _ = plan_brief_tuple
                    if plan_limits_tuple is not None:
                        plan_limits, _ = plan_limits_tuple

                        all_bkr_cxlled_qty = None
                        if side == Side.BUY:
                            fetched_open_qty = plan_brief_obj.pair_buy_side_bartering_brief.open_qty
                            fetched_open_notional = plan_brief_obj.pair_buy_side_bartering_brief.open_notional
                            fetched_all_bkr_cxlled_qty = plan_brief_obj.pair_buy_side_bartering_brief.all_bkr_cxlled_qty
                        else:
                            fetched_open_qty = plan_brief_obj.pair_sell_side_bartering_brief.open_qty
                            fetched_open_notional = plan_brief_obj.pair_sell_side_bartering_brief.open_notional
                            fetched_all_bkr_cxlled_qty = plan_brief_obj.pair_sell_side_bartering_brief.all_bkr_cxlled_qty

                        if isinstance(chore_journal_or_fills_journal, ChoreJournal):
                            chore_journal: ChoreJournal = chore_journal_or_fills_journal
                            if chore_journal.chore_event == ChoreEventType.OE_NEW:
                                # When chore_event is OE_NEW then just adding current chore's total qty to existing
                                # open_qty + total notional (total chore Qty * chore px) to exist open_notional
                                if fetched_open_qty is None:
                                    fetched_open_qty = 0
                                if fetched_open_notional is None:
                                    fetched_open_notional = 0
                                open_qty = fetched_open_qty + chore_snapshot.chore_brief.qty
                                open_notional = (
                                        fetched_open_notional + (
                                            chore_snapshot.chore_brief.qty *
                                            self.get_usd_px(chore_snapshot.chore_brief.px,
                                                            chore_snapshot.chore_brief.security.sec_id)))
                            elif chore_journal.chore_event in [ChoreEventType.OE_INT_REJ, ChoreEventType.OE_BRK_REJ,
                                                               ChoreEventType.OE_EXH_REJ]:
                                # When chore_event is OE_INT_REJ or OE_BRK_REJ or OE_EXH_REJ then just removing
                                # current chore's total qty from existing open_qty + total notional
                                # (total chore Qty * chore px) from existing open_notional
                                open_qty = fetched_open_qty - chore_snapshot.chore_brief.qty
                                open_notional = (
                                        fetched_open_notional - (
                                            chore_snapshot.chore_brief.qty *
                                            self.get_usd_px(chore_snapshot.chore_brief.px,
                                                            chore_snapshot.chore_brief.security.sec_id)))
                            elif chore_journal.chore_event in [ChoreEventType.OE_CXL_ACK, ChoreEventType.OE_UNSOL_CXL]:
                                # When chore_event is OE_CXL_ACK or OE_UNSOL_CXL then removing current chore's
                                # unfilled qty from existing open_qty + unfilled notional
                                # (unfilled chore Qty * chore px) from existing open_notional
                                unfilled_qty = self.get_residual_qty_post_chore_dod(chore_snapshot)
                                open_qty, open_notional, all_bkr_cxlled_qty = self._handle_cxled_qty_in_plan_brief(
                                    fetched_open_qty, fetched_open_notional, fetched_all_bkr_cxlled_qty,
                                    chore_snapshot, unfilled_qty)
                            elif chore_journal.chore_event == ChoreEventType.OE_LAPSE:
                                lapsed_qty = chore_snapshot.last_lapsed_qty
                                open_qty, open_notional, all_bkr_cxlled_qty = self._handle_cxled_qty_in_plan_brief(
                                    fetched_open_qty, fetched_open_notional, fetched_all_bkr_cxlled_qty,
                                    chore_snapshot, lapsed_qty)

                            elif chore_journal.chore_event in [ChoreEventType.OE_AMD_DN_UNACK,
                                                               ChoreEventType.OE_AMD_UP_UNACK,
                                                               ChoreEventType.OE_AMD_ACK]:
                                chore_event = self.pending_amend_type(chore_journal, chore_snapshot)

                                if chore_event == ChoreEventType.OE_AMD_DN_UNACK:
                                    amend_dn_qty = chore_snapshot.pending_amend_dn_qty
                                    amend_dn_px = chore_snapshot.pending_amend_dn_px

                                    if amend_dn_qty:
                                        all_bkr_cxlled_qty = fetched_all_bkr_cxlled_qty + amend_dn_qty

                                    if amend_dn_qty:
                                        if chore_snapshot.chore_status not in OTHER_TERMINAL_STATES:
                                            open_qty, open_notional = self._get_amended_open_qty_n_notional(
                                                amend_dn_px, amend_dn_qty, chore_event, chore_snapshot,
                                                fetched_open_qty, fetched_open_notional)
                                        else:
                                            open_qty = fetched_open_qty
                                            open_notional = fetched_open_notional
                                    else:
                                        # if qty is not amended then px must be amended else code can't block in
                                        # chore_snapshot update
                                        open_qty = fetched_open_qty
                                        last_px = chore_snapshot.chore_brief.px + amend_dn_px
                                        old_open_notional = (
                                                open_qty * self.get_usd_px(last_px,
                                                                           chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                                open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                           chore_snapshot.chore_brief.security.sec_id))
                                        open_notional = fetched_open_notional - old_open_notional + new_open_notional
                                else:
                                    amend_up_qty = chore_snapshot.pending_amend_up_qty
                                    amend_up_px = chore_snapshot.pending_amend_up_px

                                    if not chore_has_terminal_state(chore_snapshot):
                                        if amend_up_qty:
                                            open_qty, open_notional = self._get_amended_open_qty_n_notional(
                                                amend_up_px, amend_up_qty, chore_event, chore_snapshot,
                                                fetched_open_qty, fetched_open_notional)
                                        else:
                                            # if qty is not amended then px must be amended else code can't block in
                                            # chore_snapshot update
                                            open_qty = fetched_open_qty
                                            last_px = chore_snapshot.chore_brief.px - amend_up_px
                                            old_open_notional = (
                                                    open_qty * self.get_usd_px(last_px,
                                                                               chore_snapshot.chore_brief.security.sec_id))
                                            new_open_notional = (
                                                    open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                               chore_snapshot.chore_brief.security.sec_id))
                                            open_notional = fetched_open_notional - old_open_notional + new_open_notional

                                    else:
                                        # if chore is in DOD state then whole qty is already in
                                        # cxled qty and no open chore exists to be updated
                                        open_qty = fetched_open_qty
                                        open_notional = fetched_open_notional

                                        # whatever is amended up post terminal state is put in cxled_qty
                                        if amend_up_qty and chore_snapshot.chore_status in [ChoreStatusType.OE_DOD,
                                                                                            ChoreStatusType.OE_OVER_CXLED]:
                                            all_bkr_cxlled_qty = fetched_all_bkr_cxlled_qty + amend_up_qty

                            elif chore_journal.chore_event == ChoreEventType.OE_AMD_REJ:
                                chore_event = self.pending_amend_type(chore_journal, chore_snapshot)

                                if chore_event == ChoreEventType.OE_AMD_DN_UNACK:
                                    amend_dn_qty = chore_snapshot.pending_amend_dn_qty
                                    amend_dn_px = chore_snapshot.pending_amend_dn_px

                                    if amend_dn_qty:
                                        all_bkr_cxlled_qty = fetched_all_bkr_cxlled_qty - amend_dn_qty

                                    if amend_dn_qty:
                                        if chore_snapshot.chore_status not in NON_FILLED_TERMINAL_STATES:
                                            open_qty, open_notional = self._get_reverted_open_qty_n_notional(
                                                amend_dn_px, amend_dn_qty, chore_event, chore_snapshot,
                                                fetched_open_qty, fetched_open_notional)
                                        else:
                                            open_qty = fetched_open_qty
                                            open_notional = fetched_open_notional
                                    else:
                                        # if qty is not amended then px must be amended else code can't block in
                                        # chore_snapshot update
                                        open_qty = fetched_open_qty
                                        last_px = chore_snapshot.chore_brief.px
                                        old_open_notional = (
                                                open_qty * self.get_usd_px(last_px,
                                                                           chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                                open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                           chore_snapshot.chore_brief.security.sec_id))
                                        open_notional = fetched_open_notional - old_open_notional + new_open_notional
                                else:
                                    amend_up_qty = chore_snapshot.pending_amend_up_qty
                                    amend_up_px = chore_snapshot.pending_amend_up_px

                                    if chore_snapshot.chore_status not in NON_FILLED_TERMINAL_STATES:
                                        if amend_up_qty:
                                            open_qty, open_notional = self._get_reverted_open_qty_n_notional(
                                                amend_up_px, amend_up_qty, chore_event, chore_snapshot,
                                                fetched_open_qty, fetched_open_notional)
                                        else:
                                            # if qty is not amended then px must be amended else code can't block in
                                            # chore_snapshot update
                                            open_qty = fetched_open_qty
                                            last_px = chore_snapshot.chore_brief.px
                                            old_open_notional = (
                                                    open_qty * self.get_usd_px(last_px,
                                                                               chore_snapshot.chore_brief.security.sec_id))
                                            new_open_notional = (
                                                    open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                               chore_snapshot.chore_brief.security.sec_id))
                                            open_notional = fetched_open_notional - old_open_notional + new_open_notional

                                    else:
                                        # if chore is in DOD state then whole qty is already in
                                        # cxled qty and no open chore exists to be updated
                                        open_qty = fetched_open_qty
                                        open_notional = fetched_open_notional
                            else:
                                err_str_: str = (f"Unsupported ChoreEventType: Must be either of "
                                                 f"[{ChoreEventType.OE_NEW}, {ChoreEventType.OE_INT_REJ}, "
                                                 f"{ChoreEventType.OE_BRK_REJ}, {ChoreEventType.OE_EXH_REJ}"
                                                 f"{ChoreEventType.OE_CXL_ACK}, {ChoreEventType.OE_UNSOL_CXL}], "
                                                 f"Found: {chore_journal_or_fills_journal.chore_event} - ignoring "
                                                 f"plan_brief update")
                                logging.error(err_str_)
                                return
                        elif isinstance(chore_journal_or_fills_journal, FillsJournal):
                            # For fills, removing current fill's qty from existing
                            # open_qty + current fill's notional (fill_qty * chore_px) from existing open_notional
                            fills_journal: FillsJournal = chore_journal_or_fills_journal
                            if not received_fill_after_dod:
                                if not chore_snapshot.chore_status == ChoreStatusType.OE_OVER_FILLED:
                                    open_qty = fetched_open_qty - fills_journal.fill_qty
                                    open_notional = (
                                            fetched_open_notional - (
                                                fills_journal.fill_qty *
                                                self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                chore_snapshot.chore_brief.security.sec_id)))
                                else:
                                    # if fill made chore OVER_FILLED, then extra fill can't be removed from current open
                                    # removing only what was open originally
                                    available_qty = self.get_valid_available_fill_qty(chore_snapshot)
                                    extra_fill_qty = chore_snapshot.filled_qty - available_qty
                                    acceptable_remaining_fill_qty = fills_journal.fill_qty - extra_fill_qty

                                    open_qty = fetched_open_qty - acceptable_remaining_fill_qty
                                    open_notional = fetched_open_notional - (
                                                        acceptable_remaining_fill_qty *
                                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                            else:
                                # if fills come after DOD, this chore's open calculation must
                                # have already removed from overall open qty and notional - no need to remove fill qty from
                                # existing open
                                open_qty = fetched_open_qty
                                open_notional = fetched_open_notional


                                if chore_snapshot.chore_status == ChoreStatusType.OE_OVER_FILLED:
                                    available_qty = self.get_valid_available_fill_qty(chore_snapshot)
                                    extra_fill_qty = chore_snapshot.filled_qty - available_qty
                                    acceptable_remaining_fill_qty = fills_journal.fill_qty - extra_fill_qty
                                    all_bkr_cxlled_qty = int(fetched_all_bkr_cxlled_qty - acceptable_remaining_fill_qty)
                                else:
                                    all_bkr_cxlled_qty = int(
                                        fetched_all_bkr_cxlled_qty - chore_snapshot.last_update_fill_qty)
                        else:
                            err_str_: str = ("Unsupported Journal type: Must be either ChoreJournal or FillsJournal, "
                                             f"Found type: {type(chore_journal_or_fills_journal)} - ignoring "
                                             f"plan_brief update")
                            logging.error(err_str_)
                            return
                        max_leg_notional = plan_limits.max_single_leg_notional * hedge_ratio if (
                                symbol == self.plan_leg_2.sec.sec_id) else plan_limits.max_single_leg_notional
                        consumable_notional = (max_leg_notional -
                                               symbol_side_snapshot.total_fill_notional - open_notional)
                        consumable_open_notional = plan_limits.max_open_single_leg_notional - open_notional
                        security_float = self.static_data.get_security_float_from_ticker(symbol)
                        if security_float is not None:
                            consumable_concentration = \
                                int((security_float / 100) * plan_limits.max_concentration -
                                    (open_qty + symbol_side_snapshot.total_filled_qty))
                        else:
                            consumable_concentration = 0
                        open_chores_count = (await StreetBookServiceRoutesCallbackBaseNativeOverride.
                                             underlying_get_open_chore_count_query_http(symbol))
                        consumable_open_chores = plan_limits.max_open_chores_per_side - open_chores_count[
                            0].open_chore_count
                        consumable_cxl_qty = ((((symbol_side_snapshot.total_filled_qty + open_qty +
                                                 symbol_side_snapshot.total_cxled_qty) / 100) *
                                               plan_limits.cancel_rate.max_cancel_rate) -
                                              symbol_side_snapshot.total_cxled_qty)
                        applicable_period_second = plan_limits.market_barter_volume_participation.applicable_period_seconds
                        executor_check_snapshot_list = \
                            (await StreetBookServiceRoutesCallbackBaseNativeOverride.
                             underlying_get_executor_check_snapshot_query_http(
                                symbol, side, applicable_period_second))
                        if len(executor_check_snapshot_list) == 1:
                            participation_period_chore_qty_sum = \
                                executor_check_snapshot_list[0].last_n_sec_chore_qty
                            indicative_consumable_participation_qty = \
                                get_consumable_participation_qty(
                                    executor_check_snapshot_list,
                                    plan_limits.market_barter_volume_participation.max_participation_rate)
                        else:
                            logging.error("Received unexpected length of executor_check_snapshot_list from query "
                                          f"{len(executor_check_snapshot_list)}, expected 1, symbol_side_key: "
                                          f"{get_symbol_side_key([(symbol, side)])}, likely bug in "
                                          f"get_executor_check_snapshot_query pre implementation")
                            indicative_consumable_participation_qty = 0
                            participation_period_chore_qty_sum = 0

                        updated_pair_side_brief_obj = \
                            PairSideBarteringBriefOptional(
                                security=security, side=side,
                                last_update_date_time=chore_snapshot.last_update_date_time,
                                consumable_open_chores=consumable_open_chores,
                                consumable_notional=consumable_notional,
                                consumable_open_notional=consumable_open_notional,
                                consumable_concentration=consumable_concentration,
                                participation_period_chore_qty_sum=participation_period_chore_qty_sum,
                                consumable_cxl_qty=consumable_cxl_qty,
                                indicative_consumable_participation_qty=
                                indicative_consumable_participation_qty,
                                all_bkr_cxlled_qty=all_bkr_cxlled_qty,
                                open_notional=open_notional,
                                open_qty=open_qty)

                        if side == Side.BUY:
                            other_leg_residual_qty = plan_brief_obj.pair_sell_side_bartering_brief.residual_qty
                            stored_pair_plan_bartering_brief = plan_brief_obj.pair_buy_side_bartering_brief
                            other_leg_symbol = plan_brief_obj.pair_sell_side_bartering_brief.security.sec_id
                        else:
                            other_leg_residual_qty = plan_brief_obj.pair_buy_side_bartering_brief.residual_qty
                            stored_pair_plan_bartering_brief = plan_brief_obj.pair_sell_side_bartering_brief
                            other_leg_symbol = plan_brief_obj.pair_buy_side_bartering_brief.security.sec_id
                        top_of_book_obj = self.get_cached_top_of_book_from_symbol(symbol)
                        other_leg_top_of_book = self.get_cached_top_of_book_from_symbol(other_leg_symbol)
                        if top_of_book_obj is not None and other_leg_top_of_book is not None:

                            # same residual_qty will be used if no match found below else will be replaced with
                            # updated residual_qty value
                            residual_qty = stored_pair_plan_bartering_brief.residual_qty
                            if isinstance(chore_journal_or_fills_journal, ChoreJournal):
                                if chore_journal.chore_event not in [ChoreEventType.OE_AMD_UP_UNACK,
                                                                     ChoreEventType.OE_AMD_DN_UNACK,
                                                                     ChoreEventType.OE_AMD_ACK,
                                                                     ChoreEventType.OE_AMD_REJ]:
                                    if chore_snapshot.chore_status == ChoreStatusType.OE_DOD:
                                        if chore_journal.chore_event == ChoreEventType.OE_LAPSE:
                                            # if chore is DOD and chore qty was lapsed - lapsed qty is residual
                                            unfilled_qty = chore_snapshot.last_lapsed_qty
                                        else:
                                            # If DOD came due to cxl_ack or any other non-lapse case
                                            unfilled_qty = self.get_residual_qty_post_chore_dod(chore_snapshot)
                                        residual_qty = int(stored_pair_plan_bartering_brief.residual_qty + unfilled_qty)
                                    elif chore_journal.chore_event == ChoreEventType.OE_LAPSE:
                                        lapsed_qty = chore_snapshot.last_lapsed_qty
                                        residual_qty = int(stored_pair_plan_bartering_brief.residual_qty + lapsed_qty)
                                    # else not required: No other case can affect residual qty
                                # else not required: No amend related event updates residual qty
                            else:
                                if received_fill_after_dod:
                                    if chore_snapshot.chore_status == ChoreStatusType.OE_DOD:
                                        residual_qty = int((stored_pair_plan_bartering_brief.residual_qty -
                                                            chore_snapshot.last_update_fill_qty))
                                    else:
                                        if chore_snapshot.chore_status == ChoreStatusType.OE_OVER_FILLED:
                                            available_qty = self.get_valid_available_fill_qty(chore_snapshot)
                                            extra_fill_qty = chore_snapshot.filled_qty - available_qty
                                            acceptable_remaining_fill_qty = fills_journal.fill_qty - extra_fill_qty
                                            residual_qty = int((stored_pair_plan_bartering_brief.residual_qty -
                                                                acceptable_remaining_fill_qty))
                                        else:
                                            residual_qty = int(stored_pair_plan_bartering_brief.residual_qty -
                                                               chore_snapshot.filled_qty)
                                # else not required: fills have no impact on residual qty unless they arrive post DOD

                            updated_pair_side_brief_obj.residual_qty = residual_qty

                            current_leg_tob_data, other_leg_tob_data = (
                                self._get_last_barter_px_n_symbol_tuples_from_tob(top_of_book_obj, other_leg_top_of_book))
                            current_leg_last_barter_px, current_leg_tob_symbol = current_leg_tob_data
                            other_leg_last_barter_px, other_leg_tob_symbol = other_leg_tob_data
                            updated_pair_side_brief_obj.indicative_consumable_residual = \
                                plan_limits.residual_restriction.max_residual - \
                                ((residual_qty * self.get_usd_px(current_leg_last_barter_px, current_leg_tob_symbol)) -
                                 (other_leg_residual_qty * self.get_usd_px(other_leg_last_barter_px, other_leg_tob_symbol)))
                        else:
                            logging.error(f"_update_plan_brief_from_chore_or_fill failed invalid TOBs from cache for key: "
                                          f"{StreetBookServiceRoutesCallbackBaseNativeOverride.get_chore_snapshot_log_key(chore_snapshot)};;;buy TOB: {top_of_book_obj}; sell"
                                          f" TOB: {other_leg_top_of_book}, {chore_snapshot=}")
                            return

                        # Updating consumable_nett_filled_notional
                        if symbol_side_snapshot.security.sec_id == self.plan_leg_1.sec.sec_id:
                            other_sec_id = self.plan_leg_2.sec.sec_id
                        else:
                            other_sec_id = self.plan_leg_1.sec.sec_id

                        if symbol_side_snapshot.side == Side.BUY:
                            other_side = Side.SELL
                        else:
                            other_side = Side.BUY

                        other_symbol_side_snapshot_tuple = (
                            self.plan_cache.get_symbol_side_snapshot_from_symbol(other_sec_id))
                        consumable_nett_filled_notional: float | None = None
                        if other_symbol_side_snapshot_tuple is not None:
                            other_symbol_side_snapshot, _ = other_symbol_side_snapshot_tuple
                            consumable_nett_filled_notional = (
                                    plan_limits.max_net_filled_notional - abs(
                                        symbol_side_snapshot.total_fill_notional -
                                        other_symbol_side_snapshot.total_fill_notional))
                        else:
                            err_str_ = ("Received symbol_side_snapshot_tuple as None from plan_cache, "
                                        f"symbol_side_key: {get_symbol_side_key([(other_sec_id, other_side)])}")
                            logging.error(err_str_)

                        if symbol == plan_brief_obj.pair_buy_side_bartering_brief.security.sec_id:
                            updated_plan_brief = PlanBriefOptional(
                                id=plan_brief_obj.id, pair_buy_side_bartering_brief=updated_pair_side_brief_obj,
                                consumable_nett_filled_notional=consumable_nett_filled_notional)
                        elif symbol == plan_brief_obj.pair_sell_side_bartering_brief.security.sec_id:
                            updated_plan_brief = PlanBriefOptional(
                                id=plan_brief_obj.id, pair_sell_side_bartering_brief=updated_pair_side_brief_obj,
                                consumable_nett_filled_notional=consumable_nett_filled_notional)
                        else:
                            err_str_ = f"error: None of the 2 pair_side_bartering_brief(s) contain {symbol = } in " \
                                       f"plan_brief of key: {get_plan_brief_log_key(plan_brief_obj)};;; " \
                                       f"{plan_brief_obj = }"
                            logging.exception(err_str_)
                            return

                        updated_plan_brief_dict = updated_plan_brief.to_dict(exclude_none=True)
                        updated_plan_brief = \
                            (await StreetBookServiceRoutesCallbackBaseNativeOverride.
                             underlying_partial_update_plan_brief_http(updated_plan_brief_dict))
                        logging.debug(f"Updated plan_brief for chore_id: {chore_snapshot.chore_brief.chore_id=}, "
                                      f"symbol_side_key: {get_symbol_side_key([(symbol, side)])};;;{updated_plan_brief=}")
                        return updated_plan_brief
                    else:
                        logging.error(f"error: no plan_limits found in plan_cache - ignoring update of chore_id: "
                                      f"{chore_snapshot.chore_brief.chore_id} in plan_brief, "
                                      f"symbol_side_key: {get_symbol_side_key([(symbol, side)])}")
                        return

                else:
                    err_str_ = (f"No plan brief found in plan_cache, ignoring update of plan_brief for chore_id: "
                                f"{chore_snapshot.chore_brief.chore_id}, symbol_side_key: "
                                f"{get_symbol_side_key([(symbol, side)])}")
                    logging.exception(err_str_)
                    return

    def _handle_cxl_qty_in_contact_status(self, chore_snapshot_obj: ChoreSnapshot, cxled_qty: int) -> int:
        update_overall_notional = \
            -(self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                              chore_snapshot_obj.chore_brief.security.sec_id) * cxled_qty)
        return update_overall_notional

    def get_old_n_new_open_qty_n_old_n_new_open_notional(
            self, amend_px: float, amend_qty: int, amend_event: ChoreEventType, chore_snapshot_obj: ChoreSnapshot):
        # since chore qty doesn't get changed in amend dn on qty and
        # cxled qty is increased - removing newly added amend_dn qty from old open qty
        new_open_qty = (chore_snapshot_obj.chore_brief.qty -
                        chore_snapshot_obj.filled_qty -
                        chore_snapshot_obj.cxled_qty)
        if amend_event == ChoreEventType.OE_AMD_DN_UNACK:
            old_open_qty = new_open_qty + amend_qty
        else:
            old_open_qty = new_open_qty - amend_qty

        if old_open_qty < 0:
            # case when before receiving amend rej chore was in over-filled or over-cxled state
            old_open_qty = 0

        if amend_px is not None:
            if amend_event == ChoreEventType.OE_AMD_DN_UNACK:
                last_px = chore_snapshot_obj.chore_brief.px + amend_px
            else:
                last_px = chore_snapshot_obj.chore_brief.px - amend_px
            old_open_notional = (
                    old_open_qty * self.get_usd_px(last_px,
                                                   chore_snapshot_obj.chore_brief.security.sec_id))
            new_open_notional = (
                    new_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                   chore_snapshot_obj.chore_brief.security.sec_id))
        else:
            old_open_notional = (
                    old_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                   chore_snapshot_obj.chore_brief.security.sec_id))
            new_open_notional = (
                    new_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                   chore_snapshot_obj.chore_brief.security.sec_id))
        return old_open_qty, new_open_qty, old_open_notional, new_open_notional

    def get_reverted_old_n_new_open_qty_n_old_n_new_open_notional(
            self, amend_px: float, amend_qty: int, amend_event: ChoreEventType, chore_snapshot_obj: ChoreSnapshot):
        # since chore qty doesn't get changed in amend dn on qty and
        # cxled qty is increased - removing newly added amend_dn qty from old open qty
        new_open_qty = (chore_snapshot_obj.chore_brief.qty -
                        chore_snapshot_obj.filled_qty -
                        chore_snapshot_obj.cxled_qty)
        if amend_event == ChoreEventType.OE_AMD_DN_UNACK:
            old_open_qty = (chore_snapshot_obj.chore_brief.qty -
                            chore_snapshot_obj.filled_qty -
                            (chore_snapshot_obj.cxled_qty + amend_qty))
        else:
            old_open_qty = new_open_qty + amend_qty

        if old_open_qty < 0:
            # case when before receiving amend rej chore was in over-filled or over-cxled state
            old_open_qty = 0

        if amend_px is not None:
            if amend_event == ChoreEventType.OE_AMD_DN_UNACK:
                last_px = chore_snapshot_obj.chore_brief.px - amend_px
            else:
                last_px = chore_snapshot_obj.chore_brief.px + amend_px
            old_open_notional = (
                    old_open_qty * self.get_usd_px(last_px,
                                                   chore_snapshot_obj.chore_brief.security.sec_id))
            new_open_notional = (
                    new_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                   chore_snapshot_obj.chore_brief.security.sec_id))
        else:
            old_open_notional = (
                    old_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                   chore_snapshot_obj.chore_brief.security.sec_id))
            new_open_notional = (
                    new_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                   chore_snapshot_obj.chore_brief.security.sec_id))
        return old_open_qty, new_open_qty, old_open_notional, new_open_notional

    async def _update_contact_status_from_chore_journal(
            self, chore_journal_obj: ChoreJournal,
            chore_snapshot_obj: ChoreSnapshot) -> ContactStatusUpdatesContainer | None:
        match chore_journal_obj.chore.side:
            case Side.BUY:
                update_overall_buy_notional = 0
                match chore_journal_obj.chore_event:
                    case ChoreEventType.OE_NEW:
                        update_overall_buy_notional = \
                            self.get_usd_px(chore_journal_obj.chore.px, chore_journal_obj.chore.security.sec_id) * \
                            chore_journal_obj.chore.qty
                    case (ChoreEventType.OE_CXL_ACK | ChoreEventType.OE_UNSOL_CXL | ChoreEventType.OE_INT_REJ |
                          ChoreEventType.OE_BRK_REJ | ChoreEventType.OE_EXH_REJ):
                        total_buy_unfilled_qty = self.get_residual_qty_post_chore_dod(chore_snapshot_obj)
                        update_overall_buy_notional = self._handle_cxl_qty_in_contact_status(
                            chore_snapshot_obj, total_buy_unfilled_qty)
                    case ChoreEventType.OE_LAPSE:
                        lapsed_qty = chore_snapshot_obj.last_lapsed_qty
                        update_overall_buy_notional = self._handle_cxl_qty_in_contact_status(
                            chore_snapshot_obj, lapsed_qty)
                    case ChoreEventType.OE_AMD_DN_UNACK | ChoreEventType.OE_AMD_UP_UNACK | ChoreEventType.OE_AMD_ACK:
                        if chore_snapshot_obj.chore_status not in OTHER_TERMINAL_STATES:
                            pending_amend_type = self.pending_amend_type(chore_journal_obj, chore_snapshot_obj)

                            if pending_amend_type == ChoreEventType.OE_AMD_DN_UNACK:
                                amend_dn_px = chore_snapshot_obj.pending_amend_dn_px
                                amend_dn_qty = chore_snapshot_obj.pending_amend_dn_qty

                                if amend_dn_qty:
                                    old_open_qty, new_open_qty, old_open_notional, new_open_notional = (
                                        self.get_old_n_new_open_qty_n_old_n_new_open_notional(
                                            amend_dn_px, amend_dn_qty, pending_amend_type, chore_snapshot_obj))

                                else:
                                    # if qty is not amended then px must be amended - else block will not
                                    # allow code to each here
                                    last_px = chore_snapshot_obj.chore_brief.px + amend_dn_px
                                    open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                chore_snapshot_obj.cxled_qty)
                                    old_open_notional = (
                                            open_qty * self.get_usd_px(last_px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                            else:
                                amend_up_px = chore_snapshot_obj.pending_amend_up_px
                                amend_up_qty = chore_snapshot_obj.pending_amend_up_qty

                                if amend_up_qty:
                                    # since chore qty doesn't get changed in amend dn on qty and
                                    # cxled qty is increased - removing newly added amend_dn qty from old open qty
                                    old_open_qty, new_open_qty, old_open_notional, new_open_notional = (
                                        self.get_old_n_new_open_qty_n_old_n_new_open_notional(
                                            amend_up_px, amend_up_qty, pending_amend_type, chore_snapshot_obj))
                                else:
                                    open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                chore_snapshot_obj.cxled_qty)

                                    # if qty is not amended then px must be amended - else block will not
                                    # allow code to each here
                                    last_px = chore_snapshot_obj.chore_brief.px - amend_up_px
                                    old_open_notional = (
                                            open_qty * self.get_usd_px(last_px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                            update_overall_buy_notional = new_open_notional - old_open_notional
                        # AMD: else not required: if chore status is DOD with AMD_ACK event then it is the
                        # case of amend post DOD so open would already be removed while handling DOD
                    case ChoreEventType.OE_AMD_REJ:
                        if chore_snapshot_obj.chore_status not in NON_FILLED_TERMINAL_STATES:
                            pending_amend_type = self.pending_amend_type(chore_journal_obj, chore_snapshot_obj)

                            if pending_amend_type == ChoreEventType.OE_AMD_DN_UNACK:
                                amend_dn_px = chore_snapshot_obj.pending_amend_dn_px
                                amend_dn_qty = chore_snapshot_obj.pending_amend_dn_qty

                                if amend_dn_qty:
                                    old_open_qty, new_open_qty, old_open_notional, new_open_notional = (
                                        self.get_reverted_old_n_new_open_qty_n_old_n_new_open_notional(
                                            amend_dn_px, amend_dn_qty, pending_amend_type, chore_snapshot_obj))

                                else:
                                    # if qty is not amended then px must be amended - else block will not
                                    # allow code to each here
                                    last_px = chore_snapshot_obj.chore_brief.px - amend_dn_px
                                    open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                chore_snapshot_obj.cxled_qty)
                                    old_open_notional = (
                                            open_qty * self.get_usd_px(last_px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                            else:
                                amend_up_px = chore_snapshot_obj.pending_amend_up_px
                                amend_up_qty = chore_snapshot_obj.pending_amend_up_qty

                                if amend_up_qty:
                                    # since chore qty doesn't get changed in amend dn on qty and
                                    # cxled qty is increased - removing newly added amend_dn qty from old open qty
                                    old_open_qty, new_open_qty, old_open_notional, new_open_notional = (
                                        self.get_reverted_old_n_new_open_qty_n_old_n_new_open_notional(
                                            amend_up_px, amend_up_qty, pending_amend_type, chore_snapshot_obj))
                                else:
                                    open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                chore_snapshot_obj.cxled_qty)

                                    # if qty is not amended then px must be amended - else block will not
                                    # allow code to each here
                                    last_px = chore_snapshot_obj.chore_brief.px + amend_up_px
                                    old_open_notional = (
                                            open_qty * self.get_usd_px(last_px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                            update_overall_buy_notional = new_open_notional - old_open_notional
                        # AMD: else not required: if chore status is DOD with AMD_ACK event then it is the
                        # case of amend post DOD so open would already be removed while handling DOD
                return ContactStatusUpdatesContainer(buy_notional_update=update_overall_buy_notional)
            case Side.SELL:
                update_overall_sell_notional = 0
                match chore_journal_obj.chore_event:
                    case ChoreEventType.OE_NEW:
                        update_overall_sell_notional = \
                            self.get_usd_px(chore_journal_obj.chore.px, chore_journal_obj.chore.security.sec_id) * \
                            chore_journal_obj.chore.qty
                    case (ChoreEventType.OE_CXL_ACK | ChoreEventType.OE_UNSOL_CXL | ChoreEventType.OE_INT_REJ |
                          ChoreEventType.OE_BRK_REJ | ChoreEventType.OE_EXH_REJ):
                        total_sell_unfilled_qty = self.get_residual_qty_post_chore_dod(chore_snapshot_obj)
                        update_overall_sell_notional = self._handle_cxl_qty_in_contact_status(
                            chore_snapshot_obj, total_sell_unfilled_qty)
                    case ChoreEventType.OE_LAPSE:
                        lapsed_qty = chore_snapshot_obj.last_lapsed_qty
                        update_overall_sell_notional = self._handle_cxl_qty_in_contact_status(
                            chore_snapshot_obj, lapsed_qty)
                    case ChoreEventType.OE_AMD_DN_UNACK | ChoreEventType.OE_AMD_UP_UNACK | ChoreEventType.OE_AMD_ACK:
                        if chore_snapshot_obj.chore_status not in OTHER_TERMINAL_STATES:
                            pending_amend_type = self.pending_amend_type(chore_journal_obj, chore_snapshot_obj)

                            if pending_amend_type == ChoreEventType.OE_AMD_DN_UNACK:
                                amend_dn_px = chore_snapshot_obj.pending_amend_dn_px
                                amend_dn_qty = chore_snapshot_obj.pending_amend_dn_qty

                                if amend_dn_qty:
                                    old_open_qty, new_open_qty, old_open_notional, new_open_notional = (
                                        self.get_old_n_new_open_qty_n_old_n_new_open_notional(
                                            amend_dn_px, amend_dn_qty, pending_amend_type, chore_snapshot_obj))

                                else:
                                    # if qty is not amended then px must be amended - else block will not
                                    # allow code to each here
                                    last_px = chore_snapshot_obj.chore_brief.px + amend_dn_px
                                    open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                chore_snapshot_obj.cxled_qty)
                                    old_open_notional = (
                                            open_qty * self.get_usd_px(last_px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                            else:
                                amend_up_px = chore_snapshot_obj.pending_amend_up_px
                                amend_up_qty = chore_snapshot_obj.pending_amend_up_qty

                                if amend_up_qty:
                                    # since chore qty doesn't get changed in amend dn on qty and
                                    # cxled qty is increased - removing newly added amend_dn qty from old open qty
                                    old_open_qty, new_open_qty, old_open_notional, new_open_notional = (
                                        self.get_old_n_new_open_qty_n_old_n_new_open_notional(
                                            amend_up_px, amend_up_qty, pending_amend_type, chore_snapshot_obj))
                                else:
                                    open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                chore_snapshot_obj.cxled_qty)

                                    # if qty is not amended then px must be amended - else block will not
                                    # allow code to each here
                                    last_px = chore_snapshot_obj.chore_brief.px - amend_up_px
                                    old_open_notional = (
                                            open_qty * self.get_usd_px(last_px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                            update_overall_sell_notional = new_open_notional - old_open_notional
                        # AMD: else not required: if chore status is DOD with AMD_ACK event then it is the
                        # case of amend post DOD so open would already be removed while handling DOD
                    case ChoreEventType.OE_AMD_REJ:
                        if chore_snapshot_obj.chore_status not in NON_FILLED_TERMINAL_STATES:
                            pending_amend_type = self.pending_amend_type(chore_journal_obj, chore_snapshot_obj)

                            if pending_amend_type == ChoreEventType.OE_AMD_DN_UNACK:
                                amend_dn_px = chore_snapshot_obj.pending_amend_dn_px
                                amend_dn_qty = chore_snapshot_obj.pending_amend_dn_qty

                                if amend_dn_qty:
                                    old_open_qty, new_open_qty, old_open_notional, new_open_notional = (
                                        self.get_reverted_old_n_new_open_qty_n_old_n_new_open_notional(
                                            amend_dn_px, amend_dn_qty, pending_amend_type, chore_snapshot_obj))

                                else:
                                    # if qty is not amended then px must be amended - else block will not
                                    # allow code to each here
                                    last_px = chore_snapshot_obj.chore_brief.px - amend_dn_px
                                    open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                chore_snapshot_obj.cxled_qty)
                                    old_open_notional = (
                                            open_qty * self.get_usd_px(last_px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                            else:
                                amend_up_px = chore_snapshot_obj.pending_amend_up_px
                                amend_up_qty = chore_snapshot_obj.pending_amend_up_qty

                                if amend_up_qty:
                                    # since chore qty doesn't get changed in amend dn on qty and
                                    # cxled qty is increased - removing newly added amend_dn qty from old open qty
                                    old_open_qty, new_open_qty, old_open_notional, new_open_notional = (
                                        self.get_reverted_old_n_new_open_qty_n_old_n_new_open_notional(
                                            amend_up_px, amend_up_qty, pending_amend_type, chore_snapshot_obj))
                                else:
                                    open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                chore_snapshot_obj.cxled_qty)

                                    # if qty is not amended then px must be amended - else block will not
                                    # allow code to each here
                                    last_px = chore_snapshot_obj.chore_brief.px + amend_up_px
                                    old_open_notional = (
                                            open_qty * self.get_usd_px(last_px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                       chore_snapshot_obj.chore_brief.security.sec_id))

                            update_overall_sell_notional = new_open_notional - old_open_notional
                        # AMD: else not required: if chore status is DOD with AMD_ACK event then it is the
                        # case of amend post DOD so open would already be removed while handling DOD
                return ContactStatusUpdatesContainer(sell_notional_update=update_overall_sell_notional)
            case other_:
                err_str_ = f"Unsupported Side Type {other_} received in chore_journal of key: " \
                           f"{StreetBookServiceRoutesCallbackBaseNativeOverride.get_chore_journal_log_key(chore_journal_obj)} while updating plan_status;;; " \
                           f"{chore_journal_obj = } "
                logging.error(err_str_)
                return None

    ##############################
    # Fills Journal Update Methods
    ##############################

    async def create_fills_journal_pre(self, fills_journal_obj: FillsJournal):
        await self.handle_create_fills_journal_pre(fills_journal_obj)

    async def create_fills_journal_post(self, fills_journal_obj: FillsJournal):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_fills_journal_get_all_ws(fills_journal_obj)

        async with StreetBookServiceRoutesCallbackBaseNativeOverride.journal_shared_lock:
            res = await self._apply_fill_update_in_chore_snapshot(fills_journal_obj)

            if res is not None:
                chore_snapshot, plan_brief, contact_status_updates = res

                # Updating and checking contact_limits in contact_manager
                post_book_service_http_client.check_contact_limits_query_client(
                    self.pair_plan_id, None, chore_snapshot, plan_brief, contact_status_updates)

            # else not required: if result returned from _apply_fill_update_in_chore_snapshot is None, that
            # signifies some unexpected exception occurred so complete update was not done,
            # therefore avoiding contact_limit checks too

    async def _update_contact_status_from_fill_journal(
            self, chore_snapshot_obj: ChoreSnapshot, received_fill_after_dod: bool
            ) -> ContactStatusUpdatesContainer | None:

        match chore_snapshot_obj.chore_brief.side:
            case Side.BUY:
                if received_fill_after_dod:
                    update_overall_buy_notional = \
                        (chore_snapshot_obj.last_update_fill_qty *
                         self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                         chore_snapshot_obj.chore_brief.security.sec_id))
                else:
                    if not chore_snapshot_obj.chore_status == ChoreStatusType.OE_OVER_FILLED:
                        update_overall_buy_notional = \
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                             chore_snapshot_obj.chore_brief.security.sec_id)) - \
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                             chore_snapshot_obj.chore_brief.security.sec_id))
                    else:
                        # if fill made chore OVER_FILLED, then extra fill can't be removed from current open
                        # removing only what was open originally
                        available_qty = self.get_valid_available_fill_qty(chore_snapshot_obj)
                        extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                        acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                        update_overall_buy_notional = \
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                             chore_snapshot_obj.chore_brief.security.sec_id)) - \
                            (acceptable_remaining_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                             chore_snapshot_obj.chore_brief.security.sec_id))

                update_overall_buy_fill_notional = \
                    (self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                     chore_snapshot_obj.chore_brief.security.sec_id) *
                     chore_snapshot_obj.last_update_fill_qty)
                return ContactStatusUpdatesContainer(buy_notional_update=update_overall_buy_notional,
                                                       buy_fill_notional_update=update_overall_buy_fill_notional)
            case Side.SELL:
                if received_fill_after_dod:
                    update_overall_sell_notional = \
                        (chore_snapshot_obj.last_update_fill_qty *
                         self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                         chore_snapshot_obj.chore_brief.security.sec_id))
                else:
                    if not chore_snapshot_obj.chore_status == ChoreStatusType.OE_OVER_FILLED:
                        update_overall_sell_notional = \
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                             chore_snapshot_obj.chore_brief.security.sec_id)) - \
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                             chore_snapshot_obj.chore_brief.security.sec_id))
                    else:
                        # if fill made chore OVER_FILLED, then extra fill can't be removed from current open
                        # removing only what was open originally
                        available_qty = self.get_valid_available_fill_qty(chore_snapshot_obj)
                        extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                        acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                        update_overall_sell_notional = \
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                             chore_snapshot_obj.chore_brief.security.sec_id)) - \
                            (acceptable_remaining_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                             chore_snapshot_obj.chore_brief.security.sec_id))
                update_overall_sell_fill_notional = \
                    self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                    chore_snapshot_obj.chore_brief.security.sec_id) * \
                    chore_snapshot_obj.last_update_fill_qty
                return ContactStatusUpdatesContainer(sell_notional_update=update_overall_sell_notional,
                                                       sell_fill_notional_update=update_overall_sell_fill_notional)
            case other_:
                err_str_ = f"Unsupported Side Type {other_} received in chore snapshot of key " \
                           f"{StreetBookServiceRoutesCallbackBaseNativeOverride.get_chore_snapshot_log_key(chore_snapshot_obj)} while updating plan_status;;; " \
                           f"{chore_snapshot_obj = }"
                logging.error(err_str_)
                return None

    async def _update_symbol_side_snapshot_from_fill_applied_chore_snapshot(
            self, chore_snapshot_obj: ChoreSnapshot, received_fill_after_dod: bool) -> SymbolSideSnapshot:
        async with SymbolSideSnapshot.reentrant_lock:
            symbol_side_snapshot_tuple = self.plan_cache.get_symbol_side_snapshot_from_symbol(
                chore_snapshot_obj.chore_brief.security.sec_id)

            if symbol_side_snapshot_tuple is not None:
                symbol_side_snapshot_obj, _ = symbol_side_snapshot_tuple
                updated_symbol_side_snapshot_obj = SymbolSideSnapshotBaseModel(id=symbol_side_snapshot_obj.id)
                updated_symbol_side_snapshot_obj.total_filled_qty = int(
                    symbol_side_snapshot_obj.total_filled_qty + chore_snapshot_obj.last_update_fill_qty)
                updated_symbol_side_snapshot_obj.total_fill_notional = \
                    symbol_side_snapshot_obj.total_fill_notional + \
                    (self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                     chore_snapshot_obj.chore_brief.security.sec_id) *
                     chore_snapshot_obj.last_update_fill_qty)
                updated_symbol_side_snapshot_obj.avg_fill_px = \
                    (self.get_local_px_or_notional(updated_symbol_side_snapshot_obj.total_fill_notional,
                                                   symbol_side_snapshot_obj.security.sec_id) /
                     updated_symbol_side_snapshot_obj.total_filled_qty
                     if updated_symbol_side_snapshot_obj.total_filled_qty != 0 else 0)
                updated_symbol_side_snapshot_obj.last_update_fill_px = chore_snapshot_obj.last_update_fill_px
                updated_symbol_side_snapshot_obj.last_update_fill_qty = int(chore_snapshot_obj.last_update_fill_qty)
                updated_symbol_side_snapshot_obj.last_update_date_time = chore_snapshot_obj.last_update_date_time
                if received_fill_after_dod:
                    if chore_snapshot_obj.chore_status == ChoreStatusType.OE_OVER_FILLED:
                        available_qty = self.get_valid_available_fill_qty(chore_snapshot_obj)
                        extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                        acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                        updated_symbol_side_snapshot_obj.total_cxled_qty = int(
                            symbol_side_snapshot_obj.total_cxled_qty - acceptable_remaining_fill_qty)
                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                            (symbol_side_snapshot_obj.total_cxled_notional - acceptable_remaining_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                             chore_snapshot_obj.chore_brief.security.sec_id)))
                    else:
                        updated_symbol_side_snapshot_obj.total_cxled_qty = int(
                            symbol_side_snapshot_obj.total_cxled_qty - chore_snapshot_obj.last_update_fill_qty)
                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                            symbol_side_snapshot_obj.total_cxled_notional -
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                             chore_snapshot_obj.chore_brief.security.sec_id)))
                    updated_symbol_side_snapshot_obj.avg_cxled_px = (
                            self.get_local_px_or_notional(updated_symbol_side_snapshot_obj.total_cxled_notional,
                                                          symbol_side_snapshot_obj.security.sec_id) /
                            updated_symbol_side_snapshot_obj.total_cxled_qty) \
                        if updated_symbol_side_snapshot_obj.total_cxled_qty != 0 else 0

                updated_symbol_side_snapshot_obj_dict = updated_symbol_side_snapshot_obj.to_dict(exclude_none=True)
                updated_symbol_side_snapshot_obj = \
                    await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                    underlying_partial_update_symbol_side_snapshot_http(updated_symbol_side_snapshot_obj_dict))
                return updated_symbol_side_snapshot_obj
            else:
                err_str_ = ("Received symbol_side_snapshot_tuple as None from plan_cache for symbol: "
                            f"{chore_snapshot_obj.chore_brief.security.sec_id}, "
                            f"chore_snapshot_key: {StreetBookServiceRoutesCallbackBaseNativeOverride.get_chore_snapshot_log_key(chore_snapshot_obj)} - "
                            f"ignoring this symbol_side_snapshot update from fills")
                logging.error(err_str_)

    def pause_plan(self):
        pair_plan = self.plan_cache.get_pair_plan_obj()
        if is_ongoing_plan(pair_plan):
            guaranteed_call_pair_plan_client(
                PairPlanBaseModel, email_book_service_http_client.patch_pair_plan_client,
                _id=self.pair_plan_id, plan_state=PlanState.PlanState_PAUSED.value)
        else:
            logging.error(f"Could not pause plan, plan is not in ongoing state;;;{pair_plan=}")

    def unpause_plan(self):
        guaranteed_call_pair_plan_client(
            PairPlanBaseModel, email_book_service_http_client.patch_pair_plan_client,
            _id=self.pair_plan_id, plan_state=PlanState.PlanState_ACTIVE.value)

    async def handle_post_chore_snapshot_tasks_for_fills(
            self, fills_journal_obj: FillsJournal, chore_snapshot_obj: ChoreSnapshot,
            received_fill_after_dod: bool):
        symbol_side_snapshot = \
            await self._update_symbol_side_snapshot_from_fill_applied_chore_snapshot(
                chore_snapshot_obj, received_fill_after_dod=received_fill_after_dod)
        if symbol_side_snapshot is not None:
            updated_plan_brief = await self._update_plan_brief_from_chore_or_fill(
                fills_journal_obj, chore_snapshot_obj, symbol_side_snapshot,
                received_fill_after_dod=received_fill_after_dod)
            if updated_plan_brief is not None:
                await self._update_plan_status_from_fill_journal(
                    chore_snapshot_obj, symbol_side_snapshot, updated_plan_brief,
                    received_fill_after_dod=received_fill_after_dod)
            # else not required: if updated_plan_brief is None then it means some error occurred in
            # _update_plan_brief_from_chore which would have got added to alert already
            contact_status_updates: ContactStatusUpdatesContainer | None = (
                await self._update_contact_status_from_fill_journal(
                    chore_snapshot_obj, received_fill_after_dod=received_fill_after_dod))

            return chore_snapshot_obj, updated_plan_brief, contact_status_updates
        # else not require_create_update_symbol_side_snapshot_from_chore_journald: if symbol_side_snapshot
        # is None then it means error occurred in _create_update_symbol_side_snapshot_from_chore_journal
        # which would have got added to alert already

    async def _update_plan_status_from_fill_journal(self, chore_snapshot_obj: ChoreSnapshot,
                                                     symbol_side_snapshot: SymbolSideSnapshot,
                                                     plan_brief_obj: PlanBrief,
                                                     received_fill_after_dod: bool):
        plan_limits_tuple = self.plan_cache.get_plan_limits()

        async with PlanStatus.reentrant_lock:
            plan_status_tuple = self.plan_cache.get_plan_status()

            if plan_limits_tuple is not None and plan_status_tuple is not None:
                plan_limits, _ = plan_limits_tuple
                fetched_plan_status_obj, _ = plan_status_tuple

                update_plan_status_obj = PlanStatusBaseModel(id=fetched_plan_status_obj.id)
                match chore_snapshot_obj.chore_brief.side:
                    case Side.BUY:
                        if not received_fill_after_dod:
                            if chore_snapshot_obj.chore_status != ChoreStatusType.OE_OVER_FILLED:
                                update_plan_status_obj.total_open_buy_qty = (
                                    int(fetched_plan_status_obj.total_open_buy_qty -
                                        chore_snapshot_obj.last_update_fill_qty))
                                update_plan_status_obj.total_open_buy_notional = (
                                    fetched_plan_status_obj.total_open_buy_notional -
                                    (chore_snapshot_obj.last_update_fill_qty *
                                     self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                     chore_snapshot_obj.chore_brief.security.sec_id)))
                            else:
                                # if fill made chore OVER_FILLED, then extra fill can't be removed from current open
                                # removing only what was open originally
                                available_qty = self.get_valid_available_fill_qty(chore_snapshot_obj)
                                extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                                acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                                update_plan_status_obj.total_open_buy_qty = int(
                                    fetched_plan_status_obj.total_open_buy_qty - acceptable_remaining_fill_qty)
                                update_plan_status_obj.total_open_buy_notional = (
                                    fetched_plan_status_obj.total_open_buy_notional -
                                    (acceptable_remaining_fill_qty *
                                     self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                     chore_snapshot_obj.chore_brief.security.sec_id)))
                            update_plan_status_obj.total_open_sell_notional = (
                                fetched_plan_status_obj.total_open_sell_notional)
                            if update_plan_status_obj.total_open_buy_qty == 0:
                                update_plan_status_obj.avg_open_buy_px = 0
                            else:
                                update_plan_status_obj.avg_open_buy_px = \
                                    self.get_local_px_or_notional(update_plan_status_obj.total_open_buy_notional,
                                                                  chore_snapshot_obj.chore_brief.security.sec_id) / \
                                    update_plan_status_obj.total_open_buy_qty

                        update_plan_status_obj.total_fill_buy_qty = int(
                            fetched_plan_status_obj.total_fill_buy_qty + chore_snapshot_obj.last_update_fill_qty)
                        update_plan_status_obj.total_fill_buy_notional = (
                            fetched_plan_status_obj.total_fill_buy_notional +
                            chore_snapshot_obj.last_update_fill_qty * self.get_usd_px(
                                chore_snapshot_obj.last_update_fill_px,
                                chore_snapshot_obj.chore_brief.security.sec_id))
                        update_plan_status_obj.avg_fill_buy_px = \
                            (self.get_local_px_or_notional(update_plan_status_obj.total_fill_buy_notional,
                                                           chore_snapshot_obj.chore_brief.security.sec_id) /
                             update_plan_status_obj.total_fill_buy_qty
                             if update_plan_status_obj.total_fill_buy_qty != 0 else 0)
                        update_plan_status_obj.total_fill_sell_notional = (
                            fetched_plan_status_obj.total_fill_sell_notional)
                        if received_fill_after_dod:
                            if chore_snapshot_obj.chore_status == ChoreStatusType.OE_OVER_FILLED:
                                # if fill made chore OVER_FILLED, then extra fill can't be removed from current cxl_qty
                                # removing only what was cxled qty originally
                                available_qty = self.get_valid_available_fill_qty(chore_snapshot_obj)
                                extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                                acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                                update_plan_status_obj.total_cxl_buy_qty = int(
                                    fetched_plan_status_obj.total_cxl_buy_qty - acceptable_remaining_fill_qty)
                                update_plan_status_obj.total_cxl_buy_notional = (
                                    fetched_plan_status_obj.total_cxl_buy_notional -
                                    (self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                     chore_snapshot_obj.chore_brief.security.sec_id) *
                                     acceptable_remaining_fill_qty))
                            else:
                                update_plan_status_obj.total_cxl_buy_qty = int(
                                    fetched_plan_status_obj.total_cxl_buy_qty -
                                    chore_snapshot_obj.last_update_fill_qty)
                                update_plan_status_obj.total_cxl_buy_notional = (
                                    fetched_plan_status_obj.total_cxl_buy_notional -
                                    (self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                     chore_snapshot_obj.chore_brief.security.sec_id) *
                                     chore_snapshot_obj.last_update_fill_qty))
                            update_plan_status_obj.avg_cxl_buy_px = (
                                (self.get_local_px_or_notional(update_plan_status_obj.total_cxl_buy_notional,
                                                               chore_snapshot_obj.chore_brief.security.sec_id) /
                                 update_plan_status_obj.total_cxl_buy_qty)
                                if update_plan_status_obj.total_cxl_buy_qty != 0 else 0)
                            update_plan_status_obj.total_cxl_sell_notional = (
                                fetched_plan_status_obj.total_cxl_sell_notional)

                    case Side.SELL:
                        if not received_fill_after_dod:
                            if chore_snapshot_obj.chore_status != ChoreStatusType.OE_OVER_FILLED:
                                update_plan_status_obj.total_open_sell_qty = (
                                    int(fetched_plan_status_obj.total_open_sell_qty -
                                        chore_snapshot_obj.last_update_fill_qty))
                                update_plan_status_obj.total_open_sell_notional = (
                                    fetched_plan_status_obj.total_open_sell_notional -
                                    (chore_snapshot_obj.last_update_fill_qty *
                                     self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                     chore_snapshot_obj.chore_brief.security.sec_id)))
                            else:
                                # if fill made chore OVER_FILLED, then extra fill can't be removed from current open
                                # removing only what was open originally
                                available_qty = self.get_valid_available_fill_qty(chore_snapshot_obj)
                                extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                                acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                                update_plan_status_obj.total_open_sell_qty = int(
                                    fetched_plan_status_obj.total_open_sell_qty - acceptable_remaining_fill_qty)
                                update_plan_status_obj.total_open_sell_notional = (
                                    fetched_plan_status_obj.total_open_sell_notional -
                                    (acceptable_remaining_fill_qty *
                                     self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                     chore_snapshot_obj.chore_brief.security.sec_id)))
                            update_plan_status_obj.total_open_buy_notional = (
                                fetched_plan_status_obj.total_open_buy_notional)
                            if update_plan_status_obj.total_open_sell_qty == 0:
                                update_plan_status_obj.avg_open_sell_px = 0
                            else:
                                update_plan_status_obj.avg_open_sell_px = \
                                    self.get_local_px_or_notional(update_plan_status_obj.total_open_sell_notional,
                                                                  chore_snapshot_obj.chore_brief.security.sec_id) / \
                                    update_plan_status_obj.total_open_sell_qty

                        update_plan_status_obj.total_fill_sell_qty = int(
                            fetched_plan_status_obj.total_fill_sell_qty + chore_snapshot_obj.last_update_fill_qty)
                        update_plan_status_obj.total_fill_sell_notional = (
                                fetched_plan_status_obj.total_fill_sell_notional +
                                chore_snapshot_obj.last_update_fill_qty * self.get_usd_px(
                                    chore_snapshot_obj.last_update_fill_px,
                                    chore_snapshot_obj.chore_brief.security.sec_id))
                        if update_plan_status_obj.total_fill_sell_qty:
                            update_plan_status_obj.avg_fill_sell_px = \
                                self.get_local_px_or_notional(update_plan_status_obj.total_fill_sell_notional,
                                                              chore_snapshot_obj.chore_brief.security.sec_id) / \
                                update_plan_status_obj.total_fill_sell_qty
                        else:
                            update_plan_status_obj.avg_fill_sell_px = 0
                        update_plan_status_obj.total_fill_buy_notional = (
                            fetched_plan_status_obj.total_fill_buy_notional)

                        if received_fill_after_dod:
                            if chore_snapshot_obj.chore_status == ChoreStatusType.OE_OVER_FILLED:
                                # if fill made chore OVER_FILLED, then extra fill can't be removed from current cxl_qty
                                # removing only what was cxled qty originally
                                available_qty = self.get_valid_available_fill_qty(chore_snapshot_obj)
                                extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                                acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                                update_plan_status_obj.total_cxl_sell_qty = int(
                                    fetched_plan_status_obj.total_cxl_sell_qty - acceptable_remaining_fill_qty)
                                update_plan_status_obj.total_cxl_sell_notional = (
                                        fetched_plan_status_obj.total_cxl_sell_notional -
                                        (self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                         chore_snapshot_obj.chore_brief.security.sec_id) *
                                         acceptable_remaining_fill_qty))
                            else:
                                update_plan_status_obj.total_cxl_sell_qty = int(
                                    fetched_plan_status_obj.total_cxl_sell_qty -
                                    chore_snapshot_obj.last_update_fill_qty)
                                update_plan_status_obj.total_cxl_sell_notional = (
                                    fetched_plan_status_obj.total_cxl_sell_notional -
                                    (self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                     chore_snapshot_obj.chore_brief.security.sec_id) *
                                     chore_snapshot_obj.last_update_fill_qty))
                            update_plan_status_obj.avg_cxl_sell_px = (
                                (self.get_local_px_or_notional(update_plan_status_obj.total_cxl_sell_notional,
                                                               chore_snapshot_obj.chore_brief.security.sec_id) /
                                 update_plan_status_obj.total_cxl_sell_qty)
                                if update_plan_status_obj.total_cxl_sell_qty != 0 else 0)
                            update_plan_status_obj.total_cxl_buy_notional = (
                                fetched_plan_status_obj.total_cxl_buy_notional)

                    case other_:
                        err_str_ = f"Unsupported Side Type {other_} received for chore_snapshot_key: " \
                                   f"{StreetBookServiceRoutesCallbackBaseNativeOverride.get_chore_snapshot_log_key(chore_snapshot_obj)} while updating plan_status;;; " \
                                   f"{chore_snapshot_obj = }"
                        logging.error(err_str_)
                        return
                if not received_fill_after_dod:
                    update_plan_status_obj.total_open_exposure = (update_plan_status_obj.total_open_buy_notional -
                                                                   update_plan_status_obj.total_open_sell_notional)
                update_plan_status_obj.total_fill_exposure = (update_plan_status_obj.total_fill_buy_notional -
                                                               update_plan_status_obj.total_fill_sell_notional)
                if received_fill_after_dod:
                    update_plan_status_obj.total_cxl_exposure = (update_plan_status_obj.total_cxl_buy_notional -
                                                                  update_plan_status_obj.total_cxl_sell_notional)
                if update_plan_status_obj.total_fill_buy_notional < update_plan_status_obj.total_fill_sell_notional:
                    update_plan_status_obj.balance_notional = \
                        plan_limits.max_single_leg_notional - update_plan_status_obj.total_fill_buy_notional
                else:
                    update_plan_status_obj.balance_notional = \
                        plan_limits.max_single_leg_notional - update_plan_status_obj.total_fill_sell_notional

                updated_residual = self.__get_residual_obj(chore_snapshot_obj.chore_brief.side, plan_brief_obj)
                if updated_residual is not None:
                    update_plan_status_obj.residual = updated_residual

                # Updating plan_state as paused if limits get breached
                await self._pause_plan_if_limits_breached(update_plan_status_obj, plan_limits,
                                                           plan_brief_obj, symbol_side_snapshot)

                update_plan_status_obj_dict = update_plan_status_obj.to_dict(exclude_none=True)
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_plan_status_http(
                    update_plan_status_obj_dict)
            else:
                logging.error(f"error: either tuple of plan_status or plan_limits received as None from cache;;; "
                              f"{plan_status_tuple=}, {plan_limits_tuple=}")
                return

    async def _check_n_delete_symbol_side_snapshot_from_unload_plan(self) -> bool:
        pair_symbol_side_list = [
            (self.plan_leg_1.sec, self.plan_leg_1.side),
            (self.plan_leg_2.sec, self.plan_leg_2.side)
        ]

        for security, side in pair_symbol_side_list:
            symbol_side_snapshots_tuple = self.plan_cache.get_symbol_side_snapshot_from_symbol(security.sec_id)

            if symbol_side_snapshots_tuple is not None:
                symbol_side_snapshot, _ = symbol_side_snapshots_tuple
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_symbol_side_snapshot_http(
                    symbol_side_snapshot.id)
        return True

    async def _check_n_delete_plan_brief_for_unload_plan(self) -> bool:
        symbol = self.plan_leg_1.sec.sec_id
        plan_brief_obj_tuple = self.plan_cache.get_plan_brief()

        if plan_brief_obj_tuple is not None:
            plan_brief_obj, _ = plan_brief_obj_tuple
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_plan_brief_http(
                plan_brief_obj.id)
        return True

    async def _force_unpublish_symbol_overview_from_unload_plan(self) -> bool:
        symbols_list = [self.plan_leg_1.sec.sec_id, self.plan_leg_2.sec.sec_id]

        async with SymbolOverview.reentrant_lock:
            for symbol in symbols_list:
                symbol_overview_tuple = self.plan_cache.get_symbol_overview_from_symbol(symbol)

                if symbol_overview_tuple is not None:
                    symbol_overview_obj, _ = symbol_overview_tuple
                    updated_symbol_overview = {"_id": symbol_overview_obj.id, "force_publish": False}
                    await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                           underlying_partial_update_symbol_overview_http(updated_symbol_overview))

        return True

    ############################
    # BarteringDataManager updates
    ############################

    async def partial_update_chore_journal_post(self, updated_chore_journal_obj_json: Dict[str, Any]):
        await self.handle_partial_update_chore_journal_post(updated_chore_journal_obj_json)

    async def create_chore_snapshot_post(self, chore_snapshot_obj: ChoreSnapshot):
        await self.handle_create_chore_snapshot_post(chore_snapshot_obj)

    async def update_chore_snapshot_post(self, updated_chore_snapshot_obj: ChoreSnapshot):
        await self.handle_update_chore_snapshot_post(updated_chore_snapshot_obj)

    async def partial_update_chore_snapshot_post(self, updated_chore_snapshot_obj_json: Dict[str, Any]):
        await self.handle_partial_update_chore_snapshot_post(updated_chore_snapshot_obj_json)

    async def create_symbol_side_snapshot_post(self, symbol_side_snapshot_obj: SymbolSideSnapshot):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_symbol_side_snapshot_get_all_ws(symbol_side_snapshot_obj)

    async def update_symbol_side_snapshot_post(self, updated_symbol_side_snapshot_obj: SymbolSideSnapshot):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_symbol_side_snapshot_get_all_ws(updated_symbol_side_snapshot_obj)

    async def partial_update_symbol_side_snapshot_post(self, updated_symbol_side_snapshot_obj_json: Dict[str, Any]):
        updated_symbol_side_snapshot_obj = SymbolSideSnapshot.from_dict(updated_symbol_side_snapshot_obj_json)
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_symbol_side_snapshot_get_all_ws(updated_symbol_side_snapshot_obj)

    async def update_plan_status_post(self, updated_plan_status_obj: PlanStatus):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_plan_status_get_all_ws(updated_plan_status_obj)

        # updating balance_notional field in current pair_plan's PlanView using log analyzer
        log_str = pair_plan_client_call_log_str(PlanViewBaseModel,
                                                 photo_book_service_http_client.patch_all_plan_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=updated_plan_status_obj.id,
                                                 balance_notional=updated_plan_status_obj.balance_notional,
                                                 average_premium=updated_plan_status_obj.average_premium,
                                                 total_fill_buy_notional=
                                                 updated_plan_status_obj.total_fill_buy_notional,
                                                 total_fill_sell_notional=
                                                 updated_plan_status_obj.total_fill_sell_notional)
        logging.db(log_str)

    async def partial_update_plan_status_post(self, updated_plan_status_obj_json: Dict[str, Any]):
        updated_plan_status_obj = PlanStatus.from_dict(updated_plan_status_obj_json)
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_plan_status_get_all_ws(updated_plan_status_obj)

        # updating balance_notional field in current pair_plan's PlanView using log analyzer
        log_str = pair_plan_client_call_log_str(PlanViewBaseModel,
                                                 photo_book_service_http_client.patch_all_plan_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=updated_plan_status_obj.id,
                                                 balance_notional=updated_plan_status_obj.balance_notional,
                                                 average_premium=updated_plan_status_obj.average_premium,
                                                 total_fill_buy_notional=
                                                 updated_plan_status_obj.total_fill_buy_notional,
                                                 total_fill_sell_notional=
                                                 updated_plan_status_obj.total_fill_sell_notional)
        logging.db(log_str)

    @staticmethod
    def validate_single_id_per_symbol(stored_tobs: List[TopOfBookBaseModel | TopOfBookBaseModel],
                                      cmp_tob: TopOfBookBaseModel):
        err: str | None = None
        if stored_tobs[0] is not None and cmp_tob.symbol == stored_tobs[0].symbol and cmp_tob.id != stored_tobs[0].id:
            err = f"id_mismatched for same symbol! stored TOB: {stored_tobs[0]}, found TOB: {cmp_tob}"
        elif stored_tobs[1] is not None and cmp_tob.symbol == stored_tobs[1].symbol and cmp_tob.id != stored_tobs[1].id:
            err = f"id_mismatched for same symbol! stored TOB: {stored_tobs[1]}, found TOB: {cmp_tob}"
        return err

    def update_fill(self):
        self.plan_cache.get_plan_brief()

    async def partial_update_fills_journal_post(self, updated_fills_journal_obj_json: Dict[str, Any]):
        await self.handle_partial_update_fills_journal_post(updated_fills_journal_obj_json)

    async def create_plan_brief_post(self, plan_brief_obj: PlanBrief):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_plan_brief_get_all_ws(plan_brief_obj)

    async def update_plan_brief_post(self, updated_plan_brief_obj: PlanBrief):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_plan_brief_get_all_ws(updated_plan_brief_obj)

    async def partial_update_plan_brief_post(self, updated_plan_brief_obj_json: Dict[str, Any]):
        updated_plan_brief_obj = PlanBrief.from_dict(updated_plan_brief_obj_json)
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_plan_brief_get_all_ws(updated_plan_brief_obj)

    async def create_plan_status_post(self, plan_status_obj: PlanStatus):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_plan_status_get_all_ws(plan_status_obj)

        # updating balance_notional field in current pair_plan's PlanView using log analyzer
        log_str = pair_plan_client_call_log_str(PlanViewBaseModel,
                                                 photo_book_service_http_client.patch_all_plan_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=plan_status_obj.id,
                                                 balance_notional=plan_status_obj.balance_notional,
                                                 average_premium=plan_status_obj.average_premium,
                                                 total_fill_buy_notional=
                                                 plan_status_obj.total_fill_buy_notional,
                                                 total_fill_sell_notional=
                                                 plan_status_obj.total_fill_sell_notional, market_premium=0)
        logging.db(log_str)

    async def create_plan_limits_post(self, plan_limits_obj: PlanLimits):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_plan_limits_get_all_ws(plan_limits_obj)

        # updating max_single_leg_notional field in current pair_plan's PlanView using log analyzer
        log_str = pair_plan_client_call_log_str(PlanViewBaseModel,
                                                 photo_book_service_http_client.patch_all_plan_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=plan_limits_obj.id,
                                                 max_single_leg_notional=
                                                 plan_limits_obj.max_single_leg_notional)
        logging.db(log_str)

    async def _update_plan_brief_consumables_based_on_plan_limit_updates(
            self, stored_plan_limits_obj: Dict | PlanLimits, updated_plan_limits_obj: PlanLimits):

        plan_brief_patch_dict = {"_id": updated_plan_limits_obj.id,
                                  "pair_buy_side_bartering_brief": {},
                                  "pair_sell_side_bartering_brief": {}}    # will keep updating based on updates found
        do_plan_brief_update = False

        async with StreetBookServiceRoutesCallbackBaseNativeOverride.journal_shared_lock:
            # taking journal_shared_lock since in some updates open and filled qty too is involved
            async with PlanBrief.reentrant_lock:
                stored_plan_brief_tuple = self.plan_cache.get_plan_brief()
                if stored_plan_brief_tuple is not None:
                    stored_plan_brief, _ = stored_plan_brief_tuple

                    # checking max_single_leg_notional and updating consumable_notional on both legs if updated
                    if isinstance(stored_plan_limits_obj, dict):
                        stored_max_single_leg_notional = stored_plan_limits_obj.get("max_single_leg_notional")
                    else:
                        stored_max_single_leg_notional = stored_plan_limits_obj.max_single_leg_notional
                    if stored_max_single_leg_notional != updated_plan_limits_obj.max_single_leg_notional:
                        updated_max_single_leg_notional_delta = (
                            updated_plan_limits_obj.max_single_leg_notional - stored_max_single_leg_notional)
                        plan_brief_patch_dict["pair_buy_side_bartering_brief"]["consumable_notional"] = (
                            stored_plan_brief.pair_buy_side_bartering_brief.consumable_notional +
                            updated_max_single_leg_notional_delta)
                        plan_brief_patch_dict["pair_sell_side_bartering_brief"]["consumable_notional"] = (
                            stored_plan_brief.pair_sell_side_bartering_brief.consumable_notional +
                            updated_max_single_leg_notional_delta)
                        do_plan_brief_update = True
                    # else not required: max_single_leg_notional not updated - no extra handling required

                    # checking max_open_single_leg_notional and updating consumable_open_notional on both legs if updated
                    if isinstance(stored_plan_limits_obj, dict):
                        stored_max_open_single_leg_notional = stored_plan_limits_obj.get("max_open_single_leg_notional")
                    else:
                        stored_max_open_single_leg_notional = stored_plan_limits_obj.max_open_single_leg_notional
                    if stored_max_open_single_leg_notional != updated_plan_limits_obj.max_open_single_leg_notional:
                        updated_max_open_single_leg_notional_delta = (
                            updated_plan_limits_obj.max_open_single_leg_notional - stored_max_open_single_leg_notional)
                        plan_brief_patch_dict["pair_buy_side_bartering_brief"]["consumable_open_notional"] = (
                            stored_plan_brief.pair_buy_side_bartering_brief.consumable_open_notional +
                            updated_max_open_single_leg_notional_delta)
                        plan_brief_patch_dict["pair_sell_side_bartering_brief"]["consumable_open_notional"] = (
                            stored_plan_brief.pair_sell_side_bartering_brief.consumable_open_notional +
                            updated_max_open_single_leg_notional_delta)
                        do_plan_brief_update = True
                    # else not required: max_open_single_leg_notional not updated - no extra handling required

                    # checking max_open_chores_per_side and updating consumable_open_chores on both legs if updated
                    if isinstance(stored_plan_limits_obj, dict):
                        stored_max_open_chores_per_side = stored_plan_limits_obj.get(
                            "max_open_chores_per_side")
                    else:
                        stored_max_open_chores_per_side = stored_plan_limits_obj.max_open_chores_per_side
                    if stored_max_open_chores_per_side != updated_plan_limits_obj.max_open_chores_per_side:
                        updated_max_open_chores_per_side_delta = (
                            updated_plan_limits_obj.max_open_chores_per_side - stored_max_open_chores_per_side)
                        plan_brief_patch_dict["pair_buy_side_bartering_brief"]["consumable_open_chores"] = (
                            stored_plan_brief.pair_buy_side_bartering_brief.consumable_open_chores +
                            updated_max_open_chores_per_side_delta)
                        plan_brief_patch_dict["pair_sell_side_bartering_brief"]["consumable_open_chores"] = (
                            stored_plan_brief.pair_sell_side_bartering_brief.consumable_open_chores +
                            updated_max_open_chores_per_side_delta)
                        do_plan_brief_update = True

                    # else not required: max_open_chores_per_side not updated - no extra handling required

                    # checking max_concentration and updating consumable_open_chores on both legs if updated
                    if isinstance(stored_plan_limits_obj, dict):
                        stored_max_concentration = stored_plan_limits_obj.get(
                            "max_concentration")
                    else:
                        stored_max_concentration = stored_plan_limits_obj.max_concentration
                    if stored_max_concentration != updated_plan_limits_obj.max_concentration:
                        # Formula used to compute consumable_concentration is:
                        # consumable_concentration = int((security_float / 100) * plan_limits.max_concentration -
                        #                                     (total_open_qty + total_filled_qty))
                        # (total_open_qty + total_filled_qty) =
                        #           int((security_float / 100) * plan_limits.max_concentration - consumable_concentration)

                        # Finding value for (total_open_qty + total_filled_qty) based on current
                        # consumable_concentration to compute consumable_concentration based on new max_concentration

                        security_float = self.static_data.get_security_float_from_ticker(
                            stored_plan_brief.pair_buy_side_bartering_brief.security.sec_id)
                        if security_float is not None:
                            open_n_filled_qty_sum = int((security_float / 100) * stored_max_concentration -
                                                        stored_plan_brief.pair_buy_side_bartering_brief.consumable_concentration)
                            updated_consumable_concentration = (
                                int((security_float / 100) * updated_plan_limits_obj.max_concentration -
                                    open_n_filled_qty_sum))
                            plan_brief_patch_dict["pair_buy_side_bartering_brief"]["consumable_concentration"] = updated_consumable_concentration

                            open_n_filled_qty_sum = int((security_float / 100) * stored_max_concentration -
                                                        stored_plan_brief.pair_sell_side_bartering_brief.consumable_concentration)
                            updated_consumable_concentration = (
                                int((security_float / 100) * updated_plan_limits_obj.max_concentration -
                                    open_n_filled_qty_sum))
                            plan_brief_patch_dict["pair_sell_side_bartering_brief"]["consumable_concentration"] = updated_consumable_concentration
                            do_plan_brief_update = True
                        # else not required: consumable_concentration is 0 when security_float is found None
                    # else not required: max_concentration not updated - no extra handling required

                    # checking max_net_filled_notional and updating consumable_nett_filled_notional on both legs if updated
                    if isinstance(stored_plan_limits_obj, dict):
                        stored_max_net_filled_notional = stored_plan_limits_obj.get(
                            "max_net_filled_notional")
                    else:
                        stored_max_net_filled_notional = stored_plan_limits_obj.max_net_filled_notional
                    if stored_max_net_filled_notional != updated_plan_limits_obj.max_net_filled_notional:
                        updated_max_net_filled_notional_delta = (
                                updated_plan_limits_obj.max_net_filled_notional - stored_max_net_filled_notional)
                        plan_brief_patch_dict["consumable_nett_filled_notional"] = (
                                stored_plan_brief.consumable_nett_filled_notional +
                                updated_max_net_filled_notional_delta)
                        do_plan_brief_update = True
                    # else not required: max_concentration not updated - no extra handling required

                    if do_plan_brief_update:
                        # cleaning plan_brief_patch_dict
                        if not plan_brief_patch_dict["pair_buy_side_bartering_brief"]:
                            del plan_brief_patch_dict["pair_buy_side_bartering_brief"]
                        if not plan_brief_patch_dict["pair_sell_side_bartering_brief"]:
                            del plan_brief_patch_dict["pair_sell_side_bartering_brief"]

                        await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_plan_brief_http(
                            plan_brief_patch_dict)
                    # else not required: if no limit having corresponding consumable is updated
                    # then avoiding any plan_brief update
                # else not required: plan_brief doesn't exist - when created will use updated limit values
                # for setting consumables

    async def _update_plan_limits_post(self, stored_plan_limits_obj: PlanLimits | Dict,
                                        updated_plan_limits_obj: PlanLimits):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_plan_limits_get_all_ws(updated_plan_limits_obj)

        # updating max_single_leg_notional field in current pair_plan's PlanView using log analyzer
        log_str = pair_plan_client_call_log_str(PlanViewBaseModel,
                                                 photo_book_service_http_client.patch_all_plan_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=updated_plan_limits_obj.id,
                                                 max_single_leg_notional=
                                                 updated_plan_limits_obj.max_single_leg_notional)
        logging.db(log_str)

        if isinstance(stored_plan_limits_obj, dict):
            stored_eqt_sod_disable = stored_plan_limits_obj.get("eqt_sod_disable")
        else:
            stored_eqt_sod_disable = stored_plan_limits_obj.eqt_sod_disable
        if not stored_eqt_sod_disable and updated_plan_limits_obj.eqt_sod_disable:
            script_path: str = str(PAIR_STRAT_ENGINE_DIR / "pyscripts" / "disable_sod_positions_on_eqt.py")
            cmd: List[str] = ["python", script_path, f"{updated_plan_limits_obj.id}", "&"]
            launcher: subprocess.Popen = subprocess.Popen(cmd)
            logging.warning(f"Triggered eqt_sod_disable event at {DateTime.utcnow()};;;{cmd=}, {launcher=}")

        # updating all consumables if any corresponding limit is updated
        await self._update_plan_brief_consumables_based_on_plan_limit_updates(stored_plan_limits_obj,
                                                                                updated_plan_limits_obj)

    async def update_plan_limits_post(self, stored_plan_limits_obj: PlanLimits,
                                       updated_plan_limits_obj: PlanLimits):
        await self._update_plan_limits_post(stored_plan_limits_obj, updated_plan_limits_obj)

    async def partial_update_plan_limits_post(self, stored_plan_limits_obj_json: Dict[str, Any],
                                               updated_plan_limits_obj_json: Dict[str, Any]):
        updated_plan_limits_obj = PlanLimits.from_dict(updated_plan_limits_obj_json)
        await self._update_plan_limits_post(stored_plan_limits_obj_json, updated_plan_limits_obj)

    async def create_new_chore_post(self, new_chore_obj: NewChore):
        await self.handle_create_new_chore_post(new_chore_obj)

    async def create_cancel_chore_post(self, cancel_chore_obj: CancelChore):
        await self.handle_create_cancel_chore_post(cancel_chore_obj)

    async def partial_update_cancel_chore_post(self, updated_cancel_chore_obj_json: Dict[str, Any]):
        await self.handle_partial_update_cancel_chore_post(updated_cancel_chore_obj_json)

    async def create_symbol_overview_pre(self, symbol_overview_obj: SymbolOverview):
        await self.handle_create_symbol_overview_pre(symbol_overview_obj)

    async def update_symbol_overview_pre(self, updated_symbol_overview_obj: SymbolOverview):
        return await self.handle_update_symbol_overview_pre(updated_symbol_overview_obj)

    async def partial_update_symbol_overview_pre(self, stored_symbol_overview_obj_json: Dict[str, Any], 
                                                 updated_symbol_overview_obj_json: Dict[str, Any]):
        return await self.handle_partial_update_symbol_overview_pre(stored_symbol_overview_obj_json,
                                                                    updated_symbol_overview_obj_json)

    async def create_symbol_overview_post(self, symbol_overview_obj: SymbolOverview):
        await self.handle_create_symbol_overview_post(symbol_overview_obj)

    async def update_symbol_overview_post(self, updated_symbol_overview_obj: SymbolOverview):
        await self.handle_update_symbol_overview_post(updated_symbol_overview_obj)

    async def partial_update_symbol_overview_post(self, updated_symbol_overview_obj_json: Dict[str, Any]):
        await self.handle_partial_update_symbol_overview_post(updated_symbol_overview_obj_json)

    async def create_all_symbol_overview_post(self, symbol_overview_obj_list: List[SymbolOverview]):
        await self.handle_create_all_symbol_overview_post(symbol_overview_obj_list)

    async def update_all_symbol_overview_post(self, updated_symbol_overview_obj_list: List[SymbolOverview]):
        await self.handle_update_all_symbol_overview_post(updated_symbol_overview_obj_list)

    async def partial_update_all_symbol_overview_post(self, updated_symbol_overview_dict_list: List[Dict[str, Any]]):
        await self.handle_partial_update_all_symbol_overview_post(updated_symbol_overview_dict_list)

    #####################
    # Query Pre/Post handling
    #####################

    async def get_symbol_side_snapshot_from_symbol_side_query_pre(
            self, symbol_side_snapshot_class_type: Type[SymbolSideSnapshot], security_id: str, side: str):
        symbol_side_snapshot_objs = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_side_snapshot_http(
                get_symbol_side_snapshot_from_symbol_side(security_id, side), self.get_generic_read_route())

        if len(symbol_side_snapshot_objs) > 1:
            err_str_ = f"Found multiple objects of symbol_side_snapshot for key: " \
                       f"{get_symbol_side_key([(security_id, Side(side))])}"
            logging.error(err_str_)

        return symbol_side_snapshot_objs

    async def update_residuals_query_pre(self, pair_plan_class_type: Type[PlanStatus], security_id: str, side: Side,
                                         residual_qty: int):
        async with StreetBookServiceRoutesCallbackBaseNativeOverride.journal_shared_lock:
            async with (StreetBookServiceRoutesCallbackBaseNativeOverride.residual_compute_shared_lock):
                plan_brief_tuple = self.plan_cache.get_plan_brief()

                if plan_brief_tuple is not None:
                    plan_brief_obj, _ = plan_brief_tuple
                    if side == Side.BUY:
                        update_bartering_side_brief = \
                            PairSideBarteringBriefOptional(
                                residual_qty=int(plan_brief_obj.pair_buy_side_bartering_brief.residual_qty + residual_qty))
                        update_plan_brief = PlanBriefBaseModel(id=plan_brief_obj.id,
                                                                 pair_buy_side_bartering_brief=update_bartering_side_brief)

                    else:
                        update_bartering_side_brief = \
                            PairSideBarteringBriefOptional(
                                residual_qty=int(plan_brief_obj.pair_sell_side_bartering_brief.residual_qty + residual_qty))
                        update_plan_brief = PlanBriefBaseModel(id=plan_brief_obj.id,
                                                                 pair_sell_side_bartering_brief=update_bartering_side_brief)

                    update_plan_brief_dict = update_plan_brief.to_dict(exclude_none=True)
                    updated_plan_brief = (
                        await StreetBookServiceRoutesCallbackBaseNativeOverride.
                        underlying_partial_update_plan_brief_http(update_plan_brief_dict))
                else:
                    err_str_ = (f"No plan_brief found from plan_cache for symbol_side_key: "
                                f"{get_symbol_side_key([(security_id, side)])}")
                    logging.exception(err_str_)
                    raise HTTPException(status_code=500, detail=err_str_)

                # updating pair_plan's residual notional
                async with PlanStatus.reentrant_lock:
                    plan_status_tuple = self.plan_cache.get_plan_status()

                    if plan_status_tuple is not None:
                        plan_status, _ = plan_status_tuple
                        updated_residual = self.__get_residual_obj(side, updated_plan_brief)
                        if updated_residual is not None:
                            plan_status = {"_id": plan_status.id, "residual": updated_residual.to_dict()}
                            (await StreetBookServiceRoutesCallbackBaseNativeOverride.
                             underlying_partial_update_plan_status_http(plan_status))
                        else:
                            err_str_ = f"Something went wrong while computing residual for security_side_key: " \
                                       f"{get_symbol_side_key([(security_id, side)])}"
                            logging.exception(err_str_)
                            raise HTTPException(status_code=500, detail=err_str_)
                    else:
                        err_str_ = ("Received plan_status_tuple as None from plan_cache - ignoring plan_status update "
                                    "for residual changes")
                        logging.exception(err_str_)
                        raise HTTPException(status_code=500, detail=err_str_)

                # nothing to send since this query updates residuals only
                return []

    async def get_open_chore_count_query_pre(self, open_chore_count_class_type: Type[OpenChoreCount], symbol: str):
        open_chores = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_snapshot_http(
                get_open_chore_snapshots_for_symbol(symbol), self.get_generic_read_route())

        open_chore_count = OpenChoreCount.from_kwargs(open_chore_count=len(open_chores))
        return [open_chore_count]

    async def get_underlying_account_cumulative_fill_qty_query_pre(
            self, underlying_account_cum_fill_qty_class_type: Type[UnderlyingAccountCumFillQty],
            symbol: str, side: str):
        return await self.handle_get_underlying_account_cumulative_fill_qty_query_pre(symbol, side)

    async def get_symbol_side_underlying_account_cumulative_fill_qty_query_pre(
            self, fills_journal_class_type: Type[FillsJournal], symbol: str, side: str):
        return await self.handle_get_symbol_side_underlying_account_cumulative_fill_qty_query_pre(symbol, side)

    def get_residual_mark_secs(self):
        residual_mark_secs: int | None = None
        plan_limits_tuple = self.plan_cache.get_plan_limits()
        if plan_limits_tuple is not None:
            plan_limits, _ = plan_limits_tuple
            if plan_limits and plan_limits.residual_restriction:
                residual_mark_secs = plan_limits.residual_restriction.residual_mark_seconds
                if residual_mark_secs is None or residual_mark_secs == 0:
                    # if residual_mark_secs is 0 or None check is disabled - just return - no action
                    return
                else:
                    return residual_mark_secs
            else:
                if not plan_limits:
                    invalid_field = f"{plan_limits=}"
                else:
                    invalid_field = f"{plan_limits.residual_restriction=}"
                logging.error(f"Received plan_limits_tuple has {invalid_field} from plan_cache, ignoring cxl expiring"
                              f" chore for this call, will retry again in {self.min_refresh_interval} secs")
                return
        else:
            logging.error(f"Received plan_limits_tuple as None from plan_cache, ignoring cxl expiring chore "
                          f"for this call, will retry again in {self.min_refresh_interval} secs")
            return

    async def get_plan_brief_from_symbol_query_pre(self, plan_brief_class_type: Type[PlanBrief], security_id: str):
        return await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_brief_http(
            get_plan_brief_from_symbol(security_id), self.get_generic_read_route())

    async def get_executor_check_snapshot_query_pre(
            self, executor_check_snapshot_class_type: Type[ExecutorCheckSnapshot],
            symbol: str, side: str, last_n_sec: int):

        # avoid logging - both logged in call
        last_n_sec_chore_qty = await self.get_last_n_sec_chore_qty(symbol, Side(side), last_n_sec)
        last_n_sec_barter_qty = await self.get_last_n_sec_barter_qty(symbol, Side(side))

        if last_n_sec_chore_qty is not None and \
                last_n_sec_barter_qty is not None:
            # if no data is found by respective queries then all fields are set to 0 and every call returns
            # executor_check_snapshot object (except when exception occurs)
            executor_check_snapshot = \
                ExecutorCheckSnapshot(last_n_sec_barter_qty=last_n_sec_barter_qty,
                                      last_n_sec_chore_qty=last_n_sec_chore_qty)
            return [executor_check_snapshot]
        else:
            # will only return [] if some error occurred - outside market hours this is not an error
            # if plan cache not present - there is a bigger error detected elsewhere
            if self.plan_cache:
                if not self.market.is_non_bartering_time():
                    logging.error(f"no executor_check_snapshot for: {get_symbol_side_key([(symbol, Side(side))])}, as "
                                  f"received {last_n_sec_chore_qty=}, {last_n_sec_barter_qty=}, {last_n_sec=}; "
                                  f"returning empty list []")
                # else all good - outside bartering hours this is expected [except in simulation]
            else:
                logging.error(f"get_executor_check_snapshot_query_pre error: {get_symbol_side_key([(symbol, Side(side))])}, "
                              f"invalid {self.plan_cache=}; returning empty list []")
            return []

    async def get_symbol_overview_from_symbol_query_pre(self, symbol_overview_class_type: Type[SymbolOverview],
                                                        symbol: str):
        return await self.handle_get_top_of_book_from_symbol_query_pre(symbol)

    async def get_top_of_book_from_symbol_query_pre(self, top_of_book_class_type: Type[TopOfBook], symbol: str):
        return await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_top_of_book_http(
            get_objs_from_symbol(symbol))

    async def get_last_n_sec_total_barter_qty_by_aggregated_window_all_barters(
            self, last_sec_market_barter_vol_class_type: Type[LastNSecMarketBarterVol],
            symbol: str, last_n_sec: int) -> List[LastNSecMarketBarterVol]:
        last_barter_obj_list: List[LastBarter] = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_last_barter_http(
                get_last_n_sec_total_barter_qty(symbol, last_n_sec))
        last_n_sec_barter_vol = 0
        if last_barter_obj_list:
            last_n_sec_barter_vol = last_barter_obj_list[-1].market_barter_volume.participation_period_last_barter_qty_sum

        return [LastNSecMarketBarterVol(last_n_sec_barter_vol=last_n_sec_barter_vol)]

    async def get_last_n_sec_total_barter_qty_by_aggregated_window_first_n_lst_barters(
            self, last_sec_market_barter_vol_class_type: Type[LastNSecMarketBarterVol],
            symbol: str, last_n_sec: int) -> List[LastNSecMarketBarterVol]:
        symbol_side_key = get_symbol_side_key([(self.plan_leg_1.sec.sec_id, self.plan_leg_1.side)])
        first_last_barter_cont: FirstLastBarterCont | None = None
        if self.market.is_bartering_time() or self.market.is_uat():
            first_last_barter_cont = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_last_barter_http(
                    get_last_n_sec_first_n_last_barter(symbol, last_n_sec), projection_read_http, FirstLastBarterCont)
            if ((not first_last_barter_cont) or (not first_last_barter_cont.first) or (not first_last_barter_cont.last) or
                    (not first_last_barter_cont.first.market_barter_volume) or
                    (not first_last_barter_cont.last.market_barter_volume) or
                    (not first_last_barter_cont.first.market_barter_volume.participation_period_last_barter_qty_sum) or
                    (not first_last_barter_cont.last.market_barter_volume.participation_period_last_barter_qty_sum)):
                logging.error(f"not enough data to construct last_n_sec_barter_vol for: {symbol=}, returning 0;;;"
                              f"{first_last_barter_cont=}, {symbol_side_key=}")
                return [LastNSecMarketBarterVol(last_n_sec_barter_vol=0)]
        else:
            # outside bartering hours this is not a problem
            return [LastNSecMarketBarterVol(last_n_sec_barter_vol=0)]
        last_n_sec_trd_vol = (first_last_barter_cont.first.market_barter_volume.participation_period_last_barter_qty_sum -
                              first_last_barter_cont.last.market_barter_volume.participation_period_last_barter_qty_sum)
        if last_n_sec_trd_vol < 0:
            if first_last_barter_cont.first.exch_time == first_last_barter_cont.last.exch_time:
                last_n_sec_trd_vol = abs(last_n_sec_trd_vol)
                logging.debug(f"found -ive: {last_n_sec_trd_vol}, same exch timestamp on both {first_last_barter_cont=}")
            else:
                first_mtv = first_last_barter_cont.first.market_barter_volume
                last_mtv = first_last_barter_cont.last.market_barter_volume
                logging.error(f"unexpected found -ive {last_n_sec_trd_vol=} for {symbol=}, "
                              f"{first_mtv.participation_period_last_barter_qty_sum=}, "
                              f"{last_mtv.participation_period_last_barter_qty_sum=};;;{first_mtv=}, {last_mtv=}, "
                              f"{symbol_side_key=}")
                last_n_sec_trd_vol = 0
        return [LastNSecMarketBarterVol(last_n_sec_barter_vol=last_n_sec_trd_vol)]

    async def get_last_n_sec_total_barter_qty_query_pre(
            self, last_sec_market_barter_vol_class_type: Type[LastNSecMarketBarterVol],
            symbol: str, last_n_sec: int) -> List[LastNSecMarketBarterVol]:
        if self.total_barter_qty_by_aggregated_window_first_n_lst_barters:
            last_n_sec_trd_vol_list = await self.get_last_n_sec_total_barter_qty_by_aggregated_window_first_n_lst_barters(
                last_sec_market_barter_vol_class_type, symbol, last_n_sec)
        else:
            last_n_sec_trd_vol_list = await self.get_last_n_sec_total_barter_qty_by_aggregated_window_all_barters(
                last_sec_market_barter_vol_class_type, symbol, last_n_sec)
        return last_n_sec_trd_vol_list

    async def delete_symbol_overview_pre(self, obj_id: int):
        await self.handle_delete_symbol_overview_pre(obj_id)

    async def put_plan_to_snooze_query_pre(self, plan_status_class_type: Type[PlanStatus]):
        try:
            # removing current plan_status
            await self._check_n_remove_plan_status()

            # removing current plan limits
            await self._check_n_remove_plan_limits()

            # If plan_cache stopped means plan is not ongoing anymore or was never ongoing
            # - removing related models that would have created if plan got activated
            if self.plan_cache.stopped:
                # deleting plan's both leg's symbol_side_snapshots
                await self._check_n_delete_symbol_side_snapshot_from_unload_plan()

                # deleting plan's plan_brief
                await self._check_n_delete_plan_brief_for_unload_plan()

                # making force publish flag back to false for current plan's symbol's symbol_overview
                await self._force_unpublish_symbol_overview_from_unload_plan()

            # removing plan_alert
            try:
                log_book_service_http_client.remove_plan_alerts_for_plan_id_query_client(self.pair_plan_id)
            except Exception as e:
                err_str_ = f"Some Error occurred while removing plan_alerts in snoozing plan process, exception: {e}"
                raise HTTPException(detail=err_str_, status_code=500)

            # cleaning executor config.yaml file
            try:
                os.remove(self.simulate_config_yaml_file_path)
            except Exception as e:
                err_str_ = (f"Something went wrong while deleting executor_{self.pair_plan_id}_simulate_config.yaml, "
                            f"exception: {e}")
                logging.error(err_str_)

            # removing current plan's ports from cached ports
            remove_port_list = [
                self.cpp_port
            ]
            with FileLock(self.ports_cache_lock_file_path):
                with open(self.ports_cache_file_path, 'w+') as f:
                    ports_list = f.readlines()
                    for port in remove_port_list:
                        if port is not None and str(port) in ports_list:
                            ports_list.remove(str(port))
                        # else not required: ignore remove - None state can happen if plan started and ports are not
                        # yet assigned but plan is unloading

                    # setting cleaned list in cache
                    f.writelines(ports_list)
        except Exception as e:
            err_str_ = f"put_plan_to_snooze_query_pre faile with exception: {e}"
            logging.exception(err_str_)
            raise HTTPException(detail=err_str_, status_code=500)

        return []

    async def get_market_depths_query_pre(self, market_depth_class_type: Type[MarketDepth],
                                          payload_dict: Dict[str, Any]):
        symbol_side_tuple_list = payload_dict.get("symbol_side_tuple_list")
        if symbol_side_tuple_list is None:
            err_str_ = "Can't find symbol_side_tuple_list in payload from query"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)
        market_depth_list: List[MarketDepth] = []
        try:
            market_depth_list: List[MarketDepth] = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_market_depth_http(
                    get_market_depths(symbol_side_tuple_list))
        except Exception as e:
            logging.exception(f"get_market_depths_query_pre failed for: {symbol_side_tuple_list} with exception: {e};;;"
                              f"aggregate query: {get_market_depths(symbol_side_tuple_list)}")
        return market_depth_list

    async def get_plan_status_from_cache_query_pre(self, plan_status_class_type: Type[PlanStatus]):
        cached_plan_status_tuple = self.plan_cache.get_plan_status()
        if cached_plan_status_tuple is not None:
            cached_plan_status, _ = cached_plan_status_tuple
            if cached_plan_status is not None:
                return [cached_plan_status]
        return []

    async def get_symbol_side_snapshots_from_cache_query_pre(self,
                                                             symbol_side_snapshot_class_type: Type[SymbolSideSnapshot]):
        cached_symbol_side_snapshot_tuple = self.plan_cache.get_symbol_side_snapshot()
        if cached_symbol_side_snapshot_tuple is not None:
            cached_symbol_side_snapshot, _ = cached_symbol_side_snapshot_tuple
            if cached_symbol_side_snapshot is not None:
                return cached_symbol_side_snapshot
        return []

    async def get_plan_brief_from_cache_query_pre(self, plan_brief_class_type: Type[PlanBrief]):
        cached_plan_brief_tuple = self.plan_cache.get_plan_brief()
        if cached_plan_brief_tuple is not None:
            cached_plan_brief, _ = cached_plan_brief_tuple
            if cached_plan_brief is not None:
                return [cached_plan_brief]
        return []

    async def get_new_chore_from_cache_query_pre(self, new_chore_class_type: Type[NewChore]):
        cached_new_chore_tuple = self.plan_cache.get_new_chore()
        if cached_new_chore_tuple is not None:
            cached_new_chore, _ = cached_new_chore_tuple
            if cached_new_chore is not None:
                return cached_new_chore
        return []

    async def get_plan_limits_from_cache_query_pre(self, plan_limits_class_type: Type[PlanLimits]):
        cached_plan_limits_tuple = self.plan_cache.get_plan_limits()
        if cached_plan_limits_tuple is not None:
            cached_plan_limits, _ = cached_plan_limits_tuple
            if cached_plan_limits is not None:
                return [cached_plan_limits]
        return []

    async def get_chore_journals_from_cache_query_pre(self, chore_journal_class_type: Type[ChoreJournal]):
        cached_chore_journal_tuple = self.plan_cache.get_chore_journal()
        if cached_chore_journal_tuple is not None:
            cached_chore_journal, _ = cached_chore_journal_tuple
            if cached_chore_journal is not None:
                return cached_chore_journal
        return []

    async def get_fills_journal_from_cache_query_pre(self, fills_journal_class_type: Type[FillsJournal]):
        cached_fills_journal_tuple = self.plan_cache.get_fills_journal()
        if cached_fills_journal_tuple is not None:
            cached_fills_journal, _ = cached_fills_journal_tuple
            if cached_fills_journal is not None:
                return cached_fills_journal
        return []

    async def get_chore_snapshots_from_cache_query_pre(self, chore_snapshot_class_type: Type[ChoreSnapshot]):
        cached_chore_snapshot_tuple = self.plan_cache.get_chore_snapshot()
        if cached_chore_snapshot_tuple is not None:
            cached_chore_snapshot, _ = cached_chore_snapshot_tuple
            if cached_chore_snapshot is not None:
                return cached_chore_snapshot
        return []

    async def get_tob_of_book_from_cache_query_pre(self, top_of_book_class_type: Type[TopOfBookBaseModel]):
        # used in test case to verify cache after recovery
        tob_list = []

        leg_1_tob_of_book = self.leg1_symbol_cache.get_top_of_book()
        leg_2_tob_of_book = self.leg2_symbol_cache.get_top_of_book()

        if leg_1_tob_of_book is not None:
            tob_list.append(leg_1_tob_of_book)

        if leg_2_tob_of_book is not None:
            tob_list.append(leg_2_tob_of_book)
        return tob_list

    #########################
    # Barter Simulator Queries
    #########################

    async def barter_simulator_place_new_chore_query_pre(
            self, barter_simulator_process_new_chore_class_type: Type[BarterSimulatorProcessNewChore],
            px: float, qty: int, side: Side, bartering_sec_id: str, system_sec_id: str, symbol_type: str,
            underlying_account: str, exchange: str | None = None, internal_ord_id: str | None = None):
        try:
            return await self.handle_barter_simulator_place_new_chore_query_pre(
                px, qty, side, bartering_sec_id, system_sec_id, symbol_type, underlying_account, exchange, internal_ord_id)
        except Exception as e_:
            err_str_ = f"barter_simulator_place_new_chore_query_pre failed: exception: {e_}"
            logging.exception(err_str_)
            raise HTTPException(detail=err_str_, status_code=500)

    async def barter_simulator_place_cxl_chore_query_pre(
            self, barter_simulator_process_cxl_chore_class_type: Type[BarterSimulatorProcessCxlChore],
            chore_id: str, side: Side | None = None, bartering_sec_id: str | None = None,
            system_sec_id: str | None = None, underlying_account: str | None = None):
        try:
            return await self.handle_barter_simulator_place_cxl_chore_query_pre(chore_id, side, bartering_sec_id,
                                                                               system_sec_id, underlying_account)
        except Exception as e_:
            err_str_ = f"barter_simulator_place_cxl_chore_query_pre failed: exception: {e_}"
            logging.exception(err_str_)
            raise HTTPException(detail=err_str_, status_code=500)


    async def barter_simulator_process_chore_ack_query_pre(
            self, barter_simulator_process_chore_ack_class_type: Type[BarterSimulatorProcessChoreAck], chore_id: str,
            px: float, qty: int, side: Side, sec_id: str, underlying_account: str):
        return await self.handle_barter_simulator_process_chore_ack_query_pre(chore_id, px, qty, side,
                                                                             sec_id, underlying_account)

    async def barter_simulator_process_fill_query_pre(
            self, barter_simulator_process_fill_class_type: Type[BarterSimulatorProcessFill], chore_id: str,
            px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
            use_exact_passed_qty: bool | None = None):
        return await self.handle_barter_simulator_process_fill_query_pre(chore_id, px, qty, side, sec_id,
                                                                        underlying_account, use_exact_passed_qty)

    async def barter_simulator_reload_config_query_pre(
            self, barter_simulator_reload_config_class_type: Type[BarterSimulatorReloadConfig]):
        return await self.handle_barter_simulator_reload_config_query_pre()

    async def barter_simulator_process_amend_req_query_pre(
            self, barter_simulator_process_amend_req_class_type: Type[BarterSimulatorProcessAmendReq],
            chore_id: str, side: Side, sec_id: str, underlying_account: str, chore_event: ChoreEventType,
            px: float | None = None, qty: int | None = None):
        return await self.handle_barter_simulator_process_amend_req_query_pre(chore_id, side, sec_id,
                                                                             underlying_account, chore_event, px, qty)

    async def barter_simulator_process_amend_ack_query_pre(
            self, barter_simulator_process_amend_ack_class_type: Type[BarterSimulatorProcessAmendAck],
            chore_id: str, side: Side, sec_id: str, underlying_account: str):
        return await self.handle_barter_simulator_process_amend_ack_query_pre(chore_id, side, sec_id, underlying_account)

    async def barter_simulator_process_amend_rej_query_pre(
            self, barter_simulator_process_amend_ack_class_type: Type[BarterSimulatorProcessAmendAck],
            chore_id: str, side: Side, sec_id: str, underlying_account: str):
        return await self.handle_barter_simulator_process_amend_rej_query_pre(chore_id, side, sec_id, underlying_account)

    async def barter_simulator_process_lapse_query_pre(
            self, barter_simulator_process_lapse_class_type: Type[BarterSimulatorProcessLapse],
            chore_id: str, side: Side, sec_id: str, underlying_account: str, qty: int | None = None):
        return await self.handle_barter_simulator_process_lapse_query_pre(chore_id, side, sec_id,
                                                                         underlying_account, qty)

