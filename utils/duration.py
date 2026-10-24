import re


def parse_duration(value: str) -> int | None:
    match = re.fullmatch(r"(\d+)(m|h|d)", value.lower())

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if amount <= 0:
        return None

    multipliers = {
        "m": 60,
        "h": 60 * 60,
        "d": 24 * 60 * 60,
    }

    return amount * multipliers[unit]

