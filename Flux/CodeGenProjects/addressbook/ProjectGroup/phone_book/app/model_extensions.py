import logging
import math
from typing import Dict, List, Tuple, Set
from copy import deepcopy

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import (
    Broker, BrokerBaseModel, SecPosition, SecPositionBaseModel, PositionType, Position, PositionBaseModel, Side)  # , PairStrat
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.ORMModel.dept_book_service_model_imports import (
    OptimizerCriteria)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_symbol_side_key)
from Flux.CodeGenProjects.AddressBook.ORMModel.barter_core_msgspec_model import InstrumentType
from FluxPythonUtils.scripts.utility_functions import float_str
from FluxPythonUtils.scripts.model_base_utils import MsgspecBaseModel


# class PairStratUtil:
#     @staticmethod
#     def get_strat_key(pair_strat: PairStrat):
#         if pair_strat.pair_strat_params.strat_leg2.sec.sec_id is not None


class New1LegChore(MsgspecBaseModel, kw_only=True):
    ticker: str
    side: Side
    px: float
    usd_px: float
    qty: int
    lot_size: int
    finishing_chore: bool


class BrokerUtil:
    @staticmethod
    def get_sec_position_dict(dest_broker: Broker | BrokerBaseModel):
        sec_positions_dict: Dict[str, SecPosition | SecPositionBaseModel] = dict()
        for sec_position in dest_broker.sec_positions:
            sec_positions_dict[sec_position.security.sec_id] = sec_position
        return sec_positions_dict

    @staticmethod
    def merge(dest_broker: Broker | BrokerBaseModel, source_broker: Broker | BrokerBaseModel):
        dest_sec_positions_dict: Dict[str, SecPosition | SecPositionBaseModel] = BrokerUtil.get_sec_position_dict(dest_broker)
        for source_sec_position in source_broker.sec_positions:
            dest_sec_position = dest_sec_positions_dict.get(source_sec_position.security.sec_id)
            if dest_sec_position is None:
                # no change
                dest_broker.sec_positions.append(source_sec_position)
            else:  # we have a merge
                SecPositionUtil.merge(dest_sec_position, source_sec_position)

    @staticmethod
    def compress(broker: Broker | BrokerBaseModel):
        compressed_sec_positions = [SecPositionUtil.compress(sec_position) for sec_position in broker.sec_positions]
        # overwrite with compressed sec positions and return
        broker.sec_positions = compressed_sec_positions
        return broker

    @staticmethod
    def remove_sec_position_by_type(broker: Broker | BrokerBaseModel, pos_type: PositionType):
        remove_list: List[SecPosition | SecPositionBaseModel] = list()
        for sec_position in broker.sec_positions:
            if SecPositionUtil.remove_position_by_type(sec_position, pos_type):
                # true return implies - no more positions in this security - delete entry
                remove_list.append(sec_position)
        for sec_position in remove_list:
            broker.sec_positions.remove(sec_position)
        if len(broker.sec_positions) == 0:
            return True  # indicate empty to caller for any cleanup
        else:
            return False

    @staticmethod
    def append_sec_position(broker: Broker | BrokerBaseModel, sec_position: SecPosition | SecPositionBaseModel):
        return broker.sec_positions.append(sec_position)

    @staticmethod
    def retain_broker_disable(broker: Broker | BrokerBaseModel,
                              dest_broker_dict: Dict[str, Broker | BrokerBaseModel]) -> Broker | None:
        dest_broker: Broker | BrokerBaseModel | None = dest_broker_dict.get(broker.broker)
        if dest_broker is None:
            return None
        else:
            dest_broker.bkr_disable = broker.bkr_disable
            return dest_broker

    @staticmethod
    def get_position_types(brokers: List[Broker | BrokerBaseModel]) -> Set[PositionType]:
        position_types: Set[PositionType] = set()
        if brokers:
            for broker in brokers:
                for sec_position in broker.sec_positions:
                    for position in sec_position.positions:
                        position_types.add(position.type)
        return position_types

    @staticmethod
    def get_least_efficient_cost(optimizer_criteria: OptimizerCriteria, brokers: List[Broker | BrokerBaseModel]) -> float | None:
        optimize_pos_cost: float | None = None
        for broker in brokers:
            new_optimize_pos_cost: float | None = SecPositionUtil.get_least_efficient_cost(optimizer_criteria,
                                                                                           broker.sec_positions)
            if new_optimize_pos_cost and (not math.isclose(new_optimize_pos_cost, 0)):
                if optimize_pos_cost:
                    if optimize_pos_cost < new_optimize_pos_cost:
                        optimize_pos_cost = new_optimize_pos_cost
                    # else not required - identified optimize_pos_cost is still most inefficient
                else:
                    # no optimize cost thus far - just assign
                    optimize_pos_cost = new_optimize_pos_cost
            # else not required, no new_optimize_pos_cost to evaluate / update
        return optimize_pos_cost

    @classmethod
    def has_optimization_opportunity(cls, optimizer_criteria: OptimizerCriteria, brokers: List[Broker | BrokerBaseModel]):
        if brokers:
            optimize_pos_cost: float | None = cls.get_least_efficient_cost(optimizer_criteria, brokers)
            # if optimize_pos_cost was found, then check optimization opportunity on that

            ignore_pos_type_set: Set[PositionType] = set()
            ignore_pos_type_set.add(PositionType.SOD)
            if optimizer_criteria.pos_type == PositionType.LOCATE:
                ignore_pos_type_set.add(PositionType.PTH)
            if optimize_pos_cost and (not math.isclose(optimize_pos_cost, 0)):
                for broker in brokers:
                    if SecPositionUtil.has_optimization_opportunity(optimizer_criteria.pos_type, broker.sec_positions,
                                                                    optimize_pos_cost, ignore_pos_type_set):
                        # even if we find one opportunity - it is an opportunity
                        return True
            # no optimization opportunity
            return False

    @staticmethod
    def has_position_type(broker: Broker | BrokerBaseModel, position_type: PositionType):
        for sec_position in broker.sec_positions:
            for position in sec_position.positions:
                if position.type == position_type:
                    return True


