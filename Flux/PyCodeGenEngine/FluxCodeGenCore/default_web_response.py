from pydantic import BaseModel


class DefaultWebResponse(BaseModel):
    msg: str
    id: str | int | None = None

    def format_msg(self, pydantic_obj_name: str, id: int | str) -> str:
        self.id = id
        return f"{self.msg}: {pydantic_obj_name} {id}"
