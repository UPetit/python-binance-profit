import os
import sys
import time
import argparse
from datetime import datetime

import numpy as np

# Binance
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException


def init_binance_client():
    """ Initialize the Binance client
    Args:
        None
    Return:
        None
    """
    # Get Binance keys
    API_KEY = os.environ.get("BIN_API_KEY")
    SECRET_KEY = os.environ.get("BIN_SECRET_KEY")
    
    if API_KEY == None or SECRET_KEY == None:
        print("One or both of the environment variables don't exist")
        sys.exit(0)
    
    # Init client
    print("Load client")
    client = Client(API_KEY, SECRET_KEY)
    print("Client authenticated")
    
    # Get server time
    time_res = client.get_server_time()
    time_res_date = datetime.utcfromtimestamp(time_res["serverTime"]/1000).strftime('%Y-%m-%d %H:%M:%SZ')
    print(f"Binance API Time: {time_res_date}")
    
    status = client.get_system_status()
    if status["status"] == 0:
        print(f"Binance API status: {status['msg']}")
    else:
        print(f"Binance API status: {status}")
        sys.exit(0)
    
    return client


def get_symbol_info(symbol, client):
    """ Get the information about a symbol
    Args:
        symbol (String): Crypto pair
        client (binance.client.Client): Binance client
    Return:
        Dict
    """
    info = client.get_symbol_info(symbol)
    
    # Check that trading is allowed
    if (info["status"] == "TRADING") and (info["isSpotTradingAllowed"] == True):
        print("Trading allowed")
    else:
        print("Spot trading is not enabled on this pair")
        sys.exit(0)
    
    # Check that OCO orders are allowed
    if info["ocoAllowed"] == True:
        print("OCO orders allowed")
    else:
        print("OCO order is not allowed on this pair")
        sys.exit(0)
    
    return info


def get_filters(info):
    """ Get the filters
    Args:
        info (Dict): Information about crypto pair
    Return:
        Dict, Dict, Dict, Dict
    """
    # PRICE FILTER
    price_filter = {
        "min_price": float(info["filters"][0]["minPrice"]),
        "max_price": float(info["filters"][0]["maxPrice"]),
        "tick_size": float(info["filters"][0]["tickSize"])
    }

    #PERCENT_PRICE filter
    percent_filter = {
        "mul_up": float(info["filters"][1]["multiplierUp"]),
        "mul_down": float(info["filters"][1]["multiplierDown"]),
        "avg_price_mins": float(info["filters"][1]["avgPriceMins"])
    }

    # LOT_SIZE filter
    lot_filter = {
        "min_qty": float(info["filters"][2]["minQty"]),
        "max_qty": float(info["filters"][2]["maxQty"]),
        "step_size": float(info["filters"][2]["stepSize"])
    }

    # MARKET_LOT_SIZE filter
    market_lot_filter = {
        "min_qty": float(info["filters"][5]["minQty"]),
        "max_qty": float(info["filters"][5]["maxQty"]),
        "step_size": float(info["filters"][5]["stepSize"])
    }

    return price_filter, percent_filter, lot_filter, market_lot_filter


def get_formated_price(amount, precision):
    """ Format the price with a precision
    Args:
        amount (Float): Amount to format
        precision (Integer): Precision to use
    Return:
        String
    """
    amt_formated = "{:0.0{}f}".format(amount, precision)
    
    return amt_formated


def validate_quote_qty(mkt_lot_filter, quote_quantity):
    """ Validate the quote quantity against the Market Lot Size filter:
    https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#filters
    Args:
        mkt_lot_filter (Dict): Market lot size filter rules
        quote_quantity (Float): Quantity to spend/receive in quote asset
    Return
        Bool
    """
    if quote_quantity >= mkt_lot_filter["min_qty"]:
        pass
    else:
        return False
    if quote_quantity <= mkt_lot_filter["max_qty"]:
        pass
    else:
        return False
    if mkt_lot_filter["step_size"] != 0.0:
        if round(quote_quantity, qty_round) == quote_quantity:
            pass
        else:
            return False
    else:
        pass
    if isinstance(quote_quantity, float):
        pass
    else:
        return False
    
    print("Quote quantity (market order) is validated")
    print("Quote quantity:", quote_quantity)
    return True


def validate_qty(lot_filter, quantity, qty_round):
    """ Validate the base quantity for against the Lot Size filter: 
    https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#filters
    Args:
        lot_filter (Dict): Lot size filter rules
        quantity (Float): Quantity to buy/sell in base asset
        qty_round (Integer): Precision for quantity
    Return
        Bool
    """
    if quantity >= lot_filter["min_qty"]:
        pass
    else:
        return False
    if quantity <= lot_filter["max_qty"]:
        pass
    else:
        return False
    if lot_filter["step_size"] != 0.0:
        if round(quantity, qty_round) == quantity:
            pass
        else:
            return False
    else:
        pass
    
    if isinstance(quantity, float):
        pass
    else:
        return False
    print("Quantity (limit order) is validated")
    print("Quantity:", quantity)
    return True


