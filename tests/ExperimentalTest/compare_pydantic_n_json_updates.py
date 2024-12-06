# standard imports
import dataclasses
import json
import timeit
from random import random, randint
import sys

import msgspec.json
# 3rd party imports
import orjson
from fastapi.encoders import jsonable_encoder
# from dacite import from_dict, Config

# Project imports
from tests.ExperimentalTest.sample_data_class import *
from tests.ExperimentalTest.sample_cython_class import PairStratCython, PairStratParamsC, StratLegC, SideC, SecurityC

# Pydantic object
# pair_strat_pydantic_obj = PairStratPydantic()
# pair_strat_pydantic_obj.last_active_date_time = DateTime.utcnow()
# pair_strat_pydantic_obj.pair_strat_params = PairStratParamsOptional()
# pair_strat_params_p = pair_strat_pydantic_obj.pair_strat_params
# pair_strat_params_p.hedge_ratio = 2.3
# pair_strat_params_p.exch_response_max_seconds = 2
# pair_strat_params_p.strat_leg1 = StratLegOptional()
# pair_strat_params_p.strat_leg2 = StratLegOptional()
# pair_strat_params_p.strat_leg1.sec = SecurityOptional()
# pair_strat_params_p.strat_leg2.sec = SecurityOptional()

sec1 = SecurityP(sec_id="sample1")
sec2 = SecurityP(sec_id="sample2")
strat_leg1_p = StratLegP(sec=sec1, side=Side.BUY)
strat_leg2_p = StratLegP(sec=sec2, side=Side.SELL)
pair_strat_params_p = PairStratParamsP(strat_leg1=strat_leg1_p, strat_leg2=strat_leg2_p, hedge_ratio=1.2,
                                         exch_response_max_seconds=1)
pair_strat_pydantic_obj = PairStratPydantic(_id=1, pair_strat_params=pair_strat_params_p,
                                               last_active_date_time=DateTime.utcnow())
pydantic_json_str = pair_strat_pydantic_obj.model_dump_json(by_alias=True)

#
# # Json object
# pair_strat_json_obj = pair_strat_pydantic_obj.model_dump()

# DataClass object - without slot
sec1 = SecurityDC(sec_id="sample1")
sec2 = SecurityDC(sec_id="sample2")
strat_leg1_dc = StratLegDC(sec=sec1, side=Side.BUY)
strat_leg2_dc = StratLegDC(sec=sec2, side=Side.SELL)
pair_strat_params_dc = PairStratParamsDC(strat_leg1=strat_leg1_dc, strat_leg2=strat_leg2_dc, hedge_ratio=1.2,
                                         exch_response_max_seconds=1)
pair_strat_data_class_obj = PairStratDataClass(_id=1, pair_strat_params=pair_strat_params_dc,
                                               last_active_date_time=DateTime.utcnow())


# DataClass object - slot
sec1s = SecurityDCS(sec_id="sample1")
sec2s = SecurityDCS(sec_id="sample2")
strat_leg1_dcs = StratLegDCS(sec=sec1s, side=Side.BUY)
strat_leg2_dcs = StratLegDCS(sec=sec2s, side=Side.SELL)
pair_strat_params_dcs = PairStratParamsDCS(strat_leg1=strat_leg1_dcs, strat_leg2=strat_leg2_dcs, hedge_ratio=1.2,
                                           exch_response_max_seconds=1)
pair_strat_data_class_obj_slots = PairStratDataClassSlots(pair_strat_params=pair_strat_params_dcs,
                                                          last_active_date_time=DateTime.utcnow())


# DataClass object - pydantic obj
sec1 = SecurityPDC(sec_id="sample1")
sec2 = SecurityPDC(sec_id="sample2")
strat_leg1_dc = StratLegPDC(sec=sec1, side=Side.BUY)
strat_leg2_dc = StratLegPDC(sec=sec2, side=Side.SELL)
pair_strat_params_dc = PairStratParamsPDC(strat_leg1=strat_leg1_dc, strat_leg2=strat_leg2_dc, hedge_ratio=1.2,
                                         exch_response_max_seconds=1)
