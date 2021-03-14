from decimal import Decimal
from datetime import datetime
from typing import Any

DEFAULT_DECIMAL_PLACES = 2


def get_formated_price(
    amount: Decimal,
    precision: int = DEFAULT_DECIMAL_PLACES
) -> str:
    """
    Format the price with a precision
    Args:
        amount (Float): Amount to format
        precision (Integer): Precision to use
    Return:
        formated price (String)
    """
    return "{:0.0{}f}".format(amount, precision)


def datetime_to_iso8601(
    datetime_to_convert: datetime,
    iso8601_template: str = '%Y-%m-%d %H:%M:%SZ'
) -> str:
    "Convert a datetime to a string in iso8601 format"
    return datetime_to_convert.strftime(iso8601_template)


def strict_integer_validator(cls, v: Any) -> int:
    """
    Casts a value `v` as an integer if it represents exactly an integer.
    Otherwise throw a `ValueError`
    """
    if int(v) != Decimal(v):
        raise ValueError
    return int(v)


def decimal_precision_from_scientific_notation(decimal_value: Decimal) -> int:
    """
    Retrieve the decimal precision of a Decimal of the strict form 10^n
    (with n an integer and -n the decimal_precision of the number).
    For example:
        10.0 <=> 10^1 => decimal_precision = -1
        0.001 <=> 10^-3 => decimal_precision = 3
        0.00001 <=> 10^-5 => decimal_precision = 5
        0.000011 != 10^n => ValueError
    """
    return strict_integer_validator(
        None,
        -decimal_value.log10()
    )


def is_valid_significant_digits(
    value: Decimal,
    max_significant_digits: int
) -> bool:
    """
        Are the significant digits with a lower precision than the accepted limit.
        >>> is_valid_significant_digits(Decimal(0.001), 3)
        ... True
        >>> is_valid_significant_digits(Decimal(0.0011), 3)
        ... False
    """
    return round(value, max_significant_digits) == value
