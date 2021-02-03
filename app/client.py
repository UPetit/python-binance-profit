from typing import Union, List, Dict
from datetime import datetime
from decimal import Decimal
import sys
import time
from errno import ECONNRESET

import numpy as np

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
            api_key (str): api key for binance api client
            api_secret (str): api secret for binance api client
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

    def get_symbol(self, symbol_name: str) -> Symbol:
        """
        Set the information about a symbol
        Args:
            symbol_name (str): name of the symbol to retrieve
        Return:
            Symbol
        """
        symbol_info = self.get_symbol_info(symbol_name)
        if not symbol_info:
            sys.exit(f"No info found for the symbol {symbol_name}")

        filters = self._get_filters(symbol_info["filters"])

        avg_price = Decimal(
            super().get_avg_price(symbol=symbol_name)['price']
        )
        price_round = int(-np.log10(filters.price_filter.min_price))
        qty_round = int(-np.log10(filters.lot_size_filter.min_qty))

        symbol = Symbol(
            symbol=symbol_info['symbol'],
            status=symbol_info['status'],
            baseAsset=symbol_info['baseAsset'],
            quoteAsset=symbol_info['quoteAsset'],
            isSpotTradingAllowed=symbol_info['isSpotTradingAllowed'],
            ocoAllowed=symbol_info['isSpotTradingAllowed'],
            price_decimal_precision=price_round,
            qty_decimal_precision=qty_round,
            average_price=avg_price,
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
        symbol_filters: List[Dict]
    ) -> Filters:
        """
        Get the filters
        Args:
            symbol_filters (List of Dict): list of filters as dicts
            for a given symbol
        Return:
            Filters
        """

        price_filter = PriceFilter(
            min_price=symbol_filters[0]["minPrice"],
            max_price=symbol_filters[0]["maxPrice"],
            tick_size=symbol_filters[0]["tickSize"],
        )

        percent_price_filter = PercentPriceFilter(
            mul_up=symbol_filters[1]["multiplierUp"],
            mul_down=symbol_filters[1]["multiplierDown"],
            avg_price_mins=symbol_filters[1]["avgPriceMins"]
        )

        lot_size_filter = LotSizeFilter(
            min_qty=symbol_filters[2]["minQty"],
            max_qty=symbol_filters[2]["maxQty"],
            step_size=symbol_filters[2]["stepSize"]
        )

        market_lot_size_filter = MarketLotSizeFilter(
            min_qty=symbol_filters[5]["minQty"],
            max_qty=symbol_filters[5]["maxQty"],
            step_size=symbol_filters[5]["stepSize"]
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
        quote_quantity: Decimal,
    ) -> bool:
        """
        Validate the quote quantity against the Market Lot Size filter:
        https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#filters
        Args:
            symbol (Symbol): Crypto pair
            quote_quantity (Decimal): Quantity to spend/receive in quote asset
        Return
            Bool
        """
        market_lot_size_filter = symbol.filters.market_lot_size_filter
        if quote_quantity < market_lot_size_filter.min_qty:
            return False

        if quote_quantity > market_lot_size_filter.max_qty:
            return False

        if market_lot_size_filter.step_size:
            if (round(quote_quantity, symbol.qty_decimal_precision) != quote_quantity):
                return False

        if not isinstance(quote_quantity, float):
            return False

        print("Quote quantity (market order) is validated")
        print("Quote quantity:", quote_quantity)
        return True

    def validate_qty(
        self,
        symbol: Symbol,
        quantity: Decimal
    ) -> bool:
        """
        Validate the base quantity for against the Lot Size filter:
        https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#filters
        Args:
            symbol (Symbol): Crypto pair
            quantity (Decimal): Quantity to buy/sell in base asset
        Return
            Bool
        """

        lot_size_filter = symbol.filters.lot_size_filter
        if quantity < lot_size_filter.min_qty:
            return False

        if quantity > lot_size_filter.max_qty:
            return False

        if lot_size_filter.step_size:
            if round(quantity, symbol.qty_decimal_precision) != quantity:
                return False

        print("Quantity (limit order) is validated")
        print("Quantity:", quantity)
        return True

    def validate_price(
        self,
        symbol: Symbol,
        price: Decimal,
    ) -> bool:
        """
        Validate the price for against the Price and Percent filters:
        https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#filters
        Args:
            symbol (Symbol): Crypto pair
            price (Decimal): Price to spend/received for a base asset
        Return
            Bool
        """
        # Price filter check
        price_filter = symbol.filters.price_filter
        percent_price_filter = symbol.filters.percent_price_filter

        if price < price_filter.min_price:
            return False

        if price > price_filter.max_price:
            return False

        if price_filter.tick_size:
            if round(price, symbol.price_decimal_precision) != price:
                return False

        if price > symbol.average_price * percent_price_filter.mul_up:
            return False

        if price < symbol.average_price * percent_price_filter.mul_down:
            return False

        print("Price is validated")
        print("Price: ", price)
        return True

    def create_market_buy_order(
        self,
        symbol: Symbol,
        total_quote: Decimal
    ) -> Union[Dict, int]:
        """ Place a market buy order
        Args:
            symbol (Symbol): Crypto pair
            total_quote (Decimal): Quote total price to pay
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
        base_asset_quantity_to_buy: Decimal,
        quote_unit_price: str,
    ) -> Union[Dict, int]:
        """ Place a limit buy order
        Args:
            symbol (Symbol): Crypto pair
            base_quantity (Decimal): Base asset quantity to buy
            quote_unit_price (str): Quote asset unit price
        Return
            Dict, Integer
        """
        try:
            buy_order = self.order_limit_buy(
                symbol=symbol.symbol,
                quantity=base_asset_quantity_to_buy,
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
        base_asset_quantity_to_sell: Decimal,
        sell_price_profit: str,
        sell_price_stop_loss: str,
    ) -> Dict:
        """
        Place a Sell OCO order
        Args:
            symbol (Symbol): Crypto pair
            base_asset_quantity_to_sell (Decimal): Base asset quantity to buy
            sell_price_profit (str): Price to sell
            sell_price_stop_loss (str): Stoploss price to sell
        Return:
            Dict
        """
        try:
            sell_order = self.create_oco_order(
                symbol=symbol.symbol,
                side=SIDE_SELL,
                quantity=base_asset_quantity_to_sell,
                price=sell_price_profit,
                stopPrice=sell_price_stop_loss,
                stopLimitPrice=sell_price_stop_loss,
                stopLimitTimeInForce=TIME_IN_FORCE_GTC
            )
            print("-> The sell oco order has been sent")

        except BinanceAPIException as e:
            print(f"(Code {e.status_code}) {e.message}")
            return {}

        else:
            return sell_order

    def cancel_open_order(
        self,
        symbol: Symbol,
        order_id: str
    ) -> Dict:
        """
        Cancel an open order
        Args:
            symbol (Symbol): Crypto pair
            order_id (str): Open order id
        Return
            Dict
        """
        try:
            cancel_result = client.cancel_order(
                symbol=symbol.symbol,
                orderId=order_id
            )
        
        except BinanceAPIException as e:
            print(f"(Code {e.status_code}) {e.message}")
            return {}

        else:
            return cancel_result

    def execute_buy_strategy(
        self,
        symbol: Symbol,
        order_type: str,
        quantity: Decimal,
        unit_price: Decimal,
    ) -> Union[Dict, Decimal, Decimal]:
        """
        Execute the buy strategy
        Args:
            symbol (Symbol): Crypto pair
            order_type (str): type of buy order (options: "limit", )
            quantity (Decimal): quantity to buy
            unit_price (Decimal): unitary buy price
        Return:
            Dict, Decimal, Decimal
        """

        print("=> Step 1 - Buy order execution")

        if order_type == "limit":
            print("Order validation in progress...")
            if not self.validate_qty(symbol, quantity):
                sys.exit("The order qty is not valid.")

            if not self.validate_price(symbol, unit_price):
                sys.exit("The order price is not valid.")

            buy_order, buy_order_id = self.create_limit_buy_order(
                symbol,
                quantity,
                unit_price
            )

            if not buy_order_id:
                sys.exit("Buy order has not been created")
        else:
            sys.exit("Order type not supported yet.")

        # Wait for few seconds (API may not find the order_id instantly after the executing)
        time.sleep(2)

        ORDER_IS_NOT_FILLED_YET = True
        while ORDER_IS_NOT_FILLED_YET:
            # Iterate few times if the Binance API is not responding
            for retry_number in range(3):
                try:
                    _order = self.get_order(
                        symbol=symbol.symbol,
                        orderId=buy_order_id
                    )
                except (BinanceAPIException, ECONNRESET) as e:
                    print("Connection failed. Retry...")
                    time.sleep(1)
                    continue
                else:
                    break
            else:
                print("Binance API is not responding, attempting to cancel the buy order...")
                # Cancel order
                _cancel_result = self.cancel_open_order(
                        symbol=symbol.symbol,
                        order_id=buy_order_id
                )
                print("Buy order canceled: ", _cancel_result)
                sys.exit(1)

            if _order["status"] == "FILLED":
                buy_order = _order
                print("The buy order has been filled!")
                break
            elif _order["status"] == "CANCELED":
                print("The buy order has been canceled (not by the script)!")
                sys.exit(1)
            else:
                print("The order is not filled yet...")
                time.sleep(3)

        buy_price = Decimal(buy_order["price"])
        buy_quantity = Decimal(buy_order["executedQty"])

        return buy_order, buy_quantity, buy_price

    def execute_sell_strategy(
        self,
        symbol: Symbol,
        sell_quantity: Decimal,
        buy_price: Decimal,
        profit: Decimal,
        loss: Decimal,
    ) -> Union[Dict, Dict]:
        """ Execute the sell strategy
        Args:
            symbol (Symbol): Crypto pair
            sell_quantity (Decimal): Quantity to sell (that has been bought previously)
            buy_price (Decimal): Total price spent for the previous buy order
            profit (Decimal): Percentage of the profit
            loss (Decimal): Percentage of the stoploss
        Return:
            Dict, Dict
        """
        # Place a sell OCO order
        print("=> Step 2 - Sell OCO order execution")

        # Calculate the selling price with profit
        price_profit = buy_price * (100 + profit)/100
        price_profit_str = get_formated_price(
            price_profit,
            symbol.price_decimal_precision
        )
        print(f"Selling price (profit): {price_profit_str}")
        # Calculate the stoploss price
        price_loss = buy_price * (100 - loss)/100
        price_loss_str = get_formated_price(
            price_loss,
            symbol.price_decimal_precision
        )
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