def validate_price(price_filter, percent_filter, avg_price_quote, price, price_round):
    """ Validate the price for against the Price and Percent filters: 
    https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#filters
    Args:
        price_filter (Dict): Price filter rules
        percent_filter (Dict): Percent filter rules
        avg_price_quote (String): Avg Price (quote asset)
        price (String): Price to spend/received for a base asset
        price_round (Integer): Precision for price
    Return
        Bool
    """
    # Price filter check
    if float(price) >= price_filter["min_price"]:
        pass
    else:
        return False
    if float(price) <= price_filter["max_price"]:
        pass
    else:
        return False
    if price_filter["tick_size"] != 0.0:
        if round(float(price), price_round) == float(price):
            pass
        else:
            return False
    else:
        pass
    
    # Percent filter check
    if float(price) <= float(avg_price_quote) * percent_filter["mul_up"]:
        pass
    else:
        return False
    if float(price) >= float(avg_price_quote) * percent_filter["mul_down"]:
        pass
    else:
        return False
    
    if isinstance(price, str):
        pass
    else:
        return False
    print("Price is validated")
    print("Price:", price)
    return True


def create_market_buy_order(symbol, total_quote):
    """ Place a market buy order
    Args:
        symbol (String): Crypto pair
        total_quote (Float): Quote total price to pay
    Return
        Dict, Integer
    """
    try:
        buy_order = client.order_market_buy(
            symbol=symbol,
            quoteOrderQty=total_quote)
        buy_order_id = buy_order["orderId"]
        print("The market order has been sent")
        return buy_order, buy_order_id
    
    except BinanceAPIException as e:
        print(f"(Code {e.status_code}) {e.message}")
    
    return {}, 0


def create_limit_buy_order(symbol, client, base_quantity, quote_unit_price):
    """ Place a limit buy order
    Args:
        symbol (String): Crypto pair
        client (binance.client.Client): Binance client
        base_quantity (Float): Base asset quantity to buy
        quote_unit_price (String): Quote asset unit price
    Return
        Dict, Integer
    """
    try:
        buy_order = client.order_limit_buy(
            symbol=symbol,
            quantity=base_quantity,
            price=quote_unit_price)
        buy_order_id = buy_order["orderId"]
        print("-> The limit buy order has been sent")
        return buy_order, buy_order_id
    
    except BinanceAPIException as e:
        print(f"(Code {e.status_code}) {e.message}")
    
    return {}, 0


def create_sell_oco_order(symbol, client, base_quantity, price_profit, price_loss):
    """ Place a Sell OCO order
    Args:
        symbol (String): Crypto pair
        client (binance.client.Client): Binance client
        base_quantity (Float): Base asset quantity to buy
        price_profit (String): Price to sell
        price_loss (String): Stoploss price to sell
    Return:
        Dict
    """
    try:
        sell_order = client.create_oco_order(
            symbol=symbol,
            side=SIDE_SELL,
            quantity=base_quantity,
            price=price_profit,
            stopPrice=price_loss,
            stopLimitPrice=price_loss,
            stopLimitTimeInForce=TIME_IN_FORCE_GTC)
        print("-> The sell oco order has been sent")
        return sell_order

    except BinanceAPIException as e:
        print(f"(Code {e.status_code}) {e.message}")
    
    return {}


