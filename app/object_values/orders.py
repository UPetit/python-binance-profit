from enum import Enum
from pydantic import condecimal, root_validator, validator
from decimal import Decimal

from .base import ObjectValue
from .symbol import Symbol
from ..tools import is_valid_significant_digits


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

    @validator('total')
    def validate_total(cls, total: Decimal):
        """
            `total` checked against the MARKET_LOT_SIZE_FILTER.
        """
        filter = cls.symbol.filters.market_lot_size_filter
        if not filter.min_qty <= total <= filter.max_qty:
            return False

        if filter.step_size and not is_valid_significant_digits(
            total,
            cls.symbol.qty_decimal_precision
        ):
            return False

        return True


class LimitOrder(Order):
    price: condecimal(gt=0)
    quantity: condecimal(gt=0)

    @root_validator
    def attribute_validation(cls, values: dict) -> dict:
        validated_values = cls._validate_price(cls, values)
        validated_values = cls._validate_qty(cls, values)
        return validated_values

    def _validate_price(cls, values: dict):
        if not (price := values.get('price')):
            raise ValueError("price attribute is required")

        if not (symbol := values.get('symbol')):
            raise ValueError("symbol attribute is required")

        price_filter = symbol.filters.price_filter
        percent_price_filter = symbol.filters.percent_price_filter

        if not price_filter.min_price <= price <= price_filter.max_price:
            raise ValueError("The price is not in valid range")

        if price_filter.tick_size and not is_valid_significant_digits(
            price,
            symbol.price_decimal_precision
        ):
            raise ValueError("The price precision is not valid")

        price_upper_limit = symbol.average_price * percent_price_filter.mul_up
        price_lower_limit = symbol.average_price * percent_price_filter.mul_down

        if not price_lower_limit <= price <= price_upper_limit:
            raise ValueError("The price is not valid compared to current avg trades")

        return values

    def _validate_qty(cls, values: dict):
        """
            `quantity` checked against the LOT_SIZE_FILTER.
        """

        if not (quantity := values.get('quantity')):
            raise ValueError("quantity attribute is required")

        if not (symbol := values.get('symbol')):
            raise ValueError("symbol attribute is required")

        filter = symbol.filters.lot_size_filter
        if not filter.min_qty <= quantity <= filter.max_qty:
            ValueError("The quantity is not in valid range")

        if filter.step_size and not is_valid_significant_digits(
            quantity,
            symbol.qty_decimal_precision
        ):
            raise ValueError("The quantity precision is not valid")

        print(values)
        return values


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
    cummulative_quote_quantity: condecimal(ge=0)
    executed_quantity: condecimal(ge=0)
