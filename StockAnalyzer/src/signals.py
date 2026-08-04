"""Golden Cross / Death Cross detection.

A Golden Cross occurs when the 50-day moving average crosses *above* the
200-day moving average (bullish signal). A Death Cross is the inverse
(bearish signal). Detection is fully vectorized with pandas — no explicit
row-by-row loops.
"""

from __future__ import annotations

from typing import TypedDict

import pandas as pd

GOLDEN_CROSS = "Golden Cross"
DEATH_CROSS = "Death Cross"


class CrossSignal(TypedDict):
    """A single detected moving-average crossover event."""

    Ticker: str
    Date: pd.Timestamp
    Signal: str
    Price: float


def detect_crosses(dataframe: pd.DataFrame, ticker: str) -> list[CrossSignal]:
    """Detect every Golden Cross / Death Cross event in a stock's history.

    Args:
        dataframe: Price history that already contains ``MA50`` and
            ``MA200`` columns (see :func:`src.indicators.add_indicators`).
        ticker: Ticker symbol, stored alongside each signal for reporting.

    Returns:
        A list of signal records ordered chronologically. Empty if the
        history is too short for both moving averages to be defined.
    """
    valid = dataframe.dropna(subset=["MA50", "MA200"])
    if valid.empty:
        return []

    is_above = valid["MA50"] > valid["MA200"]
    # +1 => flipped from below to above (Golden Cross)
    # -1 => flipped from above to below (Death Cross)
    transition = is_above.astype(int).diff()

    golden_dates = valid.index[transition == 1]
    death_dates = valid.index[transition == -1]

    signals: list[CrossSignal] = [
        {"Ticker": ticker, "Date": date, "Signal": GOLDEN_CROSS, "Price": float(valid.loc[date, "Close"])}
        for date in golden_dates
    ]
    signals += [
        {"Ticker": ticker, "Date": date, "Signal": DEATH_CROSS, "Price": float(valid.loc[date, "Close"])}
        for date in death_dates
    ]
    signals.sort(key=lambda record: record["Date"])
    return signals


def latest_cross_status(dataframe: pd.DataFrame) -> tuple[str, str]:
    """Determine the current Golden/Death Cross state as of the last row.

    Returns:
        A tuple ``(golden_cross_status, death_cross_status)`` where each
        value is ``"Active"`` or ``"Inactive"``. "Active" for
        golden-cross-status means MA50 is currently above MA200 (bullish
        trend in effect); the death-cross status is simply the inverse.
    """
    valid = dataframe.dropna(subset=["MA50", "MA200"])
    if valid.empty:
        return "Unknown", "Unknown"
    ma50_above = bool(valid["MA50"].iloc[-1] > valid["MA200"].iloc[-1])
    return ("Active" if ma50_above else "Inactive"), ("Inactive" if ma50_above else "Active")
