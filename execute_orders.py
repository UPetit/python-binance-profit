import sys
import argparse

import numpy as np
from environs import Env

from app.client import Client
from app.entities import Symbol


# Get Binance keys
env = Env()
env.read_env()

API_KEY = env.str("API_KEY", None)
SECRET_KEY = env.str("SECRET_KEY", None)
if API_KEY is None or SECRET_KEY is None:
    sys.exit("Neither `API_KEY` nor `SECRET_KEY` environment variables are defined!")


def main(symbol_name, quantity, price, profit, loss):

    client = Client(api_key=API_KEY, api_secret=SECRET_KEY)
    symbol = client.get_symbol(symbol_name)

    buy_order_type = "limit"

    # To be used to check the Percent Filter rule
    avg_price = client.get_avg_price(symbol)

    # Get the precisions for both price and quantity
    price_round = int(-np.log10(symbol.filters.price_filter.min_price))
    # print("Min price decimal:", price_round)
    qty_round = int(-np.log10(symbol.filters.lot_size_filter.min_qty))
    # print("Min quantity decimal:", qty_round)

    # Place a market buy order
    buy_order, buy_quantity, buy_price = client.execute_buy_strategy(
        symbol,
        buy_order_type,
        avg_price,
        quantity,
        price,
        qty_round,
        price_round
    )

    print(f"=> Buy price: {buy_price} {symbol.quote_asset}")
    print(
        f"=> Total price: {round(float(buy_order['cummulativeQuoteQty']), price_round)} "
        f"{symbol.quote_asset}"
    )
    print(f"=> Buy quantity: {buy_quantity} {symbol.base_asset}")

    stop_loss_limit_order, limit_maker_order = client.execute_sell_strategy(
        buy_quantity,
        buy_price,
        profit,
        loss,
        price_round
    )
    print("=> OCO order summary:")
    print("Stop loss limit order:", stop_loss_limit_order)
    print("Limit maker order:", limit_maker_order)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="define the symbol of the crypto pair to trade"
    )
    parser.add_argument(
        "--quantity",
        type=float,
        required=True,
        help="define the quantity to buy"
    )
    parser.add_argument(
        "--price",
        type=float,
        required=True,
        help="define the unit price to spend"
    )
    parser.add_argument(
        "--profit",
        type=float,
        required=True,
        help="define the profit to make in percentage between 0.0 and 1.0"
    )
    parser.add_argument(
        "--loss",
        type=float,
        required=True,
        help="define the stoploss in percentage between 0.0 and 1.0"
    )
    args = parser.parse_args()

    if not (
        0.0 < args.profit <= 1.0
        and 0.0 < args.loss <= 1.0
    ):
        sys.exit("The profit and the loss should be between 0.0 and 1.0")

    main(
        str(args.symbol),
        float(args.quantity),
        str(args.price),
        float(args.profit),
        float(args.loss)
    )
