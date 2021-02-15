from pydantic import BaseModel


class ObjectValue(BaseModel):

    class Config:
        allow_mutation = False
