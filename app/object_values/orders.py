from decimal import Decimal
from enum import Enum
from pydantic import condecimal, root_validator

from .base import ObjectValue
from .symbol import Symbol


class Order(ObjectValue):

    class SideEnum(str, Enum):
        buy = 'BUY'
        sell = 'SELL'

    symbol: Symbol
    side: SideEnum


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


class OCOOrder(StopLimitOrder):
    stop_limit_price: condecimal(gt=0)


class OrderInfo(ObjectValue):
    class StatusEnum(str, Enum):
        new = 'NEW'
        partially_filled = 'PARTIALLY_FILLED'
        filled = 'FILLED'
        canceled = 'CANCELED'
        pending_cancel = 'PENDING_CANCEL'
        rejected = 'REJECTED'
        expired = 'EXPIRED'

    status: StatusEnum
    price: condecimal(gt=0)
    cummulative_quote_quantity: Decimal
    executed_quantity: Decimal
