from pydantic import BaseModel


class DefaultWebResponse(BaseModel):
    brief: str | None = None
    description: str | None = None