def execute_buy_strategy(symbol, client, buy_order_type, price_filter, percent_filter,
                        lot_filter, avg_price, quantity, unit_price, qty_round,
                        price_round):
    """ Execute the buy strategy
    Args:
        symbol (String): Crypto pair
        client (binance.client.Client): Binance client
        buy_order_type (String): Type of the buying order
        price_filter (Dict): Price trading rules
        percent_filter (Dict): Percent price trading rules
        lot_filter (Dict): Quantity trading rules 
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
    #if buy_order_type == "market":
    #    print("Order validation in progress...")
    #    #quote_qty = round(quote_qty, price_round)
    #    is_quote_qty_valid = validate_quote_qty(market_lot_filter, quote_qty)
    #    if is_quote_qty_valid == True:
    #        buy_order, buy_order_id = create_market_buy_order(symbol, quote_qty)
    #    else:
    #        sys.exit(f"The order is not valid.")
    if buy_order_type == "limit":
        print("Order validation in progress...")
        is_qty_valid = validate_qty(lot_filter, quantity, qty_round)
        is_price_valid = validate_price(price_filter, percent_filter, avg_price["price"], 
                                        unit_price, price_round)
        if is_qty_valid == True and is_price_valid == True:
            buy_order, buy_order_id = create_limit_buy_order(symbol, client, quantity,
                                                            unit_price)
        else:
            sys.exit(f"The order is not valid.")
    else:
        sys.exit("Order type not supported yet.")

    # Check if the order has been created
    if buy_order_id == 0:
        sys.exit("Buy order has not been created")

    # Wait for few seconds (API may not find the order_id instantly after the executing)
    time.sleep(2)

    is_filled = False
    # Wait until the Buy Order has been filled
    while is_filled == False:
        _order = client.get_order(symbol=symbol,
                                orderId=buy_order_id)
        if _order["status"] == "FILLED":
            buy_order = _order
            is_filled = True
        else:
            print("The order is not filled yet...")
            time.sleep(3)

    print(f"The buy order has been filled!")
    # If multiple trades have been executed, calculate the weighted
    # average price and sum the quantity bought (that's what Binance
    # is doing in this case)
    #if buy_order_type == "market":
    #    weighted_prices = 0.0
    #    quantity_sum = 0.0
    #    for trade in buy_order["fills"]:
    #        weighted_prices += float(trade["price"])*float(trade["qty"])
    #        quantity_sum += float(trade["qty"])
    #
    #   buy_price = round(weighted_prices/quantity_sum, price_round)
    #    buy_quantity = quantity_sum
    #else:
    buy_price = float(buy_order["price"])
    buy_quantity = float(buy_order["executedQty"])
    
    return buy_order, buy_quantity, buy_price


def execute_sell_strategy(symbol, client, sell_quantity, buy_price, profit, loss, price_round):
    """ Execute the sell strategy
    Args:
        symbol (String): Crypto pair
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

    sell_order = create_sell_oco_order(symbol, client, sell_quantity,
                                        price_profit_str, price_loss_str)
    
    sell_orders = sell_order["orderReports"]
    stop_loss_limit_order = sell_orders[0]
    limit_maker_order = sell_orders[1]

    return stop_loss_limit_order, limit_maker_order


def main(symbol, quantity, price, profit, loss):

    client = init_binance_client()

    buy_order_type = "limit"

    info = get_symbol_info(symbol, client)

    # To be used to check the Percent Filter rule
    avg_price = client.get_avg_price(symbol=symbol)

    # Assets
    base_asset = info["baseAsset"]
    quote_asset = info["quoteAsset"]

    # Get each filter to use at the validation step
    price_filter, percent_filter, lot_filter, market_lot_filter = get_filters(info)

    # Get the precisions for both price and quantity
    price_round = int(-np.log10(price_filter["min_price"]))
    #print("Min price decimal:", price_round)
    qty_round = int(-np.log10(lot_filter["min_qty"]))
    #print("Min quantity decimal:", qty_round)
    
    # Place a market buy order
    buy_order, buy_quantity, buy_price = execute_buy_strategy(symbol, client,
                                                            buy_order_type,
                                                            price_filter,
                                                            percent_filter,
                                                            lot_filter, avg_price,
                                                            quantity, price,
                                                            qty_round, price_round)

    print(f"=> Buy price: {buy_price} {quote_asset}")
    print(f"=> Total price: {round(float(buy_order['cummulativeQuoteQty']), price_round)} " \
          f"{quote_asset}")
    print(f"=> Buy quantity: {buy_quantity} {base_asset}")

    stop_loss_limit_order, limit_maker_order = execute_sell_strategy(symbol, client,
                                                                    buy_quantity,
                                                                    buy_price,
                                                                    profit, loss,
                                                                    price_round)
    print("=> OCO order summary:")
    print("Stop loss limit order:", stop_loss_limit_order)
    print("Limit maker order:", limit_maker_order)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--symbol", type=str, required=True, 
                help="define the symbol of the crypto pair to trade")
    parser.add_argument("--quantity", type=float, required=True, 
                help="define the quantity to buy")
    parser.add_argument("--price", type=float, required=True, 
                help="define the unit price to spend")
    
    parser.add_argument("--profit", type=float, required=True, 
                help="define the profit to make in percentage between 0.0 and 1.0")
    
    parser.add_argument("--loss", type=float, required=True, 
                help="define the stoploss in percentage between 0.0 and 1.0")
    args = parser.parse_args()
    
    if (0.0 < args.profit <= 1.0) and (0.0 < args.loss <= 0):
        sys.exit("The profit and the loss should be between 0.0 and 1.0")
    else:
        pass

    main(str(args.symbol), float(args.quantity), str(args.price),
        float(args.profit), float(args.loss))