from typing import Union, List, Dict, Optional
from datetime import datetime
from decimal import Decimal

import sys
import time

from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException
from binance.enums import TIME_IN_FORCE_GTC


from .object_values.filters import (
    Filters,
    PriceFilter,
    PercentPriceFilter,
    LotSizeFilter,
    MarketLotSizeFilter,
)
from .object_values.orders import (
    Order,
    LimitOrder,
    MarketOrder,
    OrderInfo,
    OCOOrder
)
from .object_values.symbol import Symbol
from .entities import OrderInProgress

from .tools import (
    get_formated_price,
    datetime_to_iso8601,
    decimal_precision_from_scientific_notation
)

MULT_MILLISECONDS_TO_SECONDS = 1000


class Client:

    def __init__(
        self,
        api_key: str,
        api_secret: str,
    ) -> None:
        """
        Initialize the Binance client
        Args:
            api_key (str): api key for binance api client
            api_secret (str): api secret for binance api client
        Return:
            None
        """

        self.binance_client = BinanceClient(
            api_key=api_key,
            api_secret=api_secret
        )

        server_time_utc_iso8601 = datetime_to_iso8601(
            self.get_binance_api_server_time()
        )
        print(f"Binance API Time: {server_time_utc_iso8601}")

        if not self.is_binance_api_live():
            sys.exit("Binance API is down")
        print("Binance API is up")

    def get_binance_api_server_time(self) -> datetime:
        """Retrieve Binance API UTC server time as a datetime."""
        server_time_unix_epoch = self.binance_client.get_server_time()
        server_time_utc_datetime = datetime.utcfromtimestamp(
            server_time_unix_epoch["serverTime"]/MULT_MILLISECONDS_TO_SECONDS
        )
        return server_time_utc_datetime

    def is_binance_api_live(self) -> bool:
        """Get binance api status."""
        return not bool(self.binance_client.get_system_status()["status"])

    def get_symbol(self, symbol_name: str) -> Symbol:
        """
        Set the information about a symbol.
        Args:
            symbol_name (str): name of the symbol to retrieve
        Return:
            Symbol
        """
        symbol_info = self.binance_client.get_symbol_info(symbol_name)
        if not symbol_info:
            sys.exit(f"No info found for the symbol {symbol_name}")

        filters = self._get_filters(symbol_info["filters"])

        avg_price = self.get_avg_symbol_price(symbol_name)

        price_round = decimal_precision_from_scientific_notation(
            filters.price_filter.min_price
        )
        qty_round = decimal_precision_from_scientific_notation(
            filters.lot_size_filter.min_qty
        )

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

    def get_avg_symbol_price(self, symbol_name: str) -> Decimal:
        return Decimal(
            self.binance_client.get_avg_price(symbol=symbol_name)['price']
        )

    def _get_filters(
        self,
        symbol_filters: List[Dict]
    ) -> Filters:
        """
        Get the filters.
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

    def create_market_buy_order(
        self,
        order: MarketOrder
    ) -> Optional[OrderInProgress]:
        """
        Place a market buy order.
        Args:
            order (MarketOrder): Market order to be executed by Binance
        Return
            OrderInProgress
        """
        try:
            buy_order = self.binance_client.order_market_buy(
                symbol=order.symbol.symbol,
                quoteOrderQty=order.total,
            )
            order_in_progress = OrderInProgress(
                id=buy_order["orderId"],
                order=order
            )
            print("The market order has been sent")

        except BinanceAPIException as e:
            print(f"(Code {e.status_code}) {e.message}")
            return None

        else:
            return order_in_progress

    def create_limit_buy_order(
        self,
        order: LimitOrder,
    ) -> Optional[OrderInProgress]:
        """
        Place a limit buy order.
        Args:
            order (LimitOrder): Limit order to be executed by Binance
        Return
            OrderInProgress
        """
        try:
            buy_order = self.binance_client.order_limit_buy(
                symbol=order.symbol.symbol,
                quantity=order.quantity,
                price=order.price,
            )
            order_in_progress = OrderInProgress(
                id=buy_order["orderId"],
                order=order
            )
            print("-> The limit buy order has been sent")

        except BinanceAPIException as e:
            print(f"(Code {e.status_code}) {e.message}")
            return None

        else:
            return order_in_progress

    def create_sell_oco_order(
        self,
        order: OCOOrder,
    ) -> Dict:
        """
        Place a Sell OCO order.
        Args:
            order: OCOOrder
        Return:
            Dict
        """
        try:
            sell_order = self.binance_client.create_oco_order(
                symbol=order.symbol.symbol,
                side=order.side,
                quantity=order.quantity,
                price=order.price,
                stopPrice=order.stop_price,
                stopLimitPrice=order.stop_limit_price,
                stopLimitTimeInForce=order.time_in_force
            )
            print("-> The sell oco order has been sent")

        except BinanceAPIException as e:
            print(f"(Code {e.status_code}) {e.message}")
            return {}

        else:
            return sell_order

    def cancel_open_order(
        self,
        order_in_progress: OrderInProgress,
    ) -> Dict:
        """
        Cancel an open order.
        Args:
            order_in_progress (OrderInProgress): Order executed by Binance
        Return
            Dict
        """
        try:
            cancel_result = self.binance_client.cancel_order(
                symbol=order_in_progress.order.symbol.symbol,
                orderId=order_in_progress.id
            )

        except BinanceAPIException as e:
            print(f"(Code {e.status_code}) {e.message}")
            return {}

        else:
            return cancel_result

    def execute_buy_strategy(
        self,
        order: Order,
    ) -> OrderInProgress:
        """
        Execute the buy strategy.
        Args:
            order (Order): Order to be executed by Binance
        Return:
            OrderInProgress
        """

        print("=> Step 1 - Buy order execution")

        if isinstance(order, LimitOrder):
            if not (buy_order_in_progress := self.create_limit_buy_order(order)):
                sys.exit("Limit buy order has not been created")

        elif isinstance(order, MarketOrder):
            if not (buy_order_in_progress := self.create_market_buy_order(order)):
                sys.exit("Market buy order has not been created")
        else:
            sys.exit("Order type not supported yet.")

        # Wait for few seconds (API may not find the order_id instantly after the executing)
        time.sleep(3)

        NB_MAX_ATTEMPTS = 10
        ORDER_IS_NOT_FILLED_YET = True
        while ORDER_IS_NOT_FILLED_YET:
            # Iterate few times if the Binance API is not responding
            for retry_number in range(NB_MAX_ATTEMPTS):
                try:
                    self.update_order_info(
                        order_in_progress=buy_order_in_progress
                    )
                except Exception as e:
                    print(f"({retry_number + 1}) Connection failed. Retry...", e)
                    time.sleep(2)
                    continue
                else:
                    break
            else:
                print("Binance API is not responding, attempting to cancel the buy order...")
                # Cancel order
                _cancel_result = self.cancel_open_order(
                    order_in_progress=buy_order_in_progress
                )
                sys.exit(f"Buy order canceled: {_cancel_result}")

            if buy_order_in_progress.info.status == "FILLED":
                print("The buy order has been filled!")
                break

            elif buy_order_in_progress.info.status == "CANCELED":
                sys.exit("The buy order has been canceled (not by the script)!")

            else:
                print("The order is not filled yet...")
                time.sleep(3)

        return buy_order_in_progress

    def update_order_info(
        self,
        order_in_progress: OrderInProgress,
    ) -> None:
        """Get current status of an existing order."""

        order_info_binance = self.binance_client.get_order(
            symbol=order_in_progress.order.symbol.symbol,
            orderId=order_in_progress.id
        )

        if isinstance(order_in_progress.order, LimitOrder):
            buy_price = Decimal(order_info_binance["price"])

        elif isinstance(order_in_progress.order, MarketOrder):
            buy_price = (
                Decimal(order_info_binance["cummulativeQuoteQty"])
                / Decimal(order_info_binance["executedQty"])
            )

        else:
            sys.exit("Buy order type not supported")

        order_info_client = OrderInfo(
            status=order_info_binance["status"],
            price=buy_price,
            cummulative_quote_quantity=order_info_binance["cummulativeQuoteQty"],
            executed_quantity=order_info_binance["executedQty"]
        )
        order_in_progress.info = order_info_client

    def execute_sell_strategy(
        self,
        order_in_progress: OrderInProgress,
        profit: Decimal,
        loss: Decimal,
    ) -> Union[Dict, Dict]:
        """
        Execute the sell strategy.
        Args:
            order_in_progress (OrderInProgress): Order executed by Binance
            profit (Decimal): Percentage of the profit
            loss (Decimal): Percentage of the stoploss
        Return:
            Dict, Dict
        """
        # Place a sell OCO order
        print("=> Step 2 - Sell OCO order execution")
        bought_price = order_in_progress.info.price

        # Calculate the selling price with profit
        price_profit = round(
            bought_price * (100 + profit)/100,
            order_in_progress.order.symbol.price_decimal_precision
        )
        price_profit_str = get_formated_price(
            price_profit,
            order_in_progress.order.symbol.price_decimal_precision
        )
        print(f"Selling price (profit): {price_profit_str}")
        # Calculate the stoploss price
        price_loss = round(
            bought_price * (100 - loss)/100,
            order_in_progress.order.symbol.price_decimal_precision
        )
        price_loss_str = get_formated_price(
            price_loss,
            order_in_progress.order.symbol.price_decimal_precision
        )
        print(f"Stoploss price: {price_loss_str}")
        oco_order = OCOOrder(
            symbol=order_in_progress.order.symbol,
            side=Order.SideEnum.sell,
            price=price_profit,
            quantity=order_in_progress.info.executed_quantity,
            stop_price=price_loss,
            stop_limit_price=price_loss,
            time_in_force=TIME_IN_FORCE_GTC
        )
        sell_order = self.create_sell_oco_order(order=oco_order)

        sell_orders = sell_order["orderReports"]
        stop_loss_limit_order = sell_orders[0]
        limit_maker_order = sell_orders[1]

        return stop_loss_limit_order, limit_maker_order
