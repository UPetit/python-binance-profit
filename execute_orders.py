import sys
import argparse
from decimal import Decimal

from environs import Env
from pydantic import ValidationError, BaseModel

from app.client import Client
from app.entities import InputArgs


# Get Binance keys
env = Env()
env.read_env()

API_KEY = env.str("API_KEY", None)
SECRET_KEY = env.str("SECRET_KEY", None)
if API_KEY is None or SECRET_KEY is None:
    sys.exit("Neither `API_KEY` nor `SECRET_KEY` environment variables are defined!")


def main(
    input_args: InputArgs
) -> None:

    client = Client(api_key=API_KEY, api_secret=SECRET_KEY)
    symbol = client.get_symbol(input_args.symbol)

    buy_order_type = "limit"

    # Place a market buy order
    buy_order, buy_quantity, buy_price = client.execute_buy_strategy(
        symbol,
        buy_order_type,
        input_args.quantity,
        input_args.price,
    )

    print(f"=> Buy price: {buy_price} {symbol.quoteAsset}")
    print(
        "=> Total price: "
        f"{round(Decimal(buy_order['cummulativeQuoteQty']), symbol.price_decimal_precision)} "
        f"{symbol.quoteAsset}"
    )
    print(f"=> Buy quantity: {buy_quantity} {symbol.baseAsset}")

    stop_loss_limit_order, limit_maker_order = client.execute_sell_strategy(
        symbol,
        buy_quantity,
        buy_price,
        input_args.profit,
        input_args.loss,
    )
    print("=> OCO order summary:")
    print("Stop loss limit order:", stop_loss_limit_order)
    print("Limit maker order:", limit_maker_order)


def input_validation(
    raw_input_args,
    input_validator: BaseModel = InputArgs
) -> BaseModel:

    try:
        input_args_validated = InputArgs(**args)
    except ValidationError as e:
        sys.exit(e)
    else:
        return input_args_validated


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--symbol",
        required=True,
        help="define the symbol of the crypto pair to trade"
    )
    parser.add_argument(
        "--quantity",
        required=True,
        help="define the quantity to buy (decimal number)"
    )
    parser.add_argument(
        "--price",
        required=True,
        help="define the unit price to spend"
    )
    parser.add_argument(
        "--profit",
        required=True,
        help="define the profit to make in percentage between 0 and 100"
    )
    parser.add_argument(
        "--loss",
        required=True,
        help="define the stoploss in percentage between 0 and 100"
    )

    args = vars(parser.parse_args())
    input_args_validated = input_validation(args)

    main(
        input_args=input_args_validated
    )
