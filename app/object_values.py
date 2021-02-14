from decimal import Decimal

from pydantic import BaseModel, condecimal, validator


class ObjectValue(BaseModel):

    class Config:
        allow_mutation = False


class LimitInputArgs(ObjectValue):
    symbol: str
    buy_type: str
    quantity: condecimal(gt=0)
    price: condecimal(gt=0)
    profit: condecimal(gt=0, le=100)
    loss: condecimal(gt=0, le=100)


class MarketInputArgs(ObjectValue):
    symbol: str
    buy_type: str
    total: condecimal(gt=0)
    profit: condecimal(gt=0, le=100)
    loss: condecimal(gt=0, le=100)


class PriceFilter(ObjectValue):
    min_price: Decimal
    max_price: Decimal
    tick_size: Decimal


class PercentPriceFilter(ObjectValue):
    mul_up: Decimal
    mul_down: Decimal
    avg_price_mins: Decimal


class LotSizeFilter(ObjectValue):
    min_qty: Decimal
    max_qty: Decimal
    step_size: Decimal


class MarketLotSizeFilter(ObjectValue):
    min_qty: Decimal
    max_qty: Decimal
    step_size: Decimal