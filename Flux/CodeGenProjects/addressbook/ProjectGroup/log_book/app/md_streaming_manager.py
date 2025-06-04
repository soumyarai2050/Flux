import os
import stat
import subprocess
import time

from pathlib import PurePath
from typing import Dict, List, Tuple, Final, Any, Set
import logging

from pendulum import DateTime

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecordManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    MDShellEnvData, create_md_shell_script, create_stop_md_script)

class SymbolStreamingData:

    def __init__(self, run_symbol_overview_file_path: PurePath, stop_so_file_paths: PurePath):
        # increment on MD trigger request (0->1 real trigger) and decrement on MD stop request (1->0 real stop)
        self.md_request_counter: int = 0
        self.run_so_file_path: PurePath = run_symbol_overview_file_path
        self.stop_so_file_paths: PurePath = stop_so_file_paths
        self.md_so_trigger_time: DateTime | None = None
        self.md_so_stop_time: DateTime | None = None

    def trigger_so_streaming(self) -> DateTime:
        if self.md_request_counter < 0:
            raise Exception(f"Unexpected: {self.md_request_counter} found < 0")
        if self.md_request_counter == 0:
            self.run_shell_script(self.run_so_file_path)
            self.md_so_trigger_time = DateTime.utcnow()
        # else streaming for symbol triggered by prior request, common increment / return trigger time is sufficient
        self.md_request_counter += 1
        return self.md_so_trigger_time

    def stop_so_streaming(self, force: bool = False) -> Tuple[DateTime, subprocess.Popen]:
        if self.md_request_counter > 0:
            self.md_request_counter -= 1
        process = None
        if force or self.md_request_counter == 0:
            # either force or last nonce depleted - call stop API, record stop time, reset md_request_counter
            process = self.run_shell_script(self.stop_so_file_paths)
            self.md_so_stop_time = DateTime.utcnow()
            self.md_request_counter = 0
        else:
            if self.md_request_counter < 0:
                raise Exception(f"Unexpected: {self.md_request_counter=} found < 0 in stop_so_streaming")
            # else not required, normal case

        return self.md_so_stop_time, process  # return actual [prior-recorded or now-updated] stop time

    @staticmethod
    def run_shell_script(script_file_path: PurePath):
        """
        returns immediately after child process is created - does not wait for completion
        TODO Move this to utility script
        """
        if not os.path.exists(script_file_path):
            file_name = os.path.basename(script_file_path)
            logging.error(f"{file_name} failed, not found on path provided - see details;;;{script_file_path=}")
            return
        # so file exists, run symbol overview file
        return subprocess.Popen([f"{script_file_path}"])  # returns immediately after child process is created