class BrokerData(MsgspecBaseModel, kw_only=True):
    # Each Broker can have EQT and CB , CASH and SWAP accounts over QFII and CONNECT
    eqt_connect_account: str
    eqt_connect_route: str
    eqt_qfii_account: str
    eqt_qfii_route: str
    cb_qfii_account: str | None = None  # CB can never be barterd via connect
    cb_qfii_route: str | None = None  # CB can never be barterd via connect


class SecPosExtended(SecPosition):
    broker: str
    bkr_data: BrokerData
    bartering_account: str | None = None
    bartering_route: str | None = None
    no_return: bool = False
    consumed: bool = False

    @classmethod
    def from_kwargs(cls, **kwargs):
        id_val = kwargs.pop("_id", None)
        if id_val is not None:
            kwargs["_id"] = str(id_val)

        sec_pos_extended = super().from_kwargs(**kwargs)
        return sec_pos_extended

    def get_extracted_size(self) -> int:
        position: Position | PositionBaseModel
        extracted_size = 0
        for position in self.positions:
            extracted_size += position.available_size
        return extracted_size

    @staticmethod
    def validate_all(system_symbol: str, side: Side, sec_pos_extended_list: List['SecPosExtended']):
        for sec_pos_extended in sec_pos_extended_list:
            if not sec_pos_extended.validate(system_symbol, side):
                return False  # Failed
        return True

    def validate(self, system_symbol: str, side: Side) -> bool:
        """
        log error and return False if mandatory data not found else return True
        Returns: True if all data present
        """
        bartering_symbol = self.security.sec_id
        account = self.bartering_account
        exchange = self.bartering_route
        if bartering_symbol is None or account is None or exchange is None:
            symbol_side_key = get_symbol_side_key([(system_symbol, side)])
            logging.error(f"unable to send chore, couldn't find metadata for symbol_side_key: {symbol_side_key}, "
                          f"bartering_symbol: {bartering_symbol}, account: {account}, exchange: {exchange}")
            return False
        return True


class LivePosition(MsgspecBaseModel, kw_only=True):
    pending_fill_qty: float


