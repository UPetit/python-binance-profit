from decimal import Decimal

from pydantic import BaseModel, condecimal


class ObjectValue(BaseModel):

    class Config:
        allow_mutation = False


class InputArgs(ObjectValue):
    symbol: str
    quantity: condecimal(gt=0)
    price: condecimal(gt=0)
    profit: condecimal(gt=0, le=100)
    loss: condecimal(gt=0, le=100)


class PriceFilter(ObjectValue):
    min_price: Decimal
    max_price: Decimal
    tick_size: Decimal

    class Config:
        allow_mutation = False


class PercentPriceFilter(ObjectValue):
    mul_up: Decimal
    mul_down: Decimal
    avg_price_mins: Decimal

    class Config:
        allow_mutation = False


class LotSizeFilter(ObjectValue):
    min_qty: Decimal
    max_qty: Decimal
    step_size: Decimal


class MarketLotSizeFilter(ObjectValue):
    pass