class MDStreamingManager:
    def __init__(self, CURRENT_PROJECT_DIR: PurePath, host: str, port: int,
                 db_name: str):
        self.static_data: SecurityRecordManager | None = None
        self.symbol_to_symbol_streaming_data: Dict[str, SymbolStreamingData] = {}
        self.CURRENT_PROJECT_DIR: PurePath = CURRENT_PROJECT_DIR
        self.host = host
        self.port = port
        self.db_name: Final[str] = db_name

    def restart_md_for_symbols(self, system_symbol_n_sec_id_source_list: List[Tuple[str, Any]]) -> None:
        self.force_stop_md_for_symbols(system_symbol_n_sec_id_source_list)
        self.trigger_md_for_symbols(system_symbol_n_sec_id_source_list)

    def trigger_md_for_symbols(self, system_symbol_n_sec_id_source_list: List[Tuple[str, Any]]) -> None:
        for system_symbol, sec_id_source in system_symbol_n_sec_id_source_list:
            symbol_streaming_data: SymbolStreamingData
            if symbol_streaming_data := self.symbol_to_symbol_streaming_data.get(system_symbol):
                pass
            else:
                symbol_streaming_data = self._create_symbol_streaming_data(system_symbol, sec_id_source,
                                                                           continue_mode=True)
                self.symbol_to_symbol_streaming_data[system_symbol] = symbol_streaming_data
            trigger_req_time = DateTime.utcnow()
            trigger_time = symbol_streaming_data.trigger_so_streaming()
            logging.info(f"trigger_md_for_symbols: {trigger_req_time}, {trigger_time}")

    @staticmethod
    def _wait_if_running(processes: List[subprocess.Popen]):
        time.sleep(2)  # initial 2 sec sleep, waiting for process to terminate
        for proc in processes:
            if proc.poll() is None:
                proc.wait()
            # else - process already terminated

    def force_stop_md_for_symbols(self, system_symbol_n_sec_id_source_list: List[Tuple[str, Any]]) -> None:
        """
        currently used to stop MD on recovery start for all chores found
        """
        if 1 > len(system_symbol_n_sec_id_source_list):
            raise Exception(f"Unsupported: {len(system_symbol_n_sec_id_source_list)=} expected >0;;;"
                            f"{system_symbol_n_sec_id_source_list=}")
        processes: List[subprocess.Popen] = []
        symbol: str
        for system_symbol, sec_id_source in system_symbol_n_sec_id_source_list:
            symbol_streaming_data: SymbolStreamingData
            if symbol_streaming_data := self.symbol_to_symbol_streaming_data.get(system_symbol):
                pass
            else:
                # create and run so shell script
                symbol_streaming_data = self._create_symbol_streaming_data(system_symbol, sec_id_source,
                                                                           continue_mode=True)
                self.symbol_to_symbol_streaming_data[system_symbol] = symbol_streaming_data
            # now that we have symbol_streaming_data, let's stop_so_streaming
            trigger_req_time = DateTime.utcnow()
            trigger_time, proc = symbol_streaming_data.stop_so_streaming(force=True)
            processes.append(proc)
            logging.info(f"stop_md_for_symbols: {trigger_req_time=}, {trigger_time=}")
        self._wait_if_running(processes)
        logging.info(f"force_stop_md_for_symbols done for {len(system_symbol_n_sec_id_source_list)=} symbols;;;"
                     f"{system_symbol_n_sec_id_source_list=}")

    def stop_md_for_symbols(self, symbols: List[str]):
        # called for all fully closed chores where no other chore exist on same symbol
        processes: List[subprocess.Popen] = []
        symbol: str
        for system_symbol in symbols:
            symbol_streaming_data: SymbolStreamingData
            if symbol_streaming_data := self.symbol_to_symbol_streaming_data.get(system_symbol):
                trigger_req_time = DateTime.utcnow()
                trigger_time, proc = symbol_streaming_data.stop_so_streaming()
                processes.append(proc)
                logging.info(f"stop_md_for_symbols: {trigger_req_time=}, {trigger_time=}")
            else:
                logging.error(f"symbol_streaming_data not found for {system_symbol=} in symbol_to_symbol_streaming_data"
                              f" in run_stop_md_by_symbol call;;;{symbols=}")
        self._wait_if_running(processes)
        logging.info(f"run stop_md_by_symbol done for {len(symbols)=} {symbols};;;{symbols=}")

    @staticmethod
    def _get_subscription_data(sec_id: str, sec_id_source: str):
        # currently only accepts CB ticker
        leg1_ticker: str = sec_id
        # leg2_ticker = self.static_data.get_underlying_eq_ticker_from_cb_ticker(leg1_ticker)

        subscription_data: List[Tuple[str, str]] = [
            (leg1_ticker, str(sec_id_source)),
            # (leg2_ticker, str(sec_id_source))
        ]
        return subscription_data

    def _create_symbol_streaming_data(self, sec_id: str, sec_id_source: str,
                                      continue_mode: bool = False) -> SymbolStreamingData:
        if self.static_data is None:
            raise Exception(f"Unexpected: trigger_md_for_symbols is invoked while self.static_data is None, this call"
                            f" assumes static data is ready")

        # create and run so shell script
        exch_id: str | None
        ticker: str | None
        exch_id, ticker = self.static_data.get_exchange_n_ticker_from_sec_id_n_source(sec_id, sec_id_source)
        is_eqt: bool = self.static_data.is_eqt_ticker(ticker)
        # creating symbol_overview sh file
        run_symbol_overview_file_path = self.CURRENT_PROJECT_DIR / "scripts" / f"new_ord_{ticker}_so.sh"
        stop_symbol_overview_file_path = self.CURRENT_PROJECT_DIR / "scripts" / f"stop_new_ord_{ticker}_so.sh"
        symbol_streaming_data: SymbolStreamingData = SymbolStreamingData(run_symbol_overview_file_path,
                                                                         stop_symbol_overview_file_path)

        subscription_data = self.get_subscription_data(sec_id, sec_id_source)
        exch_code = "SS" if exch_id == "SSE" else "SZ"
        md_shell_env_data: MDShellEnvData = (
            MDShellEnvData(subscription_data=subscription_data, host=self.host, port=self.port, db_name=self.db_name,
                           exch_code=exch_code, project_name="basket_book"))
        mode="SO_CONTINUE" if continue_mode else "SO"
        create_md_shell_script(md_shell_env_data, str(run_symbol_overview_file_path), mode,
                               instance_id=ticker, is_eqt=is_eqt)
        os.chmod(run_symbol_overview_file_path, stat.S_IRWXU)
        create_stop_md_script(running_process_name=str(run_symbol_overview_file_path),
                              generation_stop_file_path=str(stop_symbol_overview_file_path))
        os.chmod(stop_symbol_overview_file_path, stat.S_IRWXU)
        return symbol_streaming_data