class SecPositionUtil:

    @staticmethod
    def remove_position_by_type(sec_position: SecPosition | SecPositionBaseModel, pos_type: PositionType):
        remove_list: List[Position | PositionBaseModel] = list()
        for position in sec_position.positions:
            if position.type == pos_type:
                remove_list.append(position)
            else:
                continue  # ignore and continue
        for position in remove_list:
            sec_position.positions.remove(position)
        if len(sec_position.positions) == 0:
            return True  # indicate empty to caller for any cleanup
        return False

    @staticmethod
    def append_position(sec_position: SecPosition | SecPositionBaseModel, position: Position | PositionBaseModel):
        return sec_position.positions.append(position)

    @staticmethod
    def merge(dest_sec_position: SecPosition | SecPositionBaseModel,
              source_sec_position: SecPosition | SecPositionBaseModel):
        # this just appends new positions, to update: delete old position and add updated position
        for position in source_sec_position.positions:
            dest_sec_position.positions.append(position)

    @staticmethod
    def get_least_efficient_cost(optimizer_criteria: OptimizerCriteria,
                                 sec_pos_list: List[SecPosition | SecPositionBaseModel]) -> float | None:
        optimize_pos_cost: float | None = None
        for sec_pos in sec_pos_list:
            new_optimize_pos_cost: float | None = PositionUtil.get_least_efficient_cost(optimizer_criteria,
                                                                                        sec_pos.positions)
            if new_optimize_pos_cost and (not math.isclose(new_optimize_pos_cost, 0)):
                if optimize_pos_cost:
                    if optimize_pos_cost < new_optimize_pos_cost:
                        optimize_pos_cost = new_optimize_pos_cost
                    # else not required - identified optimize_pos_cost is still most inefficient
                else:
                    # no optimize cost thus far - just assign
                    optimize_pos_cost = new_optimize_pos_cost
            # else not required, no new_optimize_pos_cost to evaluate / update
        return optimize_pos_cost

    @staticmethod
    def has_optimization_opportunity(optimization_by: PositionType, sec_pos_list: List[SecPosition | SecPositionBaseModel],
                                     optimize_pos_cost: float, ignore_pos_type_set: Set[PositionType]):
        for sec_pos in sec_pos_list:
            if PositionUtil.has_optimization_opportunity(optimization_by, sec_pos.positions,
                                                         optimize_pos_cost, ignore_pos_type_set):
                return True
        return False

    @staticmethod
    def extract_position(qty: int, stored_sec_pos_list: List[SecPosExtended], sec_pos_idx: int, pos_idx: int) \
            -> SecPosExtended | None:
        sec_pos_list_len = len(stored_sec_pos_list)
        if sec_pos_list_len > sec_pos_idx:
            stored_positions = stored_sec_pos_list[sec_pos_idx].positions
            pos_list_len = len(stored_positions)
            if pos_list_len > pos_idx:
                stored_position = stored_positions[pos_idx]
                if (abs(stored_position.available_size) - stored_position.consumed_size) < qty:
                    logging.error(f"extract_position invoked on position with insufficient qty. available_size: "
                                  f"{stored_position.available_size}, consumed_size: {stored_position.consumed_size}, "
                                  f"qty: {qty};;;position: {stored_position}")
                stored_sec_pos_extended: SecPosExtended = stored_sec_pos_list[sec_pos_idx]
                extracted_sec_pos_extended: SecPosExtended = (
                    SecPosExtended(broker=stored_sec_pos_extended.broker, bkr_data=stored_sec_pos_extended.bkr_data,
                                   security=stored_sec_pos_extended.security, positions=[deepcopy(stored_position)]))
                extracted_sec_pos_extended.positions[0].available_size = qty
                extracted_sec_pos_extended.positions[0].consumed_size = 0
                stored_sec_pos_extended.positions[pos_idx].consumed_size += qty
                return extracted_sec_pos_extended
            else:
                logging.error(f"extract_position invoked with pos_list_len: {pos_list_len} not > pos_idx: {pos_idx} "
                              f"for sec_pos_idx: {sec_pos_idx};;;pos_list: {[str(position) for position in stored_positions]}")
                return None
        else:
            logging.error(f"extract_position invoked with sec_pos_list_len: {sec_pos_list_len} not > sec_pos_idx: "
                          f"{sec_pos_idx} and pos_idx: {pos_idx};;;"
                          f"sec_pos_list: {[str(sec_pos) for sec_pos in stored_sec_pos_list]}")
            return None

    @staticmethod
    def return_availability(dest_sec_position: SecPosExtended, source_sec_position: SecPosExtended):
        if source_sec_position.no_return:
            return  # no need to process this return of availability
        # designed for small collection (current use-case), n2 is fine, not worth creating a dict to merge
        for source_position in source_sec_position.positions:
            source_key = PositionUtil.get_pos_compression_key(source_position)
            for dest_position in dest_sec_position.positions:
                dest_key = PositionUtil.get_pos_compression_key(dest_position)
                if source_key == dest_key:
                    dest_position.consumed_size -= source_position.available_size
                    if dest_position.consumed_size < 0:
                        logging.warning(f"return_availability: dest_position.consumed_size is: "
                                        f"{dest_position.consumed_size} upon returning source_position.available_size: "
                                        f"{source_position.available_size} for sec: {dest_sec_position.security.sec_id}"
                                        f"resetting dest_position.consumed_size to 0;;;dest_sec_position: "
                                        f"{dest_sec_position}, source_sec_position: {source_sec_position}")
                        dest_position.consumed_size = 0
                    else:
                        logging.debug(f"returning sec_pos succeeded for {source_key}, "
                                      f"returned {source_position.available_size} updated "
                                      f"dest_position.consumed_size: {dest_position.consumed_size};;;passed "
                                      f"source_position: {source_position}, updated dest position: {dest_position}")
                    source_position.available_size = 0
                    break
                # else retry till we exhaust all dest pos - in which case the "else" of for will create new dest entry
            else:
                # no match for source_position in dest_sec_position.positions, we add new entry
                dest_sec_position.positions.append(source_position)

    @staticmethod
    def override_availability(dest_sec_pos: SecPosExtended, source_sec_pos: SecPosExtended):
        """
        designed for small collection (current use-case), n2 is fine, not worth creating a dict to merge
        called if same broker, sec-id & ticker
        overrides availability and resets source_sec_pos where source_key == dest_key
        """
        compression_key_position_dict: Dict[str, Position | PositionBaseModel] = dict()
        for source_pos in source_sec_pos.positions:
            source_key = PositionUtil.get_pos_compression_key(source_pos)
            compression_key_position_dict[source_key] = source_pos
            for dest_pos in dest_sec_pos.positions:
                dest_key = PositionUtil.get_pos_compression_key(dest_pos)
                if source_key == dest_key:
                    if source_pos.available_size > 0 and \
                            (source_pos.available_size - dest_pos.consumed_size) < 0:
                        logging.error(f"Error: updated available_size: {source_pos.available_size} is < old "
                                      f"consumed size: {dest_pos.consumed_size} for sec: "
                                      f"{dest_sec_pos.security.sec_id}, leaving old available size as-is: "
                                      f"{dest_pos.available_size};;;updated dest_sec_position: "
                                      f"{dest_sec_pos}, source_sec_position: {source_sec_pos}")
                    elif dest_pos.available_size != source_pos.available_size:
                        dest_pos.available_size = source_pos.available_size
                    # else since dest_pos.available_size == source_pos.available_size, just reset source available_size
                    source_pos.available_size = 0
                    break
            else:
                dest_sec_pos.positions.append(source_pos)
        for dest_pos in dest_sec_pos.positions:
            dest_key = PositionUtil.get_pos_compression_key(dest_pos)
            if compression_key_position_dict.get(dest_key) is None:
                dest_sec_pos.positions.remove(dest_pos)
            # else not required: position exists in source sec position

    @staticmethod
    def is_unsupported_broker_by_sec_type(sec_pos: SecPosExtended):
        if sec_pos.security.inst_type == InstrumentType.CB and sec_pos.broker == "UBS":
            return True
        return False

    @staticmethod
    def clear_intraday_consumption(sec_pos_list: List[SecPosExtended]):
        sec_pos: SecPosExtended
        for sec_pos in sec_pos_list:
            PositionUtil.clear_intraday_positions(sec_pos.positions)

    @staticmethod
    def find_best_availability(
            sec_pos_list: List[SecPosExtended], qty: int,
            pos_type_vis_max_available_size_n_abs_overall_available_size: Dict[PositionType, Tuple[int, int]] | None) -> \
            Tuple[int | None, int | None]:
        best_availability_sec_pos_idx: int | None = None
        best_availability_position: Position | PositionBaseModel | None = None
        best_availability_pos_idx: int | None = None
        # lower value is higher priority, at same priority level - picks largest qty
        sec_pos: SecPosExtended
        for sec_pos_idx, sec_pos in enumerate(sec_pos_list):
            pos_idx: int | None
            sec_pos_max_available_size: int | None
            sec_pos_abs_overall_available_size: int | None
            if SecPositionUtil.is_unsupported_broker_by_sec_type(sec_pos):
                continue  # skip unsupported sec_pos
            pos_idx = PositionUtil.find_best_availability(
                sec_pos.positions, qty, pos_type_vis_max_available_size_n_abs_overall_available_size)
            # compute overall availability and overall max available pos (most preferred) to consume
            position_: Position | PositionBaseModel | None = None
            if pos_idx is not None:
                position_: Position | PositionBaseModel | None = sec_pos.positions[pos_idx]
            if best_availability_sec_pos_idx is not None and pos_idx is not None:
                # enable if we see exception from here with position_.priority is None
                # if position_.priority is None:
                #     logging.error(f"Unexpected: {position_.priority=}; {position_=} for {sec_pos.security.sec_id}; "
                #                   f"check why, ignoring position;;;{pos_idx=}; {sec_pos.positions=}")
                tmp_idx = PositionUtil.best_availability(best_availability_position, position_)
                if tmp_idx == 2:
                    best_availability_position = position_
                    best_availability_sec_pos_idx = sec_pos_idx
                    best_availability_pos_idx = pos_idx
                # else not required - new pos is not better than prior identified best_availability_position
            elif pos_idx is not None:
                best_availability_position = position_
                best_availability_sec_pos_idx = sec_pos_idx
                best_availability_pos_idx = pos_idx
            else:
                # no available position for the sec_pos
                continue
        return best_availability_sec_pos_idx, best_availability_pos_idx

    @staticmethod
    def set_fixed_priorities(compressed_sec_position_dict: Dict[str, Position | PositionBaseModel]):
        sod_positions = [position for key, position in compressed_sec_position_dict.items() if
                         key.startswith(f"{PositionType.SOD}")]
        pth_positions = [position for key, position in compressed_sec_position_dict.items() if
                         key.startswith(f"{PositionType.PTH}")]
        locate_positions = [position for key, position in compressed_sec_position_dict.items() if
                            key.startswith(f"{PositionType.LOCATE}")]
        for sod_position in sod_positions:
            sod_position.priority = 0
        for pth_position in pth_positions:
            pth_position.priority = 3
        for locate_position in locate_positions:
            locate_position.priority = 2

    @staticmethod
    def compress(sec_position: SecPosition | SecPositionBaseModel):
        # position.type is key
        compressed_sec_position_dict: Dict[str, Position | PositionBaseModel] = {}
        for position in sec_position.positions:
            key = PositionUtil.get_pos_compression_key(position)
            if (compressed_sec_position := compressed_sec_position_dict.get(key)) is not None:
                compressed_sec_position_dict[key] = PositionUtil.compress(compressed_sec_position, position)
            else:
                compressed_sec_position_dict[key] = position
        # prioritize positions [fixed priority]
        SecPositionUtil.set_fixed_priorities(compressed_sec_position_dict)
        # overwrite position list with compressed position list
        sec_position.positions = [*(compressed_sec_position_dict.values())]
        return sec_position

    @staticmethod
    def retain_position_disable(sec_position: SecPosition | SecPositionBaseModel,
                                dest_sec_position_dict: Dict[str, SecPosition | SecPositionBaseModel]):
        dest_sec_position: SecPosition | None = dest_sec_position_dict.get(sec_position.security.sec_id)
        if dest_sec_position is not None:
            for position in sec_position.positions:
                source_key = PositionUtil.get_pos_compression_key(position, with_pos_disable=False)
                for dest_position in dest_sec_position.positions:
                    dest_key = PositionUtil.get_pos_compression_key(dest_position, with_pos_disable=False)
                    if source_key == dest_key:
                        dest_position.pos_disable = position.pos_disable
                        break
                    # else not required
        # else not required: sec position not found in updated sec position dict


