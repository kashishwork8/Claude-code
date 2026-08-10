"""
Lightweight charting tool that plots the historical closing price of any
Yahoo Finance ticker (stocks, ETFs, indices, forex, commodities, crypto, etc.)
using yfinance and matplotlib. Plots close price only - no indicators.
"""

import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

# Timeframes supported by the tool, mapped to yfinance's `period` parameter.
VALID_TIMEFRAMES = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]


def get_user_input():
    """Prompt the user for a ticker symbol and a timeframe, and return them."""
    ticker = input("Enter ticker symbol (e.g. AAPL, BTC-USD, EURUSD=X): ").strip().upper()

    timeframe = ""
    while timeframe not in VALID_TIMEFRAMES:
        timeframe = input(
            f"Enter timeframe ({', '.join(VALID_TIMEFRAMES)}): "
        ).strip().lower()
        if timeframe not in VALID_TIMEFRAMES:
            print(f"Invalid timeframe. Choose one of: {', '.join(VALID_TIMEFRAMES)}")

    return ticker, timeframe


def fetch_price_data(ticker, timeframe):
    """Download historical price data for the given ticker and period."""
    # multi_level_index=False keeps columns flat (e.g. "Close") even though
    # only one ticker is requested.
    data = yf.download(ticker, period=timeframe, progress=False, multi_level_index=False)
    return data


def _month_tick_label(x, _pos=None):
    """Format an x-axis tick as the month abbreviation, or the year at
    each January tick (mirrors TradingView-style date axes)."""
    date = mdates.num2date(x)
    return date.strftime("%Y") if date.month == 1 else date.strftime("%b")


def plot_close_price(data, ticker, timeframe):
    """Plot the Close price series on a white background with a black line."""
    fig, ax = plt.subplots(facecolor="white")
    ax.set_facecolor("white")

    ax.plot(data.index, data["Close"], color="black", linewidth=2)

    ax.set_title(f"{ticker} Price Chart ({timeframe})")

    # Price axis on the right, matching TradingView-style charts.
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.set_ylabel("Price")

    # X-axis ticked by month, with the year shown at each January.
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=6, maxticks=12))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_month_tick_label))
    ax.set_xlabel("Date")

    # Minimal border, similar to TradingView's chart frame.
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_visible(False)

    # Source attribution, bottom-left of the figure.
    fig.text(0.01, 0.01, "Source: Yahoo Finance", fontsize=8, color="gray")

    plt.tight_layout()
    plt.show()


def main():
    """Entry point: collect input, fetch data, validate, and plot."""
    ticker, timeframe = get_user_input()

    data = fetch_price_data(ticker, timeframe)

    # Validate that data was returned before attempting to plot.
    if data.empty or "Close" not in data.columns:
        print("No data found for the selected ticker or timeframe.")
        return

    plot_close_price(data, ticker, timeframe)


if __name__ == "__main__":
    main()
