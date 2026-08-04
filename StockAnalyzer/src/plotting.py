"""Chart generation for individual stocks using matplotlib.

Each chart shows the closing price, both moving averages, and clearly
visible arrow annotations marking every Golden Cross / Death Cross event.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from src.signals import DEATH_CROSS, GOLDEN_CROSS, CrossSignal

matplotlib.use("Agg")  # Render to file only; no GUI backend required.

GOLDEN_COLOR = "#1E8F4E"
DEATH_COLOR = "#C0392B"


def _annotate_signal(ax: plt.Axes, signal: CrossSignal) -> None:
    """Draw a single up/down arrow annotation for one cross signal."""
    is_golden = signal["Signal"] == GOLDEN_CROSS
    color = GOLDEN_COLOR if is_golden else DEATH_COLOR
    # Golden crosses get an arrow rising from below the price; death
    # crosses get an arrow descending from above, so they never overlap
    # the price line itself.
    y_offset = -40 if is_golden else 40
    ax.annotate(
        "",
        xy=(signal["Date"], signal["Price"]),
        xytext=(0, y_offset),
        textcoords="offset points",
        arrowprops=dict(facecolor=color, edgecolor=color, width=3, headwidth=10, headlength=10, shrink=0.05),
    )


def plot_stock_chart(
    dataframe: pd.DataFrame,
    ticker: str,
    signals: list[CrossSignal],
    charts_dir: Path,
) -> Path:
    """Render and save a professional price/MA chart with cross markers.

    Args:
        dataframe: Price history containing ``Close``, ``MA50``, ``MA200``.
        ticker: Ticker symbol, used for the title and output filename.
        signals: Golden/Death cross events for this ticker.
        charts_dir: Directory the PNG chart is saved into.

    Returns:
        Path to the saved chart image.
    """
    plt.style.use("seaborn-v0_8-darkgrid")
    fig, ax = plt.subplots(figsize=(14, 7), dpi=150)

    ax.plot(dataframe.index, dataframe["Close"], label="Close Price", color="#2C3E50", linewidth=1.4)
    ax.plot(dataframe.index, dataframe["MA50"], label="50-Day MA", color="#2980B9", linewidth=1.2)
    ax.plot(dataframe.index, dataframe["MA200"], label="200-Day MA", color="#E67E22", linewidth=1.2)

    for signal in signals:
        _annotate_signal(ax, signal)

    # Add invisible scatter points solely so Golden/Death Cross appear in
    # the legend (arrows themselves cannot carry a legend label).
    if any(s["Signal"] == GOLDEN_CROSS for s in signals):
        ax.scatter([], [], marker="^", color=GOLDEN_COLOR, s=100, label="Golden Cross")
    if any(s["Signal"] == DEATH_CROSS for s in signals):
        ax.scatter([], [], marker="v", color=DEATH_COLOR, s=100, label="Death Cross")

    ax.set_title(f"{ticker} — Price, Moving Averages & Cross Signals", fontsize=15, fontweight="bold")
    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("Price (USD)", fontsize=11)
    ax.legend(loc="upper left", frameon=True, fontsize=10)
    ax.grid(True, alpha=0.3)

    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    fig.autofmt_xdate()

    fig.tight_layout()
    output_path = charts_dir / f"{ticker}_chart.png"
    fig.savefig(output_path)
    plt.close(fig)
    return output_path