pair_strat_pydantic_data_class_obj = PairStratPydanticDataClass(pair_strat_params=pair_strat_params_dc,
                                                                last_active_date_time=DateTime.utcnow())

# Msgspec object - pydantic obj
sec1 = SecurityMS(sec_id="sample1")
sec2 = SecurityMS(sec_id="sample2")
strat_leg1_ms = StratLegMS(sec=sec1, side=Side.BUY)
strat_leg2_ms = StratLegMS(sec=sec2, side=Side.SELL)
pair_strat_params_ms = PairStratParamsMS(strat_leg1=strat_leg1_ms, strat_leg2=strat_leg2_ms, hedge_ratio=1.2,
                                         exch_response_max_seconds=1)
pair_strat_msgspec_obj = PairStratMS(_id=1, pair_strat_params=pair_strat_params_ms,
                                     last_active_date_time=DateTime.utcnow())


# Cython object
pair_strat_cython_obj = PairStratCython()
pair_strat_cython_obj.last_active_date_time = DateTime.utcnow()
pair_strat_cython_obj.pair_strat_params = PairStratParamsC()
pair_strat_params_c = pair_strat_cython_obj.pair_strat_params
pair_strat_params_c.hedge_ratio = 2.3
pair_strat_params_c.exch_response_max_seconds = 2
pair_strat_params_c.strat_leg1 = StratLegC()
pair_strat_params_c.strat_leg2 = StratLegC()
pair_strat_params_c.strat_leg1.sec = SecurityC()
pair_strat_params_c.strat_leg2.sec = SecurityC()


total_update_count = 1000000
repeat = 5


def benchmark_pydantic(pair_strat_pydantic_obj_: PairStratPydantic):
    # updating fields
    random_float = random()
    random_int = randint(1, 100)
    pair_strat_pydantic_obj_.last_active_date_time = DateTime.utcnow()
    pair_strat_params = pair_strat_pydantic_obj_.pair_strat_params
    pair_strat_params.hedge_ratio = random_float
    pair_strat_params.exch_response_max_seconds = random_int
    strat_leg1 = pair_strat_params.strat_leg1
    strat_leg2 = pair_strat_params.strat_leg2
    strat_leg1.sec.sec_id = str(random_int)
    strat_leg2.sec.sec_id = str(random_int)
    strat_leg1.side = Side.BUY
    strat_leg2.side = Side.SELL

    # serialization to json
    # serialized_obj = pair_strat_pydantic_obj_.to_json()
    # serialized_obj = orjson.dumps(pair_strat_pydantic_obj_, default=str)
    # serialized_obj = dataclasses.asdict(pair_strat_pydantic_obj_)
    serialized_obj = pair_strat_pydantic_obj_.model_dump_json()
    # print(serialized_obj)

    # deserialize back to pydantic obj
    # deserialized_obj = from_dict(PairStratBaseModel, orjson.loads(serialized_obj), config=Config(check_types=False))
    # deserialized_obj = PairStratBaseModel.from_json(serialized_obj)
    deserialized_obj = PairStratPydantic(**orjson.loads(serialized_obj))
    # deserialized_obj = PairStratBaseModel(**serialized_obj)
    # print(deserialized_obj)

# t = timeit.repeat("benchmark_pydantic(pair_strat_pydantic_obj)", globals=globals(),
#                   number=total_update_count, repeat=repeat)
# print(f"Pydantic {total_update_count} updates took {min(t)} seconds")
# print(f"Pydantic Class BasicSize: {PairStratBaseModel.__basicsize__} bytes")
# print(f"Pydantic object size: {sys.getsizeof(pair_strat_params_p)} bytes")
# print("-"*100)


def enc_hook(obj: Any) -> Any:
    if isinstance(obj, DateTime):
        return str(obj)


def dec_hook(type: Type, obj: Any) -> Any:
    if type == DateTime and isinstance(obj, str):
        return pendulum.parse(obj)


