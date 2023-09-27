import sys

from Flux.CodeGenProjects.addressbook.app.aggregate import get_ongoing_pair_strat_filter
from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_http_client import \
    StratManagerServiceHttpClient
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, get_native_host_n_port_from_config_dict, get_symbol_side_key

server_port = os.environ.get("PORT")
if server_port is None or len(server_port) == 0:
    err_str = f"Env var 'Port' received as {server_port}"
    logging.exception(err_str)
    raise Exception(err_str)

CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"addressbook_{server_port}_config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

native_host, native_port = get_native_host_n_port_from_config_dict(config_yaml_dict)
strat_manager_service_native_http_client = \
    StratManagerServiceHttpClient.set_or_get_if_instance_exists(native_host, native_port)

update_portfolio_status_lock: asyncio.Lock = asyncio.Lock()


def except_n_log_alert(severity: Severity = Severity.Severity_ERROR):
    def decorator_function(original_function):
        def wrapper_function(*args, **kwargs):
            result = None
            try:
                result = original_function(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                alert_brief: str = f"exception: {e} while attempting {original_function.__name__}, " \
                                   f"date-time: {DateTime.now()}"
                alert_details: str = f"{exc_type}: file: {filename}, line: {exc_tb.tb_lineno}, args: {args}, " \
                                     f"kwargs: {kwargs}"
                logging.error(f"{alert_brief};;; {alert_details}")
            return result

        return wrapper_function

    return decorator_function

#
# def update_portfolio_status(overall_buy_notional: float | None, overall_sell_notional: float | None,
#                             portfolio_alerts: List[Alert] | None = None):
#     """
#     this function is generally invoked in extreme cases - best to not throw any further exceptions from here
#     otherwise the program will terminate - log critical error and continue
#     """
#     try:
#         kwargs = {}
#         act = False
#         if overall_buy_notional is not None:
#             kwargs.update(overall_buy_notional=overall_buy_notional)
#             act = True
#         if overall_sell_notional is not None:
#             kwargs.update(overall_sell_notional=overall_sell_notional)
#             act = True
#         if portfolio_alerts is not None:
#             act = True
#         if act:
#             with update_portfolio_status_lock:
#                 portfolio_status_list: List[
#                     PortfolioStatusBaseModel] = strat_manager_service_web_client_internal.get_all_portfolio_status_client()
#                 logging.debug(f"portfolio_status_list count: {len(portfolio_status_list)}")
#                 if 0 == len(portfolio_status_list):  # no portfolio status set yet - create one
#                     kwargs.update(kill_switch=False)
#                     kwargs.update(portfolio_alerts=portfolio_alerts)
#                     portfolio_status: PortfolioStatusBaseModel = PortfolioStatusBaseModel(**kwargs)
#                     portfolio_status: PortfolioStatusBaseModel = \
#                         strat_manager_service_web_client_internal.create_portfolio_status_client(portfolio_status)
#                     logging.debug(f"created: portfolio_status: {portfolio_status}")
#                 elif 1 == len(portfolio_status_list):
#                     # TODO: we may need to copy non-updated fields form original model
#                     # (we should just update original model with new data (patch) and send)
#                     kwargs.update(kill_switch=portfolio_status_list[0].kill_switch)
#                     kwargs.update(_id=portfolio_status_list[0].id)
#                     if 'overall_buy_notional' not in kwargs:
#                         kwargs.update(overall_buy_notional=portfolio_status_list[0].overall_buy_notional)
#                     if 'overall_sell_notional' not in kwargs:
#                         kwargs.update(overall_sell_notional=portfolio_status_list[0].overall_sell_notional)
#                     if portfolio_status_list[0].portfolio_alerts is not None \
#                             and len(portfolio_status_list[0].portfolio_alerts) > 0:
#                         # TODO LAZY : maybe deep copy instead
#                         if portfolio_alerts is not None:
#                             portfolio_alerts += portfolio_status_list[0].portfolio_alerts
#                         else:
#                             portfolio_alerts = portfolio_status_list[0].portfolio_alerts
#                     kwargs.update(portfolio_alerts=portfolio_alerts)
#                     portfolio_status: PortfolioStatusBaseModel = PortfolioStatusBaseModel(**kwargs)
#                     strat_manager_service_web_client_internal.put_portfolio_status_client(portfolio_status)
#                 else:
#                     logging.critical(
#                         "multiple portfolio limits entries not supported at this time! "
#                         "use swagger UI to delete redundant entries from DB and retry - "
#                         f"this blocks all alert form reaching UI!! alert being processed: {portfolio_alerts}")
#         # else not action required - no action to take - ignore and continue
#     except Exception as e:
#         logging.critical(
#             f"something serious is wrong: update_portfolio_status is throwing an exception!;;; exception: {e}",
#             exc_info=True)


def is_service_up(ignore_error: bool = False):
    try:
        portfolio_status_list: List[
            PortfolioStatusBaseModel] = strat_manager_service_native_http_client.get_all_portfolio_status_client()
        if 0 == len(portfolio_status_list):  # no portfolio status set yet, create one
            portfolio_status: PortfolioStatusBaseModel = \
                PortfolioStatusBaseModel(_id=1, kill_switch=False,
                                         portfolio_alerts=[],
                                         overall_buy_notional=0,
                                         overall_sell_notional=0,
                                         overall_buy_fill_notional=0,
                                         overall_sell_fill_notional=0,
                                         alert_update_seq_num=0)
            strat_manager_service_native_http_client.create_portfolio_status_client(portfolio_status)
        return True
    except Exception as e:
        if not ignore_error:
            logging.exception("service_up test failed - tried get_all_portfolio_status_client (and maybe create);;;"
                          f"exception: {e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


def get_new_portfolio_limits(eligible_brokers: List[Broker] | None = None) -> PortfolioLimitsBaseModel:
    if eligible_brokers is None:
        eligible_brokers = []
    # else using provided value

    rolling_max_order_count = RollingMaxOrderCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxOrderCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)

    portfolio_limits_obj = PortfolioLimitsBaseModel(_id=1, max_open_baskets=20, max_open_notional_per_side=100_000,
                                                    max_gross_n_open_notional=2_400_000,
                                                    rolling_max_order_count=rolling_max_order_count,
                                                    rolling_max_reject_count=rolling_max_reject_count,
                                                    eligible_brokers=eligible_brokers)
    return portfolio_limits_obj


@except_n_log_alert(severity=Severity.Severity_ERROR)
def create_portfolio_limits(eligible_brokers: List[Broker] | None = None) -> PortfolioLimitsBaseModel:
    portfolio_limits_obj = get_new_portfolio_limits(eligible_brokers)
    portfolio_limits: PortfolioLimitsBaseModel = \
        strat_manager_service_native_http_client.create_portfolio_limits_client(portfolio_limits_obj)
    logging.info(f"created portfolio_limits;;; {portfolio_limits_obj}")
    return portfolio_limits


@except_n_log_alert(severity=Severity.Severity_ERROR)
def get_portfolio_limits() -> PortfolioLimitsBaseModel | None:
    portfolio_limits_list: List[
        PortfolioLimitsBaseModel] = strat_manager_service_native_http_client.get_all_portfolio_limits_client()
    if portfolio_limits_list is None or len(portfolio_limits_list) <= 0:
        return None
    elif len(portfolio_limits_list) > 1:
        # portfolio limits: PortfolioLimits = portfolio_limits_list[0]
        # for portfolio limits entry in portfolio limits list:
        #   if portfolio limits entry.id < portfolio_limits.id:
        #          portfolio_limits = portfolio_limits_entry
        # logging.debug(f"portfolio_limit_list: {portfolio_limits_list}, selected portfolio_limits: {portfolio_limits}")
        # return portfolio limits
        err_str_ = f"multiple: ({len(portfolio_limits_list)}) portfolio_limits entries not supported at this time!" \
                   f" use swagger UI to delete redundant entries: {portfolio_limits_list} from DB and retry"
        raise Exception(err_str_)
    else:
        return portfolio_limits_list[0]


def get_new_order_limits():
    ord_limit_obj = OrderLimitsBaseModel(_id=1, max_basis_points=1500, max_px_deviation=20, max_px_levels=5,
                                         max_order_qty=500, min_order_notional=100, max_order_notional=90_000)
    return ord_limit_obj


def get_order_limits() -> OrderLimitsBaseModel | None:
    order_limits_list: List[
        OrderLimitsBaseModel] = strat_manager_service_native_http_client.get_all_order_limits_client()
    if order_limits_list is None or len(order_limits_list) <= 0:
        return None
    elif len(order_limits_list) > 1:
        # order_limits: OrderLimits = order_limits_list[0]
        # for order_limits_entry in order_limits_list:
        #   if order_limits_entry.id < order_limits.id:
        #          order_limits = order_limits_entry
        # logging.debug(f"order_limits_list: {order_limits_list}, selected order_limits: {order_limits}")
        # return order_limits
        raise Exception(f"multiple: ({len(order_limits_list)}) order limits entries not supported at this time!"
                        f" use swagger UI to delete redundant entries: {order_limits_list} from DB and retry")
    else:
        return order_limits_list[0]


def create_order_limits():
    ord_limit_obj = get_new_order_limits()
    strat_manager_service_native_http_client.create_order_limits_client(ord_limit_obj)


def get_match_level(pair_strat: PairStrat, sec_id: str, side: Side) -> int:
    match_level: int = 6
    if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == sec_id:
        if pair_strat.pair_strat_params.strat_leg1.side == side:
            match_level = 1
        else:
            match_level = 2
    elif pair_strat.pair_strat_params.strat_leg2.sec.sec_id == sec_id:
        if pair_strat.pair_strat_params.strat_leg2.side == side:
            match_level = 1
        else:
            match_level = 2
    return match_level  # no match


# caller must take any locks as required for any read-write consistency - function operates without lock
async def get_ongoing_strats_from_symbol_n_side(sec_id: str, side: Side) -> Tuple[List[PairStrat], List[PairStrat]]:
    from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_http_routes import \
        underlying_read_pair_strat_http
    read_pair_strat_filter = get_ongoing_pair_strat_filter(sec_id)
    pair_strats: List[PairStrat] = await underlying_read_pair_strat_http(read_pair_strat_filter)

    match_level_1_pair_strats: List[PairStrat] = list()
    match_level_2_pair_strats: List[PairStrat] = list()
    for pair_strat in pair_strats:
        match_level: int = get_match_level(pair_strat, sec_id, side)
        if match_level == 1:
            match_level_1_pair_strats.append(pair_strat)
        elif match_level == 2:
            match_level_2_pair_strats.append(pair_strat)
        # else not a match ignore
    return match_level_1_pair_strats, match_level_2_pair_strats


async def get_single_exact_match_ongoing_strat_from_symbol_n_side(sec_id: str, side: Side) -> PairStrat | None:
    match_level_1_pair_strats, match_level_2_pair_strats = await get_ongoing_strats_from_symbol_n_side(sec_id, side)
    if len(match_level_1_pair_strats) == 0 and len(match_level_2_pair_strats) == 0:
        logging.error(f"error: No viable pair_strat for symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
        return
    else:
        pair_strat: PairStrat | None = None
        if len(match_level_1_pair_strats) == 1:
            pair_strat = match_level_1_pair_strats[0]
        else:
            logging.error(f"error: processing {get_symbol_side_key([(sec_id, side)])} pair_strat should be "
                          f"found only one in match_lvl_1, found {match_level_1_pair_strats}")
        if pair_strat is None:
            if len(match_level_2_pair_strats) == 1:
                pair_strat = match_level_2_pair_strats[0]
                logging.error(f"error: pair_strat should be found in level 1 only, symbol_side_key: "
                              f"{get_symbol_side_key([(sec_id, side)])}")
            else:
                logging.error(
                    f"error: multiple ongoing pair strats matching symbol_side_key: "
                    f"{get_symbol_side_key([(sec_id, side)])} found, one "
                    f"match expected, found: {len(match_level_2_pair_strats)}")
        return pair_strat
