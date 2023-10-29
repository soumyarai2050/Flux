from typing import Dict, Tuple, Type
import os

os.environ["DBType"] = "beanie"
# Below unused import is used by generated beanie file
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *


def get_open_order_counts():
    return {"aggregate": [
        {
            "$match": {
                "$or": [
                    {
                        "order_status": "OE_ACKED"
                    },
                    {
                        "order_status": "OE_UNACK"
                    }
                ]
            },
        }]}