# def benchmark_pydantic(pair_strat_pydantic_json_str: str):
#     # a = orjson.loads(pair_strat_pydantic_json_str)
#
#     # obj = msgspec.json.decode(pair_strat_pydantic_json_str, type=PairStratMS, dec_hook=dec_hook)
#     # dict = orjson.loads(msgspec.json.encode(obj, enc_hook=enc_hook))
#
#     # json_dict = orjson.loads(pair_strat_pydantic_json_str)
#     # obj = PairStratPydantic(**json_dict)
#     # dict = obj.model_dump()
#
#     json_dict = orjson.loads(pair_strat_pydantic_json_str)
#     obj = PairStratDataClass(**json_dict)
#     dict = orjson.loads(orjson.dumps(obj, default=str))

# benchmark_pydantic(pydantic_json_str)

# t = timeit.repeat("benchmark_pydantic(pydantic_json_str)", globals=globals(),
#                   number=total_update_count, repeat=repeat)
# print(f"Pydantic {total_update_count} updates took {min(t)} seconds")
# print(f"Pydantic Class BasicSize: {PairStratBaseModel.__basicsize__} bytes")
# print(f"Pydantic object size: {sys.getsizeof(pair_strat_params_p)} bytes")
# print("-"*100)



def benchmark_msgspec(pair_strat_msgspec_obj_: PairStratMS):
    # updating fields
    random_float = random()
    random_int = randint(1, 100)
    pair_strat_msgspec_obj_.last_active_date_time = DateTime.utcnow()
    pair_strat_params = pair_strat_msgspec_obj_.pair_strat_params
    pair_strat_params.hedge_ratio = random_float
    pair_strat_params.exch_response_max_seconds = random_int
    strat_leg1 = pair_strat_params.strat_leg1
    strat_leg2 = pair_strat_params.strat_leg2
    strat_leg1.sec.sec_id = str(random_int)
    strat_leg2.sec.sec_id = str(random_int)
    strat_leg1.side = Side.BUY
    strat_leg2.side = Side.SELL

    # serialization to json
    # serialized_obj = msgspec.json.encode(pair_strat_msgspec_obj_, enc_hook=enc_hook)
    serialized_obj = msgspec.to_builtins(pair_strat_msgspec_obj_, enc_hook=enc_hook)
    # serialized_obj = msgspec.structs.asdict(pair_strat_msgspec_obj_)
    # print(serialized_obj)

    # deserialize back to pydantic obj
    # deserialized_obj = msgspec.json.decode(serialized_obj, type=PairStratMS, dec_hook=dec_hook)
    deserialized_obj = msgspec.convert(serialized_obj, type=PairStratMS, dec_hook=dec_hook)
    # deserialized_obj = PairStratMS(**orjson.loads(serialized_obj))
    # deserialized_obj = PairStratMS(**serialized_obj)
    # print(deserialized_obj)

# benchmark_msgspec(pair_strat_msgspec_obj)

# t = timeit.repeat("benchmark_msgspec(pair_strat_msgspec_obj)", globals=globals(),
#                   number=total_update_count, repeat=repeat)
# print(f"Msgspec {total_update_count} updates took {min(t)} seconds")
# print(f"Msgspec Class BasicSize: {PairStratBaseModel.__basicsize__} bytes")
# print(f"Msgspec object size: {sys.getsizeof(pair_strat_params_p)} bytes")
# print("-"*100)


def benchmark_json(pair_strat_json_obj_: Dict):
    # updating fields
    random_float = random()
    random_int = randint(1, 100)
    pair_strat_json_obj_["last_active_date_time"] = DateTime.utcnow()
    pair_strat_params = pair_strat_json_obj_["pair_strat_params"]
    pair_strat_params["hedge_ratio"] = random_float
    pair_strat_params["exch_response_max_seconds"] = random_int
    strat_leg1 = pair_strat_params["strat_leg1"]
    strat_leg2 = pair_strat_params["strat_leg2"]
    strat_leg1["sec"]["sec_id"] = str(random_int)
    strat_leg2["sec"]["sec_id"] = str(random_int)
    strat_leg1["side"] = Side.BUY
    strat_leg2["side"] = Side.SELL

    # serialization to json str
    serialized_obj = orjson.dumps(pair_strat_json_obj_, default=str)
    # print(serialized_obj)

    # deserialize to json obj
    deserialized_obj = orjson.loads(serialized_obj)

