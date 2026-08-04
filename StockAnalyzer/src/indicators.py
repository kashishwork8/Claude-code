"""Technical indicator calculations built on top of pandas rolling windows.

Keeping indicators in their own module makes it trivial to extend later
(RSI, MACD, Bollinger Bands, ...) without touching data loading, signal
detection, or plotting code.
"""

from __future__ import annotations

import pandas as pd

SHORT_WINDOW = 50
LONG_WINDOW = 200


def calculate_daily_returns(prices: pd.Series) -> pd.Series:
    """Compute simple day-over-day percentage returns for a price series."""
    return prices.pct_change()


def calculate_moving_average(prices: pd.Series, window: int) -> pd.Series:
    """Compute a simple moving average over ``window`` trading days."""
    return prices.rolling(window=window, min_periods=window).mean()


def add_indicators(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``dataframe`` enriched with standard indicators.

    Adds:
        Daily_Return: simple daily percentage return of the close price.
        MA50: 50-day simple moving average of the close price.
        MA200: 200-day simple moving average of the close price.
    """
    enriched = dataframe.copy()
    enriched["Daily_Return"] = calculate_daily_returns(enriched["Close"])
    enriched["MA50"] = calculate_moving_average(enriched["Close"], SHORT_WINDOW)
    enriched["MA200"] = calculate_moving_average(enriched["Close"], LONG_WINDOW)
    return enriched
