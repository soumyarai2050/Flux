from pydantic import BaseModel
from typing import Any


class DefaultWebResponse(BaseModel):
    msg: str
    id: Any = None

    def format_msg(self, pydantic_obj_name: str, id: Any) -> str:
        self.id = id
        return f"{self.msg}: {pydantic_obj_name} {id}"
