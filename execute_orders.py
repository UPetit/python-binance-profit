from app.object_values.orders import LimitOrder, MarketOrder, Order
import sys
import argparse

from environs import Env
from pydantic import ValidationError, BaseModel

from app.client import Client
from app.object_values.args import MarketInputArgs, LimitInputArgs
from app.tools import get_formated_price


# Get Binance keys
env = Env()
env.read_env()

API_KEY = env.str("API_KEY", None)
SECRET_KEY = env.str("SECRET_KEY", None)
if API_KEY is None or SECRET_KEY is None:
    sys.exit("Either `API_KEY` or `SECRET_KEY` env. variable is not defined!")


def main(input_args: BaseModel) -> None:

    client = Client(api_key=API_KEY, api_secret=SECRET_KEY)
    symbol = client.get_symbol(input_args.symbol)

    # Buy_order_type = "limit"
    print(f"DEBUG - Buy order type: {input_args.buy_type}")

    # Place a market buy order
    if input_args.buy_type == "limit":
        buy_order = LimitOrder(
            symbol=symbol,
            side=Order.SideEnum.buy,
            price=input_args.price,
        )

    elif input_args.buy_type == "market":
        buy_order = MarketOrder(
            symbol=symbol,
            side=Order.SideEnum.buy,
            total=input_args.total
        )
    else:
        sys.exit("Buy order type not supported")

    order_in_progress = client.execute_buy_strategy(buy_order)
    print("=========================")
    print("=== Buy order summary ===")
    print(
        f"=> Buy price: "
        f"{get_formated_price(order_in_progress.info.price, symbol.price_decimal_precision)} "
        f"{symbol.quoteAsset}"
    )
    print(
        "=> Total price: "
        f"{round(order_in_progress.info.cummulative_quote_quantity, symbol.price_decimal_precision)} "
        f"{symbol.quoteAsset}"
    )
    print(
        f"=> Buy quantity: {get_formated_price(order_in_progress.info.executed_quantity, symbol.qty_decimal_precision)} "
        f"{symbol.baseAsset}"
    )

    stop_loss_limit_order, limit_maker_order = client.execute_sell_strategy(
        order_in_progress,
        input_args.profit,
        input_args.loss,
    )

    print("=========================")
    print("=== OCO order summary ===")
    print("== Stop loss limit order:", stop_loss_limit_order)
    print("== Limit maker order:", limit_maker_order)


def input_validation(raw_input_args, input_parser: BaseModel) -> BaseModel:

    try:
        cleaned_input_args = input_parser(**raw_input_args)
    except ValidationError as e:
        sys.exit(e)
    else:
        return cleaned_input_args


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--symbol",
        required=True,
        help="define the symbol of the crypto pair to trade"
    )
    parser.add_argument(
        "--buy_type",
        required=True,
        choices=["market", "limit"],
        help="define the type of buy order to execute: limit or market"
    )
    parser.add_argument(
        "--total",
        required=False,
        help="define the total amount to spend"
    )
    parser.add_argument(
        "--quantity",
        required=False,
        help="define the quantity to buy (decimal number)"
    )
    parser.add_argument(
        "--price",
        required=False,
        help="define the unit price to spend"
    )
    parser.add_argument(
        "--profit",
        required=False,
        help="define the profit to make in percentage between 0 and 100"
    )
    parser.add_argument(
        "--loss",
        required=False,
        help="define the stoploss in percentage between 0 and 100"
    )

    args = vars(parser.parse_args())
    if args["buy_type"] == "market":
        input_args_validated = input_validation(args, MarketInputArgs)
    elif args["buy_type"] == "limit":
        input_args_validated = input_validation(args, LimitInputArgs)
    else:
        sys.exit("The buy type argument is unknown")

    main(input_args=input_args_validated)
