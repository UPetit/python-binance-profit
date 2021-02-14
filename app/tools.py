from decimal import Decimal

DEFAULT_DECIMAL_PLACES = 2


def get_formated_price(
    amount: Decimal,
    precision: int = DEFAULT_DECIMAL_PLACES
) -> str:
    """ Format the price with a precision
    Args:
        amount (Float): Amount to format
        precision (Integer): Precision to use
    Return:
        formated price (String)
    """
    return "{:0.0{}f}".format(amount, precision)


def strict_integer_validator(cls, v):
    if Decimal(v) != int(v):
        raise ValueError
    return v