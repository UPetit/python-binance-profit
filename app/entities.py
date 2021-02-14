from pydantic import BaseModel, Field, validator
from decimal import Decimal

from .object_values import (
    PriceFilter,
    PercentPriceFilter,
    LotSizeFilter,
    MarketLotSizeFilter,
)
from .tools import strict_integer_validator


class Entity(BaseModel):
    class Config:
        allow_mutation = True
        validate_assignment = True


class Filters(Entity):
    price_filter: PriceFilter
    percent_price_filter: PercentPriceFilter
    lot_size_filter: LotSizeFilter
    market_lot_size_filter: MarketLotSizeFilter


class Symbol(Entity):
    symbol: str
    status: str
    baseAsset: str
    quoteAsset: str
    isSpotTradingAllowed: bool
    ocoAllowed: bool
    price_decimal_precision: int = Field(..., ge=0)
    qty_decimal_precision: int = Field(..., ge=0)
    average_price: Decimal
    filters: Filters

    @validator('price_decimal_precision', 'qty_decimal_precision')
    def enforce_strict_integer_validation(cls, v):
        return strict_integer_validator(cls, v)
