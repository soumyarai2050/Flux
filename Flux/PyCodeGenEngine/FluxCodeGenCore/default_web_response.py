# standard imports

# 3rd party imports

# project imports
from FluxPythonUtils.scripts.model_base_utils import *


class DefaultPydanticWebResponse(PydanticBaseModel):
    msg: str
    id: Any = None

    def format_msg(self, pydantic_obj_name: str, id: Any) -> str:
        self.id = id
        return f"{self.msg}: {pydantic_obj_name} {id}"


class DefaultDataclassWebResponse(DataclassBaseModel):
    msg: str
    id: Any = None

    def format_msg(self, pydantic_obj_name: str, id: Any) -> str:
        self.id = id
        return f"{self.msg}: {pydantic_obj_name} {id}"


class DefaultMsgspecWebResponse(MsgspecBaseModel):
    msg: str
    id: Any = None

    def format_msg(self, model_obj_name: str, id: Any) -> str:
        self.id = id
        return f"{self.msg}: {model_obj_name} {id}"
