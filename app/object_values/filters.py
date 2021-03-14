from decimal import Decimal

from .base import ObjectValue


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


class Filters(ObjectValue):
    price_filter: PriceFilter
    percent_price_filter: PercentPriceFilter
    lot_size_filter: LotSizeFilter
    market_lot_size_filter: MarketLotSizeFilter
