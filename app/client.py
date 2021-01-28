from typing import Union, List, Dict
from datetime import datetime
import sys
import time

from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException
from binance.enums import TIME_IN_FORCE_GTC, SIDE_SELL

from .entities import (
    Symbol,
    PriceFilter,
    PercentPriceFilter,
    LotSizeFilter,
    MarketLotSizeFilter,
    Filters,
)
from .tools import get_formated_price

MULT_MILLISECONDS_TO_SECONDS = 1000


class Client(BinanceClient):

    def __init__(
        self,
        api_key: str,
        api_secret: str,
    ) -> None:
        """ Initialize the Binance client
        Args:
            api_key (String): api key for binance api client
            api_secret (String): api secret for binance api client
        Return:
            None
        """

        super().__init__(api_key=api_key, api_secret=api_secret)

        server_time_unix_epoch = self.get_server_time()
        server_time_iso8601 = datetime.utcfromtimestamp(
            server_time_unix_epoch["serverTime"]/MULT_MILLISECONDS_TO_SECONDS
        ).strftime('%Y-%m-%d %H:%M:%SZ')

        print(f"Binance API Time: {server_time_iso8601}")

        is_down = bool(self.get_system_status()["status"])
        if is_down:
            sys.exit("Binance API is down")
        print("Binance API is up")

    def get_avg_price(self, symbol) -> Dict:
        """
        Get the API Response for the average price of the given symbol.
        Args:
            symbol (Symbol): Crypto pair
        Return:
            Dict
        """
        return super().get_avg_price(symbol=symbol.symbol)

    def get_symbol(self, symbol_name) -> Symbol:
        """
        Set the information about a symbol
        Args:
            symbol_name (String): name of the symbol to retrieve
        Return:
            Symbol
        """
        symbol_info = self.get_symbol_info(symbol_name)
        if not symbol_info:
            sys.exit(f"No info found for the symbol {symbol_name}")

        filters = self._get_filters(symbol_info["filters"])
        symbol = Symbol(
            symbol=symbol_info['symbol'],
            status=symbol_info['status'],
            baseAsset=symbol_info['baseAsset'],
            quoteAsset=symbol_info['quoteAsset'],
            isSpotTradingAllowed=symbol_info['isSpotTradingAllowed'],
            ocoAllowed=symbol_info['isSpotTradingAllowed'],
            filters=filters
        )
        if (
            symbol.status != "TRADING"
            or not symbol.isSpotTradingAllowed
        ):
            sys.exit("Spot trading is not allowed on this pair")
        print("Trading allowed")

        if not symbol.ocoAllowed:
            sys.exit("OCO order is not allowed on this pair")

        print("OCO orders allowed")
        return symbol

    def _get_filters(
        self,
        symbol_filters: List[dict]
    ) -> Filters:
        """
        Get the filters
        Args:
            symbol_filters (List of dict): list of filters as dicts
            for a given symbol
        Return:
            Filters
        """

        price_filter = PriceFilter(
            min_price=float(symbol_filters[0]["minPrice"]),
            max_price=float(symbol_filters[0]["maxPrice"]),
            tick_size=float(symbol_filters[0]["tickSize"]),
        )

        percent_price_filter = PercentPriceFilter(
            mul_up=float(symbol_filters[1]["multiplierUp"]),
            mul_down=float(symbol_filters[1]["multiplierDown"]),
            avg_price_mins=float(symbol_filters[1]["avgPriceMins"])
        )

        lot_size_filter = LotSizeFilter(
            min_qty=float(symbol_filters[2]["minQty"]),
            max_qty=float(symbol_filters[2]["maxQty"]),
            step_size=float(symbol_filters[2]["stepSize"])
        )

        market_lot_size_filter = MarketLotSizeFilter(
            min_qty=float(symbol_filters[5]["minQty"]),
            max_qty=float(symbol_filters[5]["maxQty"]),
            step_size=float(symbol_filters[5]["stepSize"])
        )

        return Filters(
            price_filter=price_filter,
            percent_price_filter=percent_price_filter,
            lot_size_filter=lot_size_filter,
            market_lot_size_filter=market_lot_size_filter,
        )

    def validate_quote_qty(
        self,
        symbol: Symbol,
        quote_quantity: float,
        qty_round: int
    ) -> bool:
        """ Validate the quote quantity against the Market Lot Size filter:
        https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#filters
        Args:
            symbol (Symbol): Crypto pair
            quote_quantity (Float): Quantity to spend/receive in quote asset
            qty_round (Integer): Precision for quantity
        Return
            Bool
        """
        market_lot_size_filter = symbol.filters.market_lot_size_filter
        if quote_quantity < market_lot_size_filter.min_qty:
            return False

        if quote_quantity > market_lot_size_filter.max_qty:
            return False

        if market_lot_size_filter.step_size:
            if round(quote_quantity, qty_round) != quote_quantity:
                return False

        if not isinstance(quote_quantity, float):
            return False

        print("Quote quantity (market order) is validated")
        print("Quote quantity:", quote_quantity)
        return True

    def validate_qty(
        self,
        symbol: Symbol,
        quantity: float,
        qty_round: int
    ) -> bool:
        """
        Validate the base quantity for against the Lot Size filter:
        https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#filters
        Args:
            symbol (Symbol): Crypto pair
            quantity (Float): Quantity to buy/sell in base asset
            qty_round (Integer): Precision for quantity
        Return
            Bool
        """

        lot_size_filter = symbol.filters.lot_size_filter
        if quantity < lot_size_filter.min_qty:
            return False

        if quantity > lot_size_filter.max_qty:
            return False

        if lot_size_filter.step_size:
            if round(quantity, qty_round) != quantity:
                return False

        if not isinstance(quantity, float):
            return False

        print("Quantity (limit order) is validated")
        print("Quantity:", quantity)
        return True

    def validate_price(
        self,
        symbol: Symbol,
        avg_price_quote: str,
        price: str,
        price_round: int,
    ) -> bool:
        """
        Validate the price for against the Price and Percent filters:
        https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#filters
        Args:
            symbol (Symbol): Crypto pair
            avg_price_quote (String): Avg Price (quote asset)
            price (String): Price to spend/received for a base asset
            price_round (Integer): Precision for price
        Return
            Bool
        """
        # Price filter check
        price_filter = symbol.filters.price_filter
        percent_price_filter = symbol.filters.percent_price_filter

        if float(price) < price_filter.min_price:
            return False

        if float(price) > price_filter.max_price:
            return False

        if price_filter.tick_size:
            if round(float(price), price_round) != float(price):
                return False

        if float(price) > float(avg_price_quote) * percent_price_filter.mul_up:
            return False

        if float(price) < float(avg_price_quote) * percent_price_filter.mul_down:
            return False

        if not isinstance(price, str):
            return False

        print("Price is validated")
        print("Price: ", price)
        return True

    def create_market_buy_order(
        self,
        symbol: Symbol,
        total_quote: float
    ) -> Union[dict, int]:
        """ Place a market buy order
        Args:
            symbol (Symbol): Crypto pair
            total_quote (Float): Quote total price to pay
        Return
            Dict, Integer
        """
        try:
            buy_order = self.order_market_buy(
                symbol=symbol.symbol,
                quoteOrderQty=total_quote,
            )
            buy_order_id = buy_order["orderId"]
            print("The market order has been sent")

        except BinanceAPIException as e:
            print(f"(Code {e.status_code}) {e.message}")
            return {}, 0

        else:
            return buy_order, buy_order_id

    def create_limit_buy_order(
        self,
        symbol: Symbol,
        base_quantity: float,
        quote_unit_price: str,
    ) -> Union[dict, int]:
        """ Place a limit buy order
        Args:
            symbol (Symbol): Crypto pair
            base_quantity (Float): Base asset quantity to buy
            quote_unit_price (String): Quote asset unit price
        Return
            Dict, Integer
        """
        try:
            buy_order = self.order_limit_buy(
                symbol=symbol.symbol,
                quantity=base_quantity,
                price=quote_unit_price,
            )
            buy_order_id = buy_order["orderId"]
            print("-> The limit buy order has been sent")

        except BinanceAPIException as e:
            print(f"(Code {e.status_code}) {e.message}")
            return {}, 0

        else:
            return buy_order, buy_order_id

    def create_sell_oco_order(
        self,
        symbol: Symbol,
        base_quantity: float,
        price_profit: str,
        price_loss: str,
    ) -> dict:
        """
        Place a Sell OCO order
        Args:
            symbol (Symbol): Crypto pair
            base_quantity (Float): Base asset quantity to buy
            price_profit (String): Price to sell
            price_loss (String): Stoploss price to sell
        Return:
            Dict
        """
        try:
            sell_order = self.create_oco_order(
                symbol=symbol.symbol,
                side=SIDE_SELL,
                quantity=base_quantity,
                price=price_profit,
                stopPrice=price_loss,
                stopLimitPrice=price_loss,
                stopLimitTimeInForce=TIME_IN_FORCE_GTC
            )
            print("-> The sell oco order has been sent")

        except BinanceAPIException as e:
            print(f"(Code {e.status_code}) {e.message}")
            return {}

        else:
            return sell_order

    def execute_buy_strategy(
        self,
        symbol: Symbol,
        buy_order_type: str,
        avg_price: dict,
        quantity: float,
        unit_price: str,
        qty_round: int,
        price_round: int,
    ):
        """ Execute the buy strategy
        Args:
            symbol (Symbol): Crypto pair
            buy_order_type (String): Type of the buying order
            avg_price (Dict): Avg price for this symbol
            quantity (Float): Quantity to buy
            unit_price (String): Unit price to spend
            qty_round (Integer): Precision for quantity
            price_round (Integer): Precision for price
        Return:
            Dict, Float, Float
        """
        print("============================")
        print("Step 1 - Buy order execution")

        if buy_order_type == "limit":
            print("Order validation in progress...")
            is_qty_valid = self.validate_qty(
                symbol,
                quantity,
                qty_round
            )
            is_price_valid = self.validate_price(
                symbol,
                avg_price["price"],
                unit_price,
                price_round
            )

            if not is_qty_valid or not is_price_valid:
                sys.exit("The order is not valid.")
            buy_order, buy_order_id = self.create_limit_buy_order(
                symbol,
                quantity,
                unit_price
            )
        else:
            sys.exit("Order type not supported yet.")

        # Check if the order has been created
        if not buy_order_id:
            sys.exit("Buy order has not been created")

        # Wait for few seconds (API may not find the order_id instantly after the executing)
        time.sleep(2)

        ORDER_IS_NOT_FILLED_YET = True
        while ORDER_IS_NOT_FILLED_YET:
            _order = self.get_order(
                symbol=symbol.symbol,
                orderId=buy_order_id
            )
            if _order["status"] == "FILLED":
                buy_order = _order
                print("The buy order has been filled!")
                break
            else:
                print("The order is not filled yet...")
                time.sleep(3)

        buy_price = float(buy_order["price"])
        buy_quantity = float(buy_order["executedQty"])

        return buy_order, buy_quantity, buy_price

    def execute_sell_strategy(
        self,
        symbol: Symbol,
        sell_quantity: float,
        buy_price: float,
        profit: float,
        loss: float,
        price_round: int,
    ) -> Union[Dict, Dict]:
        """ Execute the sell strategy
        Args:
            symbol (Symbol): Crypto pair
            client (binance.client.Client): Binance client
            sell_quantity (Float): Quantity to sell (that has been bought previously)
            buy_price (Float): Total price spent for the previous buy order
            profit (Float): Percentage of the profit
            loss (Float): Percentage of the stoploss
            price_round (Integer): Precision of the price
        Return:
            Dict, Dict
        """
        # Place a sell OCO order
        print("============================")
        print("Step 2 - Sell OCO order execution")

        # Calculate the selling price with profit
        price_profit = buy_price * (1 + profit)
        price_profit_str = get_formated_price(price_profit, price_round)
        print(f"Selling price (profit): {price_profit_str}")
        # Calculate the stoploss price
        price_loss = buy_price * (1 - loss)
        price_loss_str = get_formated_price(price_loss, price_round)
        print(f"Stoploss price: {price_loss_str}")

        sell_order = self.create_sell_oco_order(
            symbol,
            sell_quantity,
            price_profit_str,
            price_loss_str
        )

        sell_orders = sell_order["orderReports"]
        print("sell_orders", sell_orders)
        stop_loss_limit_order = sell_orders[0]
        limit_maker_order = sell_orders[1]

        return stop_loss_limit_order, limit_maker_order