class PositionUtil:
    @staticmethod
    def get_pos_compression_key(position: Position | PositionBaseModel, with_pos_disable: bool = False) -> str:
        pos_disable_str = ""

        if with_pos_disable:
            pos_disable_str = f"_{position.pos_disable}"

        return f"{position.type}_{float_str(position.acquire_cost)}_{position.mstrat}_" \
               f"{float_str(position.carry_cost)}_{float_str(position.incurred_cost)}{pos_disable_str}"

    @staticmethod
    def get_least_efficient_cost(optimizer_criteria: OptimizerCriteria,
                                 pos_list: List[Position | PositionBaseModel]) -> float | None:
        optimize_pos_cost: float | None = None
        for pos in pos_list:
            if pos.type == optimizer_criteria.pos_type:
                new_optimize_pos_cost = pos.acquire_cost
                if new_optimize_pos_cost and (not math.isclose(new_optimize_pos_cost, 0)):
                    if optimize_pos_cost:
                        if optimize_pos_cost < new_optimize_pos_cost:
                            optimize_pos_cost = new_optimize_pos_cost
                        # else not required - identified optimize_pos_cost is still most inefficient
                    else:
                        # no optimize cost thus far - just assign
                        optimize_pos_cost = new_optimize_pos_cost
                # else not required, no new_optimize_pos_cost to evaluate / update
            # else continue - we are not interested in this iteration's pos.type
        return optimize_pos_cost

    @staticmethod
    def has_optimization_opportunity(optimization_by: PositionType, pos_list: List[Position | PositionBaseModel],
                                     optimize_pos_cost: float, ignore_pos_type_set: Set[PositionType]):
        for pos in pos_list:
            if (pos.type == optimization_by) or (pos.type in ignore_pos_type_set):
                continue
            elif pos.acquire_cost and (not math.isclose(pos.acquire_cost, 0)):
                if optimize_pos_cost > pos.acquire_cost:
                    return True
                # else not required, no optimization opportunity
            # else - we are not interested in this iteration pos.acquire_cost not meaningful
        return False

    @staticmethod
    def best_availability(position1: Position | PositionBaseModel, position2: Position | PositionBaseModel) -> int:
        best_availability_position_idx: int
        if position1:
            if position1.priority > position2.priority:
                best_availability_position_idx = 2
            # if priority is same select position/broker with maximum available size factoring in past consumption
            elif position1.priority == position2.priority and \
                    (abs(position1.available_size) - position1.consumed_size) < \
                    (abs(position2.available_size) - position2.consumed_size):
                best_availability_position_idx = 2
            else:  # position1 is better than position2
                best_availability_position_idx = 1
        else:
            best_availability_position_idx = 2
        return best_availability_position_idx

    @staticmethod
    def update_max_n_overall_dict(
            pos_type_vis_max_available_size_n_abs_overall_available_size: Dict[PositionType, Tuple[int, int]],
            abs_pos_available_size, pos_type: PositionType):
        max_n_overall = pos_type_vis_max_available_size_n_abs_overall_available_size.get(pos_type)
        if max_n_overall:
            max_available_size, abs_overall_available_size = max_n_overall
            abs_overall_available_size += abs_pos_available_size
            if max_available_size < abs_pos_available_size:
                max_available_size = abs_pos_available_size
        else:
            # no max yet, thus same as abs_pos_available_size
            max_available_size = abs_pos_available_size
            abs_overall_available_size = abs_pos_available_size
        pos_type_vis_max_available_size_n_abs_overall_available_size[pos_type] = (max_available_size,
                                                                                  abs_overall_available_size)

    @staticmethod
    def has_valid_intraday(intraday_position: Position | PositionBaseModel) -> bool:
        return (intraday_position.bot_size is not None and intraday_position.bot_size != 0) or (
                intraday_position.sld_size is not None and intraday_position.sld_size != 0)

    @staticmethod
    def clear_intraday_positions(positions: List[Position | PositionBaseModel]):
        for position in positions:
            PositionUtil.clear_intraday_position(position)

    @staticmethod
    def clear_intraday_position(position: Position | PositionBaseModel):
        position.consumed_size = 0
        position.bot_size = None
        position.sld_size = None

    @staticmethod
    def find_best_availability(
            positions_: List[Position | PositionBaseModel], qty: int,
            pos_type_vis_max_available_size_n_abs_overall_available_size: Dict[PositionType, Tuple[int, int]] | None):
        best_availability_position: Position | None = None
        best_availability_position_idx: int | None = None
        for idx, position_ in enumerate(positions_):
            if position_.available_size == 0:
                # 0 position size is incompatible with both buy and sell
                continue
            if qty < 0 and position_.available_size < 0:
                # -ive available_size is short position and -ive qty is SELL, incompatible, continue
                continue
            elif qty > 0 and position_.available_size > 0:
                # +ive available_size is long position and +ive qty is BUY, incompatible, continue
                continue
            # match only if the requested qty can be satisfied
            abs_pos_available_size: int = abs(position_.available_size)
            if (abs_pos_remaining_size := (abs_pos_available_size - position_.consumed_size)) < abs(qty):
                if abs_pos_remaining_size > 0 and \
                        pos_type_vis_max_available_size_n_abs_overall_available_size is not None:  # passed non None at start
                    PositionUtil.update_max_n_overall_dict(pos_type_vis_max_available_size_n_abs_overall_available_size,
                                                           abs_pos_remaining_size, position_.type)
                continue
            # this is a match, compare with last best match and find new best match
            if position_.priority is None:
                logging.error(f"Unexpected: {position_.priority=} in acceptable {abs_pos_available_size=} of "
                              f"{position_}, check why, ignoring position;;;{best_availability_position_idx=}; "
                              f"{positions_=}")
                continue
            else:
                temp_best_availability_position_idx = PositionUtil.best_availability(best_availability_position,
                                                                                     position_)
                if temp_best_availability_position_idx == 2:
                    best_availability_position_idx = idx
                    best_availability_position = position_
                # else previously stored best_availability_position_idx is ok to return
        return best_availability_position_idx

    @staticmethod
    def get_compressed_priority(position1: Position | PositionBaseModel, position2: Position | PositionBaseModel) -> int:
        compressed_priority: int = 0
        if position1.priority is not None and position2.priority is not None:
            compressed_priority = position1.priority if (
                    position1.priority > position2.priority) else position2.priority
        elif position1.priority is not None:
            compressed_priority = position1.priority
        elif position2.priority is not None:
            compressed_priority = position2.priority
        else:  # both priorities are none compute priority
            match position1.type:
                case PositionType.SOD:
                    compressed_priority = 0
                case PositionType.PTH:
                    compressed_priority = 3
                case PositionType.LOCATE:
                    compressed_priority = 2
                case PositionType.POS_TYPE_UNSPECIFIED:
                    raise Exception(f"Unexpected!, position type POS_TYPE_UNSPECIFIED found in compression: "
                                    f"for position: {position1} while compressing with position: {position2}")
        return compressed_priority

    @classmethod
    def compress(cls, position1: Position | PositionBaseModel, position2: Position | PositionBaseModel) -> Position:
        compressed_available_size = position1.available_size + position2.available_size
        compressed_allocated_size = position1.allocated_size + position2.allocated_size
        compressed_consumed_size = position1.consumed_size + position2.consumed_size

        def num_sized(size: int):
            return size if size else 0

        compressed_bot_size: int | None
        if position1.bot_size or position2.bot_size:
            compressed_bot_size = num_sized(position1.bot_size) + num_sized(position2.bot_size)
        else:
            compressed_bot_size = None

        compressed_sld_size: int | None
        if position1.sld_size or position2.sld_size:
            compressed_sld_size = num_sized(position1.sld_size) + num_sized(position2.sld_size)
        else:
            compressed_sld_size = None

        compressed_priority = PositionUtil.get_compressed_priority(position1, position2)
        compressed_position: Position = Position(pos_disable=position1.pos_disable,
                                                 type=position1.type,
                                                 acquire_cost=position1.acquire_cost,
                                                 available_size=compressed_available_size,
                                                 allocated_size=compressed_allocated_size,
                                                 consumed_size=compressed_consumed_size,
                                                 bot_size=compressed_bot_size,
                                                 sld_size=compressed_sld_size,
                                                 priority=compressed_priority)
        compressed_position.mstrat = cls.get_merged_mstrat(position1, position2)
        return compressed_position

    @staticmethod
    def get_merged_mstrat(position1: Position | PositionBaseModel, position2: Position | PositionBaseModel) -> str:
        def split_mstrats(string_: str | None):
            return string_.split("--") if string_ else ["None"]

        position1_mstrats = split_mstrats(position1.mstrat)
        position2_mstrats = split_mstrats(position2.mstrat)

        unique_pos2_mstrats = set()
        for position2_mstrat in position2_mstrats:
            if position2_mstrat in position1_mstrats:
                continue
            else:
                try:
                    unique_pos2_mstrats.add(position2_mstrat)
                except KeyError as key_err:
                    logging.error(f"Unexpected: found {position2_mstrat=} already present in {unique_pos2_mstrats=};;;"
                                  f"{key_err=}")
                    continue
        position1_mstrats.extend(list(unique_pos2_mstrats))
        return "--".join(sorted(position1_mstrats, reverse=True))
