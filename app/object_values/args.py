from pydantic import condecimal

from .base import ObjectValue


class InputArgs(ObjectValue):
    symbol: str
    buy_type: str
    profit: condecimal(gt=0, le=100)
    loss: condecimal(gt=0, le=100)


class LimitInputArgs(InputArgs):
    quantity: condecimal(gt=0)
    price: condecimal(gt=0)


class MarketInputArgs(InputArgs):
    total: condecimal(gt=0)
