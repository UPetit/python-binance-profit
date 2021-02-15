from pydantic import condecimal, root_validator

from .base import ObjectValue


class Order(ObjectValue):
    symbol: str
    side: str


class MarketOrder(Order):
    # amount: condecimal(gt=0) = None
    total: condecimal(gt=0) = None

    @root_validator
    def enforce_mutally_exclusive_amount_and_total(cls, values):
        if bool(values['amount']) ^ bool(values['total']):
            return values
        raise ValueError


class LimitOrder(Order):
    price: condecimal(gt=0)
    quantity: condecimal(gt=0)


class StopLimitOrder(LimitOrder):
    stop_price: condecimal(gt=0)
    time_in_force: str