# benchmark_json(pair_strat_json_obj)
# t = timeit.repeat("benchmark_json(pair_strat_json_obj)", globals=globals(),
#                   number=total_update_count, repeat=repeat)
# print(f"JSON {total_update_count} updates took {min(t)} seconds")
# print(f"JSON object size: {sys.getsizeof(pair_strat_json_obj)} bytes")
# print("-"*100)

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


def benchmark_dataclass_without_slots(pair_strat_data_class_obj_: PairStratDataClass):
    # updating fields
    random_float = random()
    random_int = randint(1, 100)
    pair_strat_data_class_obj_.last_active_date_time = DateTime.utcnow()
    pair_strat_params = pair_strat_data_class_obj_.pair_strat_params
    pair_strat_params.hedge_ratio = random_float
    pair_strat_params.exch_response_max_seconds = random_int
    strat_leg1 = pair_strat_params.strat_leg1
    strat_leg2 = pair_strat_params.strat_leg2
    strat_leg1.sec.sec_id = str(random_int)
    strat_leg2.sec.sec_id = str(random_int)
    strat_leg1.side = Side.BUY
    strat_leg2.side = Side.SELL

    # serialization to json str
    # serialized_obj_ = pair_strat_data_class_obj_.to_json()
    # print(pair_strat_data_class_obj_)
    serialized_obj = orjson.dumps(pair_strat_data_class_obj_.__dict__, default=str)
    # s = orjson.loads(serialized_obj)
    # print(serialized_obj)
    # serialized_obj = dataclasses.asdict(pair_strat_data_class_obj_)
    # print(type(pair_strat_data_class_obj_))
    # serialized_obj = jsonable_encoder(pair_strat_data_class_obj_)

    # print(serialized_obj, type(serialized_obj))
    # print(json.dumps(pair_strat_data_class_obj_, cls=EnhancedJSONEncoder, default=str), type(json.dumps(pair_strat_data_class_obj_, cls=EnhancedJSONEncoder, default=str)))
    # print(serialized_obj_, type(orjson.loads(serialized_obj_)))

    # # deserialize to json obj
    # deserialized_obj = from_dict(PairStratDataClass, orjson.loads(serialized_obj), config=Config(check_types=False))
    # deserialized_obj = PairStratDataClass.from_json(serialized_obj)
    deserialized_obj = PairStratDataClass(**orjson.loads(serialized_obj))
    # deserialized_obj = PairStratDataClass(**serialized_obj)
    # print(repr(deserialized_obj), type(deserialized_obj))

# benchmark_dataclass_without_slots(pair_strat_data_class_obj) # 37.40419095300058 seconds
# t = timeit.repeat("benchmark_dataclass_without_slots(pair_strat_data_class_obj)", globals=globals(),
#                   number=total_update_count, repeat=repeat)
# print(f"DataClass(without slots) {total_update_count} updates took {min(t)} seconds")
# print(f"DataClass(without slots) Class BasicSize: {PairStratDataClass.__basicsize__} bytes")
# print(f"DataClass(without slots) object size: {sys.getsizeof(pair_strat_data_class_obj)} bytes")
# print("-"*100)


def benchmark_dataclass_with_slots(pair_strat_data_class_obj_slots_: PairStratDataClassSlots):
    # updating fields
    random_float = random()
    random_int = randint(1, 100)
    pair_strat_params = pair_strat_data_class_obj_slots_.pair_strat_params

    strat_leg1 = pair_strat_params.strat_leg1
    strat_leg2 = pair_strat_params.strat_leg2
    pair_strat_params.hedge_ratio = random_float
    pair_strat_params.exch_response_max_seconds = random_int
    strat_leg1.sec.sec_id = str(random_int)
    strat_leg2.sec.sec_id = str(random_int)
    strat_leg1.side = Side.BUY
    strat_leg2.side = Side.SELL

    # serialization to json str
    serialized_obj = pair_strat_data_class_obj_slots_.to_json()
    # serialized_obj = orjson.dumps(pair_strat_data_class_obj_slots_, default=str)
    # print(serialized_obj)
    # serialized_obj = jsonable_encoder(pair_strat_data_class_obj_slots_)

    # deserialize to json obj
    deserialized_obj = PairStratDataClassSlots.from_json(serialized_obj)
    # deserialized_obj = PairStratDataClassSlots(**orjson.loads(serialized_obj))
    # deserialized_obj = PairStratDataClassSlots(**serialized_obj)

