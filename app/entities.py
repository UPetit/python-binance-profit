from pydantic import BaseModel, condecimal, Field, validator, PositiveInt
from decimal import Decimal


class PriceFilter(BaseModel):
    min_price: Decimal
    max_price: Decimal
    tick_size: Decimal


class PercentPriceFilter(BaseModel):
    mul_up: Decimal
    mul_down: Decimal
    avg_price_mins: Decimal


class LotSizeFilter(BaseModel):
    min_qty: Decimal
    max_qty: Decimal
    step_size: Decimal


class MarketLotSizeFilter(LotSizeFilter):
    pass


class Filters(BaseModel):
    price_filter: PriceFilter
    percent_price_filter: PercentPriceFilter
    lot_size_filter: LotSizeFilter
    market_lot_size_filter: MarketLotSizeFilter


class Symbol(BaseModel):
    symbol: str
    status: str
    baseAsset: str
    quoteAsset: str
    isSpotTradingAllowed: bool
    ocoAllowed: bool
    price_decimal_precision: PositiveInt
    qty_decimal_precision: PositiveInt
    average_price: Decimal
    filters: Filters


class InputArgs(BaseModel):
    symbol: str
    quantity: condecimal(gt=0)
    price: condecimal(gt=0)
    profit: condecimal(gt=0, le=100)
    loss: condecimal(gt=0, le=100)


def _strict_int(cls, v):
    if Decimal(v) != int(v):
        raise ValueError
    return v
