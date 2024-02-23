from typing import ClassVar, Dict, List
import logging
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract


class IbApiClient(EClient, EWrapper):
    # we can use reqMktDataType to change the exact data that is streamed to us
    # provide the live, top of book market data
    live_mobile_book: ClassVar[int] = 1
    # In the event we want to request the market data from close, this would be an optimal way to do so
    frozen_data: ClassVar[int] = 2
    # if we do not have any market data subscriptions, we are able to use this request to receive delayed data
    delayed_data: ClassVar[int] = 3
    #  will work as a combination of the two so that you can request market data outside of regular
    #  trading hours even without a subscription
    frozen_delayed_data: ClassVar[int] = 4

    # LOG Levels
    # The default is 2 = ERROR
    # 5 = DETAIL is required for capturing all API messages and troubleshooting API programs
    # Valid values are:
    # 1 = SYSTEM
    # 2 = ERROR
    # 3 = WARNING
    # 4 = INFORMATION
    # 5 = DETAIL
    log_lvl_system: ClassVar[int] = 1
    log_lvl_error: ClassVar[int] = 2
    log_lvl_warning: ClassVar[int] = 3
    log_lvl_information: ClassVar[int] = 4
    log_lvl_detail: ClassVar[int] = 5

    def __init__(self, config_yaml: Dict, required_config_key_list: List[str]):
        EClient.__init__(self, self)
        self.config_yaml: Dict = config_yaml
        # Adding contract key to required_config_key_list
        if "contracts" not in required_config_key_list:
            required_config_key_list.append("contracts")
        self._check_keys_in_yaml_config(required_config_key_list)
        self.contracts: List[Contract] = self._set_contracts()

    def _check_keys_in_yaml_config(self, keys_list: List[str]):
        """
        Checks if provided keys are present in config to prevent error at runtime
        """
        for key in keys_list:
            if key not in self.config_yaml:
                raise Exception(f"{key} key not found in yaml config file")
            # else not required: if key is in config then simply looping for next check

    def _set_contracts(self):
        contract_list = []
        try:
            for contract_yaml in self.config_yaml["contracts"]:
                contract = Contract()
                contract.symbol = contract_yaml["symbol"]
                contract.secType = contract_yaml["secType"]
                contract.exchange = contract_yaml["exchange"]
                contract.currency = contract_yaml["currency"]
                contract_list.append(contract)
        except KeyError as e:
            err_str = f"Could not find one of required keys in contract dict in yaml config: {e}"
            logging.exception(err_str)
            raise Exception(err_str)

        return contract_list
