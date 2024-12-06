# Testing Perf of dictionary value access in diff ways

# standard imports
import timeit
import os

# 3rd party imports
from fastapi.encoders import jsonable_encoder

# project imports
os.environ["DBType"] = "beanie"

from Flux.CodeGenProjects.TradeEngine.ProjectGroup.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import *

obj = OrderLimitsBaseModel(id=1)
t1 = timeit.default_timer()
print(obj.id)
t2 = timeit.default_timer()
print(t2 - t1)

print("-"*50)

obj_json = jsonable_encoder(obj, by_alias=True)
t1 = timeit.default_timer()
print(obj_json.get("_id"))
t2 = timeit.default_timer()
print(t2-t1)

print("-"*50)

t1 = timeit.default_timer()
if "_id" in obj_json:
    print(obj_json["_id"])
t2 = timeit.default_timer()
print(t2-t1)

print("-"*50)
