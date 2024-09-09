# standard imports
from typing import List, Type
from dataclasses import dataclass
import logging

# 3rd party imports
import motor.motor_asyncio


class MongoDBInit:
    __slots__ = "mongo_client", "db_name", "db_instance"
    instance_object = None

    def __init__(self, mongo_client_: motor.motor_asyncio.AsyncIOMotorClient, db_name: str):
        self.mongo_client = mongo_client_
        self.db_name = db_name
        self.db_instance = self.mongo_client.get_database(self.db_name)

    @classmethod
    async def init_db(cls, class_type_model_list: List[Type[dataclass]]):
        collection_list = await cls.instance_object.db_instance.list_collection_names()

        for class_type_model in class_type_model_list:
            model_name = class_type_model.__name__
            if model_name not in collection_list:
                class_type_model.collection_obj = await cls.instance_object.db_instance.create_collection(model_name)
            else:
                class_type_model.collection_obj = cls.instance_object.db_instance.get_collection(model_name)

    @classmethod
    async def set_instance(cls, mongo_client_: motor.motor_asyncio.AsyncIOMotorClient, db_name: str,
                           class_type_model_list: List[Type[dataclass]]):
        if cls.instance_object is not None:
            logging.warning("ServerDataBaseInit object already exists, returning existing instance")
            return cls.instance_object
        else:
            cls.instance_object = MongoDBInit(mongo_client_, db_name)

            # creating collections for collection list if doesn't exist
            await cls.init_db(class_type_model_list)
            return cls.instance_object

    @classmethod
    def get_instance(cls):
        if cls.instance_object is not None:
            return cls.instance_object
        logging.warning("ServerDataBaseInit object doesn't already exist")
        return None
