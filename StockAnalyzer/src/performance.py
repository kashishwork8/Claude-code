"""Performance and risk metrics: returns, drawdown, and beta.

Every function here operates on plain pandas Series/DataFrames so the
metrics can be reused outside the CLI (e.g. in a future Streamlit
dashboard or backtesting engine) without modification.
"""

from __future__ import annotations

from typing import TypedDict

import numpy as np
import pandas as pd
from scipy import stats

TRADING_DAYS_PER_YEAR = 252


class PerformanceMetrics(TypedDict):
    """Container for a single stock's summary performance metrics."""

    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    beta: float | None


def calculate_total_return(close_prices: pd.Series) -> float:
    """Return the total percentage return between the first and last price."""
    first_price, last_price = close_prices.iloc[0], close_prices.iloc[-1]
    return float((last_price / first_price - 1) * 100)


def calculate_annualized_return(close_prices: pd.Series) -> float:
    """Return the CAGR (annualized return) as a percentage.

    Uses the actual elapsed calendar time between the first and last
    observation, so it remains accurate even with gaps in the data.
    """
    first_price, last_price = close_prices.iloc[0], close_prices.iloc[-1]
    num_days = (close_prices.index[-1] - close_prices.index[0]).days
    years = num_days / 365.25
    if years <= 0 or first_price <= 0:
        return 0.0
    cagr = (last_price / first_price) ** (1 / years) - 1
    return float(cagr * 100)


def calculate_max_drawdown(close_prices: pd.Series) -> float:
    """Return the maximum peak-to-trough decline as a negative percentage."""
    cumulative = close_prices / close_prices.iloc[0]
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return float(drawdown.min() * 100)


def calculate_beta(stock_returns: pd.Series, market_returns: pd.Series) -> float | None:
    """Return the beta of a stock relative to a market benchmark (e.g. SPY).

    Daily returns are aligned by date (inner join) before the covariance /
    variance calculation, so mismatched trading calendars don't bias the
    result.

    Returns:
        Beta as a float, or ``None`` if there is not enough overlapping
        history to compute a meaningful value.
    """
    aligned = pd.concat(
        [stock_returns.rename("stock"), market_returns.rename("market")], axis=1, join="inner"
    ).dropna()
    if len(aligned) < 30 or np.isclose(aligned["market"].var(ddof=1), 0):
        return None
    # Beta is the slope of the linear regression of stock returns on
    # market returns.
    regression = stats.linregress(aligned["market"], aligned["stock"])
    return float(regression.slope)


def calculate_metrics(dataframe: pd.DataFrame, market_returns: pd.Series | None) -> PerformanceMetrics:
    """Compute the full set of summary performance metrics for one stock.

    Args:
        dataframe: Price history containing at least a ``Close`` column.
        market_returns: Daily returns of the benchmark (SPY) used for beta,
            or ``None`` to skip the beta calculation (e.g. when SPY itself
            failed to download).
    """
    close = dataframe["Close"]
    beta = None
    if market_returns is not None and "Daily_Return" in dataframe:
        beta = calculate_beta(dataframe["Daily_Return"], market_returns)

    return {
        "total_return_pct": calculate_total_return(close),
        "annualized_return_pct": calculate_annualized_return(close),
        "max_drawdown_pct": calculate_max_drawdown(close),
        "beta": beta,
    }


def rank_by_total_return(metrics_by_ticker: dict[str, PerformanceMetrics]) -> list[tuple[str, PerformanceMetrics]]:
    """Return ``(ticker, metrics)`` pairs sorted best-to-worst by total return."""
    return sorted(metrics_by_ticker.items(), key=lambda item: item[1]["total_return_pct"], reverse=True)
