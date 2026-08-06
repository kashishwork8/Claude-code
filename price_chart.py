"""
Lightweight charting tool that plots the historical closing price of any
Yahoo Finance ticker (stocks, ETFs, indices, forex, commodities, crypto, etc.)
using yfinance and matplotlib. Plots close price only - no indicators.
"""

import yfinance as yf
import matplotlib.pyplot as plt

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


def plot_close_price(data, ticker, timeframe):
    """Plot the Close price series on a white background with a black line."""
    fig, ax = plt.subplots(facecolor="white")
    ax.set_facecolor("white")

    ax.plot(data.index, data["Close"], color="black", linewidth=2)

    ax.set_title(f"{ticker} Price Chart ({timeframe})")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")

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
