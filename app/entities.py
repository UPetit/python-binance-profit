from pydantic import BaseModel


class PriceFilter(BaseModel):
    min_price: float
    max_price: float
    tick_size: float


class PercentPriceFilter(BaseModel):
    mul_up: float
    mul_down: float
    avg_price_mins: float


class LotSizeFilter(BaseModel):
    min_qty: float
    max_qty: float
    step_size: float


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
    filters: Filters
