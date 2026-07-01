from datetime import datetime

import pytz  # type: ignore[import-untyped]


def get_mexico_now() -> datetime:
    mexico_tz = pytz.timezone("America/Mexico_City")
    return datetime.now(mexico_tz)