# benchmark_dataclass_with_slots(pair_strat_data_class_obj_slots)
# t = timeit.repeat("benchmark_dataclass_with_slots(pair_strat_data_class_obj_slots)", globals=globals(),
#                   number=total_update_count, repeat=repeat)
# print(f"DataClass(with slots) {total_update_count} updates took {min(t)} seconds")
# print(f"DataClass(with slots) Class BasicSize: {PairStratDataClassSlots.__basicsize__} bytes")
# print(f"DataClass(with slots) object size: {sys.getsizeof(pair_strat_data_class_obj_slots)} bytes")
# print("-"*100)


def benchmark_pydantic_dataclass(pair_strat_pydantic_data_class_obj_: PairStratPydanticDataClass):
    # updating fields
    random_float = random()
    random_int = randint(1, 100)
    pair_strat_pydantic_data_class_obj_.last_active_date_time = DateTime.utcnow()
    pair_strat_params = pair_strat_pydantic_data_class_obj_.pair_strat_params
    pair_strat_params.hedge_ratio = random_float
    pair_strat_params.exch_response_max_seconds = random_int
    strat_leg1 = pair_strat_params.strat_leg1
    strat_leg2 = pair_strat_params.strat_leg2
    strat_leg1.sec.sec_id = str(random_int)
    strat_leg2.sec.sec_id = str(random_int)
    strat_leg1.side = Side.BUY
    strat_leg2.side = Side.SELL

    # serialization to json str
    serialized_obj = orjson.dumps(pair_strat_pydantic_data_class_obj_, default=str)
    # print(type(pair_strat_pydantic_data_class_obj_))
    # serialized_obj = jsonable_encoder(pair_strat_pydantic_data_class_obj_)

    # print(serialized_obj)

    # deserialize to json obj
    deserialized_obj = PairStratPydanticDataClass(**orjson.loads(serialized_obj))
    # deserialized_obj = PairStratDataClass(**serialized_obj)
    # print(deserialized_obj)


# t = timeit.repeat("benchmark_pydantic_dataclass(pair_strat_pydantic_data_class_obj)", globals=globals(),
#                   number=total_update_count, repeat=repeat)
# print(f"Pydantic DataClass {total_update_count} updates took {min(t)} seconds")
# print(f"Pydantic DataClass Class BasicSize: {PairStratDataClass.__basicsize__} bytes")
# print(f"Pydantic DataClass object size: {sys.getsizeof(pair_strat_pydantic_data_class_obj)} bytes")
# print("-"*100)


def benchmark_cython(pair_strat_cython: PairStratCython):
    random_float = random()
    random_int = randint(1, 100)
    pair_strat_params = pair_strat_cython.pair_strat_params

    strat_leg1 = pair_strat_params.strat_leg1
    strat_leg2 = pair_strat_params.strat_leg2
    pair_strat_params.hedge_ratio = random_float
    pair_strat_params.exch_response_max_seconds = random_int
    strat_leg1.sec.sec_id = 1
    strat_leg2.sec.sec_id = str(random_int)
    strat_leg1.side = 1
    strat_leg2.side = 2

# benchmark_cython(pair_strat_cython_obj)

# t = timeit.repeat("benchmark_cython(pair_strat_cython_obj)", globals=globals(),
#                   number=total_update_count, repeat=repeat)
# print(f"Cython {total_update_count} updates took {min(t)} seconds")
# print(f"Cython Class BasicSize: {PairStratCython.__basicsize__} bytes")
# print(f"Cython object size: {sys.getsizeof(pair_strat_cython_obj)} bytes")
# print("-"*100)


