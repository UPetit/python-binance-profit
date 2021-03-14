from pydantic import Field, validator
from decimal import Decimal

from .base import ObjectValue
from .filters import (
    Filters
)
from ..tools import strict_integer_validator


class Symbol(ObjectValue):
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
