# python imports
import copy
import json
import logging
import os
import signal
import subprocess

import time
import sys
from typing import Type, Set, Final
import asyncio
from pathlib import PurePath
from datetime import date
import threading

# third-party package imports
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pymongo import MongoClient

# project imports
from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes_callback import \
    StratManagerServiceRoutesCallback
from Flux.CodeGenProjects.addressbook.app.addressbook_service_helper import is_service_up, \
    get_single_exact_match_ongoing_strat_from_symbol_n_side, get_portfolio_limits, \
    create_portfolio_limits, get_order_limits, create_order_limits, except_n_log_alert, \
    get_symbol_side_key, get_ongoing_strats_from_symbol_n_side, config_yaml_dict, \
    CURRENT_PROJECT_DIR, server_port, strat_manager_service_native_http_client, YAMLConfigurationManager
from Flux.CodeGenProjects.addressbook.app.pair_strat_models_log_keys import get_pair_strat_log_key
from Flux.CodeGenProjects.addressbook.app.static_data import SecurityRecordManager
from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_client import (
    StratExecutorServiceHttpClient)
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import (
    StratState, StratStatusBaseModel, StratDetails)


class StratManagerServiceRoutesCallbackBaseNativeOverride(StratManagerServiceRoutesCallback):
    def __init__(self):
        self.asyncio_loop = None
        self.service_up: bool = False
        self.service_ready: bool = False
        self.static_data: SecurityRecordManager | None = None
        # restricted variable: don't overuse this will be extended to multi-currency support
        self.usd_fx_symbol: Final[str] = "USD|SGD"
        self.fx_symbol_overview_dict: Dict[str, FxSymbolOverviewBaseModel | None] = {"USD|SGD": None}
        self.usd_fx = None
        self.port_to_process_dict: Dict[int, subprocess.Popen] = {}
        self.port_to_web_client_dict = {}

        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30

        super().__init__()

    def _check_and_create_order_and_portfolio_limits(self) -> None:
        if (order_limits := get_order_limits()) is None:
            order_limits = create_order_limits()
        if (portfolio_limits := get_portfolio_limits()) is None:
            portfolio_limits = create_portfolio_limits()
        return

    @except_n_log_alert(severity=Severity.Severity_CRITICAL)
    async def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up, then create portfolio limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair strats at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"addressbook_{server_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    self.service_ready = True
                if not self.service_up:
                    try:
                        if is_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                            self._check_and_create_order_and_portfolio_limits()
                            await self.run_existing_executors()
                        else:
                            should_sleep = True
                            service_up_no_error_retry_count -= 1
                    except Exception as e:
                        logging.exception("unexpected: service startup threw exception, "
                                          f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                          f";;;exception: {e}", exc_info=True)
                else:
                    should_sleep = True
                    # any periodic refresh code goes here
            else:
                should_sleep = True

    async def run_existing_executors(self) -> None:
        existing_pair_strats = strat_manager_service_native_http_client.get_all_pair_strat_client()
        for pair_strat in existing_pair_strats:
            await self._start_executor_server(pair_strat)

    async def read_all_portfolio_status_pre(self):
        if not self.asyncio_loop:
            self.asyncio_loop = asyncio.get_running_loop()

    def get_usd_px(self, px: float, system_symbol: str):
        """
        assumes single currency strat for now - may extend to accept symbol and send revised px according to
        underlying trading currency
        """
        return px / self.usd_fx

    def get_local_px_or_notional(self, px_or_notional: float, system_symbol: str):
        return px_or_notional * self.usd_fx

    def app_launch_pre(self):
        app_launch_pre_thread = threading.Thread(target=asyncio.run,
                                                 args=(self._app_launch_pre_thread_func(),), daemon=True)
        app_launch_pre_thread.start()
        logging.debug("Triggered server launch pre override")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

    def get_generic_read_route(self):
        return None

    # Example: Soft API Query Interfaces

    async def update_portfolio_status_by_order_or_fill_data_query_pre(
            self, portfolio_status_class_type: Type[PortfolioStatus], overall_buy_notional: float | None = None,
            overall_sell_notional: float | None = None, overall_buy_fill_notional: float | None = None,
            overall_sell_fill_notional: float | None = None):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_http_routes import (
            underlying_partial_update_portfolio_status_http, underlying_read_portfolio_status_by_id_http)

        async with PortfolioStatus.reentrant_lock:
            updated_portfolio_status = PortfolioStatusOptional()
            portfolio_status: PortfolioStatus = await underlying_read_portfolio_status_by_id_http(1)

            updated_portfolio_status.id = portfolio_status.id
            if overall_buy_notional is not None:
                if portfolio_status.overall_buy_notional is None:
                    portfolio_status.overall_buy_notional = 0
                updated_portfolio_status.overall_buy_notional = (portfolio_status.overall_buy_notional +
                                                                 overall_buy_notional)
            if overall_sell_notional is not None:
                if portfolio_status.overall_sell_notional is None:
                    portfolio_status.overall_sell_notional = 0
                updated_portfolio_status.overall_sell_notional = (portfolio_status.overall_sell_notional +
                                                                  overall_sell_notional)
            if overall_buy_fill_notional is not None:
                if portfolio_status.overall_buy_fill_notional is None:
                    portfolio_status.overall_buy_fill_notional = 0
                updated_portfolio_status.overall_buy_fill_notional = (portfolio_status.overall_buy_fill_notional +
                                                                      overall_buy_fill_notional)
            if overall_sell_fill_notional is not None:
                if portfolio_status.overall_sell_fill_notional is None:
                    portfolio_status.overall_sell_fill_notional = 0
                updated_portfolio_status.overall_sell_fill_notional = (portfolio_status.overall_sell_fill_notional +
                                                                       overall_sell_fill_notional)

            await underlying_partial_update_portfolio_status_http(
                json.loads(updated_portfolio_status.json(by_alias=True, exclude_none=True)))

        return []

    # Code-generated
    async def get_pair_strat_sec_filter_json_query_pre(self, pair_strat_class_type: Type[PairStrat], security_id: str):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_http_routes import \
            underlying_read_pair_strat_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_ongoing_pair_strat_filter
        return await underlying_read_pair_strat_http(get_ongoing_pair_strat_filter(security_id),
                                                     self.get_generic_read_route())

    def _set_derived_side(self, pair_strat_obj: PairStrat):
        raise_error = False
        if pair_strat_obj.pair_strat_params.strat_leg2.side is None or \
                pair_strat_obj.pair_strat_params.strat_leg2.side == Side.SIDE_UNSPECIFIED:
            if pair_strat_obj.pair_strat_params.strat_leg1.side == Side.BUY:
                pair_strat_obj.pair_strat_params.strat_leg2.side = Side.SELL
            elif pair_strat_obj.pair_strat_params.strat_leg1.side == Side.SELL:
                pair_strat_obj.pair_strat_params.strat_leg2.side = Side.BUY
            else:
                raise_error = True
        elif pair_strat_obj.pair_strat_params.strat_leg1.side is None:
            raise_error = True
        # else not required, all good
        if raise_error:
            # handles pair_strat_obj.pair_strat_params.strat_leg1.side == None and all other unsupported values
            raise Exception(f"error: _set_derived_side called with unsupported side combo on legs, leg1: "
                            f"{pair_strat_obj.pair_strat_params.strat_leg1.side} leg2: "
                            f"{pair_strat_obj.pair_strat_params.strat_leg2.side} in pair strat: {pair_strat_obj}")

    def _set_derived_exchange(self, pair_strat_obj: PairStrat):
        """
        update the exchange of derived (if we have one)
        """
        return

    async def get_dismiss_filter_portfolio_limit_brokers_query_pre(
            self, dismiss_filter_portfolio_limit_broker_class_type: Type[DismissFilterPortfolioLimitBroker],
            security_id1: str, security_id2: str):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_http_routes import (
            underlying_read_portfolio_limits_http)

        # get security name from : pair_strat_params.strat_legs and then redact pattern
        # security.sec_id (a pattern in positions) where there is a value match
        dismiss_filter_agg_pipeline = {'redact': [("security.sec_id",
                                                   security_id1,
                                                   security_id2)]}
        filtered_portfolio_limits: List[PortfolioLimits] = await underlying_read_portfolio_limits_http(
            dismiss_filter_agg_pipeline, self.get_generic_read_route())
        if len(filtered_portfolio_limits) == 1:
            if filtered_portfolio_limits[0].eligible_brokers is not None:
                eligible_brokers = [eligible_broker for eligible_broker in
                                    filtered_portfolio_limits[0].eligible_brokers if
                                    eligible_broker.sec_positions]
                return_obj = DismissFilterPortfolioLimitBroker(brokers=eligible_brokers)
                return [return_obj]
        elif len(filtered_portfolio_limits) > 1:
            err_str_ = f"filtered_portfolio_limits expected: 1, found: " \
                       f"{str(len(filtered_portfolio_limits))}, for filter: " \
                       f"{dismiss_filter_agg_pipeline}, filtered_portfolio_limits: " \
                       f"{filtered_portfolio_limits}; use SWAGGER UI to check / fix and re-try "
            logging.error(err_str_)
            raise HTTPException(status_code=500, detail=err_str_)
        else:
            err_str_ = (f"No filtered_portfolio_limits found for symbols of leg1 and leg2: {security_id1} and "
                        f"{security_id2}")
            logging.warning(err_str_)
            raise HTTPException(status_code=500, detail=err_str_)

    @except_n_log_alert(severity=Severity.Severity_ERROR)
    async def create_pair_strat_pre(self, pair_strat_obj: PairStrat):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"create_pair_strat_pre not ready - service is not initialized yet, " \
                       f"pair_strat_key: {get_pair_strat_log_key(pair_strat_obj)};;; pair_strat: {pair_strat_obj}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        self._set_derived_side(pair_strat_obj)
        self._set_derived_exchange(pair_strat_obj)
        pair_strat_obj.frequency = 1
        pair_strat_obj.pair_strat_params_update_seq_num = 0
        pair_strat_obj.last_active_date_time = DateTime.utcnow()

        port_list = list(self.port_to_process_dict)
        if not port_list:
            port = 8041
        else:
            port = max(port_list) + 1
        pair_strat_obj.host = "127.0.0.1"  # todo: Hardcoded for now
        pair_strat_obj.port = port
        pair_strat_obj.is_executor_running = False

        # starting executor server for current pair strat
        await self._start_executor_server(pair_strat_obj)

    @except_n_log_alert(severity=Severity.Severity_ERROR)
    async def create_pair_strat_post(self, pair_strat_obj: PairStrat):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_http_routes import (
            underlying_read_strat_collection_http, underlying_create_strat_collection_http,
            underlying_update_strat_collection_http)

        async with StratCollection.reentrant_lock:
            strat_collection_obj_list = await underlying_read_strat_collection_http()

            strat_key = f"{pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id}-" \
                        f"{pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id}-" \
                        f"{pair_strat_obj.pair_strat_params.strat_leg1.side}-{pair_strat_obj.id}"
            if len(strat_collection_obj_list) == 0:
                created_strat_collection = StratCollection(**{
                    "_id": 1,
                    "loaded_strat_keys": [
                        strat_key
                    ],
                    "buffered_strat_keys": []
                })
                created_strat_collection = await underlying_create_strat_collection_http(created_strat_collection)
            else:
                strat_collection_obj = strat_collection_obj_list[0]
                strat_collection_obj.loaded_strat_keys.append(strat_key)
                await underlying_update_strat_collection_http(strat_collection_obj)

    async def update_pair_strat_pre(self, stored_pair_strat_obj: PairStrat, updated_pair_strat_obj: PairStrat):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_pair_strat_pre not ready - service is not initialized yet, " \
                       f"pair_strat_key: {get_pair_strat_log_key(updated_pair_strat_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if updated_pair_strat_obj.frequency is None:
            updated_pair_strat_obj.frequency = 0
        updated_pair_strat_obj.frequency += 1

        if updated_pair_strat_obj.pair_strat_params_update_seq_num is None:
            updated_pair_strat_obj.pair_strat_params_update_seq_num = 0
        updated_pair_strat_obj.pair_strat_params_update_seq_num += 1
        updated_pair_strat_obj.last_active_date_time = DateTime.utcnow()

        return updated_pair_strat_obj

    async def partial_update_pair_strat_pre(self, stored_pair_strat_obj: PairStrat, updated_pair_strat_obj_dict: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "partial_update_pair_strat_pre not ready - service is not initialized yet, " \
                       f"pair_strat_key: {get_pair_strat_log_key(stored_pair_strat_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        updated_pair_strat_obj_dict["frequency"] = stored_pair_strat_obj.frequency + 1

        if updated_pair_strat_obj_dict.get("pair_strat_params") is not None:
            if stored_pair_strat_obj.pair_strat_params_update_seq_num is None:
                updated_pair_strat_obj_dict["pair_strat_params_update_seq_num"] = 0
            updated_pair_strat_obj_dict["pair_strat_params_update_seq_num"] = \
                stored_pair_strat_obj.pair_strat_params_update_seq_num + 1

        updated_pair_strat_obj_dict["last_active_date_time"] = DateTime.utcnow()
        return updated_pair_strat_obj_dict

    async def _start_executor_server(self, pair_strat: PairStrat) -> None:
        port = pair_strat.port
        # creating config file for this server run if not exists
        code_gen_projects_dir = PurePath(__file__).parent.parent.parent
        config_file_path = (code_gen_projects_dir / "strat_executor" /
                            "data" / f"strat_executor_{port}_config.yaml")

        temp_config_file_path = code_gen_projects_dir / "template_yaml_configs" / "server_config.yaml"
        with open(temp_config_file_path, "r") as temp_config:
            config_lines = temp_config.readlines()

        with open(config_file_path, "w") as new_config_file:
            # first writing strat info to config
            strat_leg: StratLeg
            new_config_file.write(f"pair_strat_id: {pair_strat.id}\n")
            for index, strat_leg in enumerate([pair_strat.pair_strat_params.strat_leg1,
                                               pair_strat.pair_strat_params.strat_leg2]):
                if strat_leg is not None:
                    new_config_file.write(f"strat_leg_{index + 1}:\n")
                    new_config_file.write(f'  exch_id: "{strat_leg.exch_id}"\n')
                    new_config_file.write(f'  sec:\n')
                    new_config_file.write(f'    sec_id: {strat_leg.sec.sec_id}\n')
                    new_config_file.write(f'    sec_type: {strat_leg.sec.sec_type}\n')
                    new_config_file.write(f'  side: "{strat_leg.side}"\n')
                    new_config_file.write(f'  company: "{strat_leg.company}"\n')
            new_config_file.write("\n")

            for config_line in config_lines:
                if "beanie_port:" in config_line:
                    config_line = f"beanie_port: '{port}'\n"
                new_config_file.write(config_line)

        path = code_gen_projects_dir / "strat_executor" / "scripts"
        executor = subprocess.Popen(['python', 'launch_beanie_fastapi.py', f'{port}', '&'], cwd=path)
        self.port_to_process_dict[port] = executor
        current_port_web_client = StratExecutorServiceHttpClient.set_or_get_if_instance_exists(
            pair_strat.host, pair_strat.port)
        self.port_to_web_client_dict[port] = current_port_web_client

    def _close_executor_server(self, port: int) -> None:
        process = self.port_to_process_dict[port]
        process.terminate()

    async def get_ongoing_strats_symbol_n_exch_query_pre(self,
                                                         ongoing_strat_symbols_class_type: Type[
                                                             OngoingStratsSymbolNExchange]):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_http_routes import \
            underlying_read_pair_strat_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_ongoing_pair_strat_filter

        pair_strat_list: List[PairStrat] = await underlying_read_pair_strat_http(get_ongoing_pair_strat_filter(),
                                                                                 self.get_generic_read_route())
        ongoing_symbol_n_exch_set: Set[str] = set()
        ongoing_strat_symbols_n_exchange = OngoingStratsSymbolNExchange(symbol_n_exchange=[])

        before_len: int = 0
        for pair_strat in pair_strat_list:
            leg1_symbol = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
            leg1_exch = pair_strat.pair_strat_params.strat_leg1.exch_id
            leg2_symbol = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
            leg2_exch = pair_strat.pair_strat_params.strat_leg2.exch_id
            leg1_symbol_n_exch = SymbolNExchange(symbol=leg1_symbol, exchange=leg1_exch)
            leg2_symbol_n_exch = SymbolNExchange(symbol=leg2_symbol, exchange=leg2_exch)

            ongoing_symbol_n_exch_set.add(f"{leg1_symbol}_{leg1_exch}")
            if len(ongoing_symbol_n_exch_set) == before_len + 1:
                ongoing_strat_symbols_n_exchange.symbol_n_exchange.append(leg1_symbol_n_exch)
                before_len += 1

            ongoing_symbol_n_exch_set.add(f"{leg2_symbol}_{leg2_exch}")
            if len(ongoing_symbol_n_exch_set) == before_len + 1:
                ongoing_strat_symbols_n_exchange.symbol_n_exchange.append(leg2_symbol_n_exch)
                before_len += 1
        return [ongoing_strat_symbols_n_exchange]

    @staticmethod
    def get_id_from_strat_key(unloaded_strat_key: str) -> int:
        parts: List[str] = (unloaded_strat_key.split("-"))
        return parse_to_int(parts[-1])

    def _drop_executor_db_for_deleting_pair_strat(self, mongo_server_uri: str, port: int, sec_id: str, side: Side):
        if mongo_server_uri is not None:
            mongo_client = MongoClient(mongo_server_uri)
            db_name: str = f"strat_executor_{port}"

            if db_name in mongo_client.list_database_names():
                mongo_client.drop_database(db_name)
            else:
                err_str_ = (f"Unexpected: Database: '{db_name}' not found in mongo_client for uri: "
                            f"{mongo_server_uri} being used by current strat, "
                            f"symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)
        else:
            err_str_ = (f"key 'mongo_server' missing in strat_executor_{port}_config.yaml, ignoring this"
                        f"strat delete, symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=400)

    async def delete_pair_strat_pre(self, pydantic_obj_to_be_deleted: PairStrat):
        port: int = pydantic_obj_to_be_deleted.port
        sec_id = pydantic_obj_to_be_deleted.pair_strat_params.strat_leg1.sec.sec_id
        side = pydantic_obj_to_be_deleted.pair_strat_params.strat_leg1.side
        if pydantic_obj_to_be_deleted.is_executor_running:
            strat_web_client: StratExecutorServiceHttpClient = self.port_to_web_client_dict.get(port)

            if strat_web_client is None:
                err_str_ = ("Can't find any web_client present in server cache dict for ongoing strat of "
                            f"port: {port}, ignoring this strat delete, likely bug in server cache dict handling, "
                            f"symbol_side_key: {get_symbol_side_key([(sec_id, side)])};;; "
                            f"pair_strat: {pydantic_obj_to_be_deleted}")
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)

            strat_details_list: List[StratDetails] = strat_web_client.is_strat_ongoing_query_client()
            if strat_details_list:
                strat_details = strat_details_list[0]
            else:
                err_str_ = ("Received empty strat_details list from is_strat_ongoing_query_client call "
                            f"of strat_executor for port {port}, ignoring this strat delete, symbol_side_key: "
                            f"{get_symbol_side_key([(sec_id, side)])};;; pair_strat: {pydantic_obj_to_be_deleted}")
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)

            if strat_details.is_ongoing:
                err_str_ = ("This strat is ongoing: Deletion of ongoing strat is no supported, "
                            "ignoring this strat delete, try again once it is"
                            f"not ongoing, symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)

            # removing and updating relative models
            try:
                strat_web_client.put_strat_to_snooze_query_client()
            except Exception as e:
                err_str_ = ("Some error occurred in executor while setting strat to SNOOZED state, ignoring "
                            f"delete of this strat, symbol_side_key: {get_symbol_side_key([(sec_id, side)])}, ;;;"
                            f"pair_strat: {pydantic_obj_to_be_deleted}")
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)
            self._close_executor_server(port)  # closing executor

            # Dropping database for this strat
            code_gen_projects_dir = PurePath(__file__).parent.parent.parent
            server_config_file_path = (code_gen_projects_dir / "strat_executor" /
                                       "data" / f"strat_executor_{port}_config.yaml")
            if os.path.exists(server_config_file_path):
                server_config_yaml_dict = (
                    YAMLConfigurationManager.load_yaml_configurations(str(server_config_file_path)))
                mongo_server_uri = server_config_yaml_dict.get("mongo_server")
                self._drop_executor_db_for_deleting_pair_strat(mongo_server_uri, port, sec_id, side)
            else:
                err_str_ = (f"Config file for port: {port} missing, must exists since executor is running from this"
                            f"config, ignoring this strat delete, symbol_side_key: "
                            f"{get_symbol_side_key([(sec_id, side)])}")
                logging.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=400)

            # Finally removing config file for this strat
            os.remove(server_config_file_path)

        else:
            err_str_ = ("Strat is not running, Deletion of strat that is not in running_state is not supported, "
                        "please load strat and make it not ongoing and then retry, ignoring this strat delete, "
                        f"symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=400)

    async def unload_pair_strats(self, stored_strat_collection_obj: StratCollection,
                                 updated_strat_collection_obj: StratCollection) -> None:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_http_routes import \
            underlying_read_pair_strat_by_id_http
        updated_strat_collection_loaded_strat_keys_frozenset = frozenset(updated_strat_collection_obj.loaded_strat_keys)
        stored_strat_collection_loaded_strat_keys_frozenset = frozenset(stored_strat_collection_obj.loaded_strat_keys)
        # existing items in stored loaded frozenset but not in the updated stored frozen set need to move to done state
        unloaded_strat_keys_frozenset = stored_strat_collection_loaded_strat_keys_frozenset.difference(
            updated_strat_collection_loaded_strat_keys_frozenset)
        if len(unloaded_strat_keys_frozenset) != 0:
            unloaded_strat_key: str
            for unloaded_strat_key in unloaded_strat_keys_frozenset:
                if unloaded_strat_key in updated_strat_collection_obj.buffered_strat_keys:  # unloaded not deleted
                    pair_strat_id: int = self.get_id_from_strat_key(unloaded_strat_key)
                    pair_strat = await underlying_read_pair_strat_by_id_http(pair_strat_id)
                    strat_web_client: StratExecutorServiceHttpClient = self.port_to_web_client_dict.get(pair_strat.port)

                    if strat_web_client is None:
                        err_str_ = ("Can't find any web_client present in server cache dict for ongoing strat of "
                                    f"port: {pair_strat.port}, ignoring this strat unload, "
                                    f"likely bug in server cache dict handling;;; "
                                    f"pair_strat: {pair_strat}")
                        logging.error(err_str_)
                        raise HTTPException(status_code=500, detail=err_str_)

                    strat_details_list: List[StratDetails] = strat_web_client.is_strat_ongoing_query_client()
                    if strat_details_list:
                        strat_details = strat_details_list[0]
                    else:
                        err_str_ = ("Received empty strat_details list from is_strat_ongoing_query_client call "
                                    f"of strat_executor for port {pair_strat.port};;; "
                                    f"pair_strat: {pair_strat}")
                        logging.error(err_str_)
                        raise HTTPException(status_code=500, detail=err_str_)
                    if strat_details.is_ongoing:
                        # is_strat_ongoing_query_client returns strat_status if is ongoing else returns empty list
                        error_str = f"unloading and ongoing pair strat key: {unloaded_strat_key} is not supported, " \
                                    f"current strat state: {strat_details.current_state}, " \
                                    f"pair_strat_key: {get_pair_strat_log_key(pair_strat)};;; pair_strat: {pair_strat}"
                        logging.error(error_str)
                        raise HTTPException(status_code=400, detail=error_str)
                    elif strat_details.current_state in [StratState.StratState_DONE, StratState.StratState_READY]:
                        # removing and updating relative models
                        try:
                            strat_web_client.put_strat_to_snooze_query_client()
                        except Exception as e:
                            err_str_ = (
                                "Some error occurred in executor while setting strat to SNOOZED state, ignoring "
                                f"unload of this strat, pair_strat_key: {get_pair_strat_log_key(pair_strat)}, ;;;"
                                f"pair_strat: {pair_strat}")
                            logging.error(err_str_)
                            raise HTTPException(status_code=500, detail=err_str_)
                        self._close_executor_server(pair_strat.port)    # closing executor
                    elif strat_details.current_state == StratState.StratState_SNOOZED:
                        err_str_ = (f"Unloading strat with strat_state: {strat_details.current_state} is not supported,"
                                    f"pair_strat_key: "
                                    f"{get_pair_strat_log_key(pair_strat)};;; pair_strat: {pair_strat}")
                        logging.error(err_str_)
                    else:
                        err_str_ = (f"Unloading strat with strat_state: {strat_details.current_state} is not supported,"
                                    f"try unloading when start is READY or DONE, pair_strat_key: "
                                    f"{get_pair_strat_log_key(pair_strat)};;; pair_strat: {pair_strat}")
                        logging.error(err_str_)
                        raise Exception(err_str_)
                # else: deleted not unloaded - nothing to do , DB will remove entry

    async def reload_pair_strats(self, stored_strat_collection_obj: StratCollection,
                                 updated_strat_collection_obj: StratCollection) -> None:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_http_routes import \
            underlying_read_pair_strat_by_id_http, underlying_delete_pair_strat_http, underlying_create_pair_strat_http
        updated_strat_collection_buffered_strat_keys_frozenset = frozenset(
            updated_strat_collection_obj.buffered_strat_keys)
        stored_strat_collection_buffered_strat_keys_frozenset = frozenset(
            stored_strat_collection_obj.buffered_strat_keys)
        # existing items in stored buffered frozenset but not in the updated stored frozen set need to
        # move to ready state
        reloaded_strat_keys_frozenset = stored_strat_collection_buffered_strat_keys_frozenset.difference(
            updated_strat_collection_buffered_strat_keys_frozenset)
        if len(reloaded_strat_keys_frozenset) != 0:
            reloaded_strat_key: str
            for reloaded_strat_key in reloaded_strat_keys_frozenset:
                if reloaded_strat_key in updated_strat_collection_obj.loaded_strat_keys:  # loaded not deleted
                    pair_strat_id: int = self.get_id_from_strat_key(reloaded_strat_key)
                    pair_strat = await underlying_read_pair_strat_by_id_http(pair_strat_id)

                    # starting snoozed server
                    await self._start_executor_server(pair_strat)

                # else: deleted not loaded - nothing to do , DB will remove entry

    async def update_strat_collection_pre(self, stored_strat_collection_obj: StratCollection,
                                          updated_strat_collection_obj: StratCollection):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_strat_collection_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        # handling unloading pair_strats
        await self.unload_pair_strats(stored_strat_collection_obj, updated_strat_collection_obj)

        # handling reloading pair_strat
        await self.reload_pair_strats(stored_strat_collection_obj, updated_strat_collection_obj)

        return updated_strat_collection_obj

    async def get_ongoing_strat_from_symbol_side_query_pre(self, pair_strat_class_type: Type[PairStrat], sec_id: str,
                                                           side: Side):
        ongoing_strat = await get_single_exact_match_ongoing_strat_from_symbol_n_side(sec_id, side)
        if ongoing_strat is None:
            # checking if no match found or if something unexpected happened
            match_level_1_pair_strats, match_level_2_pair_strats = \
                await get_ongoing_strats_from_symbol_n_side(sec_id, side)
            if len(match_level_1_pair_strats) == 0 and len(match_level_2_pair_strats) == 0:
                return []
            else:
                err_str_ = "Something unexpected happened while fetching ongoing strats, " \
                           f"please check logs for more details, symbol_side_snapshot: " \
                           f"{get_symbol_side_key([(sec_id, side)])}"
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)
        return [ongoing_strat]

    async def create_command_n_control_pre(self, command_n_control_obj: CommandNControl):
        match command_n_control_obj.command_type:
            case CommandType.RESET_STATE:
                from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_beanie_database \
                    import document_models
                for document_model in document_models:
                    document_model._cache_obj_id_to_obj_dict = {}
            case other_:
                logging.error(f"create_command_n_control_pre failed. unrecognized command_type: {other_}")

    async def filtered_notify_pair_strat_update_query_ws_pre(self):
        return filter_ws_pair_strat


def filter_ws_pair_strat(pair_strat_obj_json: Dict, **kwargs):
    symbols = kwargs.get("symbols")
    pair_strat_params = pair_strat_obj_json.get("pair_strat_params")
    if pair_strat_params is not None:
        strat_leg1 = pair_strat_params.get("strat_leg1")
        strat_leg2 = pair_strat_params.get("strat_leg2")
        if strat_leg1 is not None and strat_leg2 is not None:
            security1 = strat_leg1.get("sec")
            security2 = strat_leg2.get("sec")
            if security1 is not None and security2 is not None:
                sec1_id = security1.get("sec_id")
                sec2_id = security2.get("sec_id")
                if sec1_id in symbols or sec2_id in symbols:
                    return True
    return False
