from pydantic import BaseModel
from typing import Optional
from .object_values.orders import Order, OrderInfo


class Entity(BaseModel):
    class Config:
        allow_mutation = True
        validate_assignment = True


class OrderInProgress(Entity):
    id: Optional[int]
    order: Order
    info: Optional[OrderInfo]
