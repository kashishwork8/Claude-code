"""Downloading and caching historical price data via ``yfinance``.

All network access to Yahoo Finance is centralized in this module so that
error handling (bad ticker, no internet, empty response, ...) lives in a
single, well-tested place.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import yfinance as yf

from src.utils import print_error, print_success, print_warning

# Minimum number of trading days required for the analysis (roughly one
# year) below which we still process the stock but warn the user that the
# 200-day moving average and long-horizon metrics will be unreliable.
MIN_RECOMMENDED_ROWS = 200


def download_price_history(ticker: str, period: str = "max") -> Optional[pd.DataFrame]:
    """Download the full available daily price history for one ticker.

    Args:
        ticker: Stock ticker symbol, e.g. ``"AAPL"``.
        period: yfinance period string. Defaults to ``"max"`` so we always
            pull the longest history available.

    Returns:
        A DataFrame indexed by date with OHLCV columns (adjusted for splits
        and dividends), or ``None`` if the download failed or returned no
        usable data.
    """
    try:
        raw = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    except Exception as exc:  # network errors, throttling, etc.
        print_error(f"{ticker}: download failed ({exc})")
        return None

    if raw is None or raw.empty:
        print_error(f"{ticker}: no data returned (invalid ticker or delisted)")
        return None

    raw = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    raw.index = pd.to_datetime(raw.index).tz_localize(None)
    raw.index.name = "Date"
    raw = raw.dropna(subset=["Close"])

    if raw.empty:
        print_error(f"{ticker}: dataset empty after cleaning")
        return None

    if len(raw) < MIN_RECOMMENDED_ROWS:
        print_warning(
            f"{ticker}: only {len(raw)} trading days available; "
            "long-term indicators (e.g. 200-day MA) may be incomplete."
        )

    return raw


def save_price_history(dataframe: pd.DataFrame, ticker: str, data_dir: Path) -> Path:
    """Persist a ticker's price history to CSV inside ``data_dir``.

    Returns:
        The path the file was written to.
    """
    output_path = data_dir / f"{ticker}.csv"
    dataframe.to_csv(output_path)
    return output_path


def download_all(tickers: list[str], data_dir: Path) -> Dict[str, pd.DataFrame]:
    """Download and save price history for every ticker in ``tickers``.

    Failures for individual tickers are logged and skipped rather than
    raised, so one bad symbol never aborts the whole batch.

    Returns:
        Mapping of ticker -> price history DataFrame, containing only the
        tickers that downloaded successfully.
    """
    results: Dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        history = download_price_history(ticker)
        if history is None:
            continue
        save_price_history(history, ticker, data_dir)
        results[ticker] = history
        print_success(f"{ticker}: downloaded {len(history)} rows "
                       f"({history.index[0].date()} to {history.index[-1].date()})")
    return results
