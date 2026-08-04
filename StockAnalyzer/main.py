#!/usr/bin/env python3
"""StockAnalyzer — command-line stock analysis tool.

Downloads historical price data for user-specified tickers, computes
technical indicators and performance metrics, detects Golden/Death Cross
signals, renders per-stock charts, and produces a consolidated Excel
report.

Usage:
    python main.py --tickers MSFT NVDA AAPL META GOOGL AMZN
    python main.py --tickers MSFT,NVDA,AAPL
    python main.py                      # falls back to an interactive prompt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.data_loader import download_all, download_price_history
from src.indicators import add_indicators
from src.performance import calculate_metrics, rank_by_total_return
from src.plotting import plot_stock_chart
from src.signals import detect_crosses, latest_cross_status
from src.utils import (
    build_daily_returns_frame,
    ensure_directories,
    format_percent,
    generate_excel_report,
    parse_ticker_input,
    print_error,
    print_header,
    print_subheader,
    print_success,
    print_warning,
    validate_tickers,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHARTS_DIR = BASE_DIR / "charts"
REPORTS_DIR = BASE_DIR / "reports"
REPORT_FILENAME = "Stock_Analysis_Report.xlsx"
BENCHMARK_TICKER = "SPY"


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Define and parse command-line arguments.

    ``--tickers`` accepts either space-separated symbols or a single
    comma-separated string (or a mix of both), so all of the following are
    equivalent:

        --tickers MSFT NVDA AAPL
        --tickers MSFT,NVDA,AAPL
        --tickers "MSFT, NVDA" AAPL
    """
    parser = argparse.ArgumentParser(
        description="Download stock data and generate technical/performance analysis.",
        epilog=(
            "Examples:\n"
            "  python main.py --tickers MSFT NVDA AAPL META GOOGL AMZN\n"
            "  python main.py --tickers MSFT,NVDA,AAPL\n"
            "  python main.py                       # interactive prompt"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="Stock tickers to analyze, space- and/or comma-separated (e.g. MSFT NVDA AAPL).",
    )
    return parser.parse_args(argv)


def resolve_tickers(cli_tickers: list[str] | None) -> list[str]:
    """Get the final ticker list from CLI args, falling back to a prompt."""
    if cli_tickers:
        raw = ",".join(cli_tickers)
    else:
        raw = input("Enter tickers separated by commas:\n\n")
    return parse_ticker_input(raw)


def build_summary_row(
    ticker: str,
    dataframe: pd.DataFrame,
    metrics: dict,
) -> dict:
    """Assemble one row of the Summary worksheet / console table."""
    golden_status, death_status = latest_cross_status(dataframe)
    latest = dataframe.iloc[-1]
    return {
        "Ticker": ticker,
        "Start Date": dataframe.index[0].date(),
        "End Date": dataframe.index[-1].date(),
        "Total Return": metrics["total_return_pct"] / 100,
        "Annual Return": metrics["annualized_return_pct"] / 100,
        "Maximum Drawdown": metrics["max_drawdown_pct"] / 100,
        "Beta": round(metrics["beta"], 3) if metrics["beta"] is not None else "N/A",
        "Latest Close": round(float(latest["Close"]), 2),
        "50 MA": round(float(latest["MA50"]), 2) if pd.notna(latest["MA50"]) else "N/A",
        "200 MA": round(float(latest["MA200"]), 2) if pd.notna(latest["MA200"]) else "N/A",
        "Golden Cross Status": golden_status,
        "Death Cross Status": death_status,
    }


def print_summary_table(summary_rows: list[dict]) -> None:
    """Print a fixed-width console table summarizing every analyzed stock."""
    header = f"{'Ticker':<8}{'Total Ret':>12}{'Annual Ret':>13}{'Max DD':>10}{'Beta':>8}"
    print(header)
    print("-" * len(header))
    for row in summary_rows:
        beta_display = f"{row['Beta']:.2f}" if isinstance(row["Beta"], (int, float)) else row["Beta"]
        print(
            f"{row['Ticker']:<8}"
            f"{format_percent(row['Total Return'] * 100):>12}"
            f"{format_percent(row['Annual Return'] * 100):>13}"
            f"{format_percent(row['Maximum Drawdown'] * 100):>10}"
            f"{beta_display:>8}"
        )


def main(argv: list[str] | None = None) -> int:
    """Run the full StockAnalyzer pipeline end to end."""
    ensure_directories(DATA_DIR, CHARTS_DIR, REPORTS_DIR)

    args = parse_arguments(argv)
    requested_tickers = resolve_tickers(args.tickers)

    if not requested_tickers:
        print_error("No tickers provided. Exiting.")
        return 1

    valid_tickers, invalid_tickers = validate_tickers(requested_tickers)
    for bad_ticker in invalid_tickers:
        print_warning(f"'{bad_ticker}' does not look like a valid ticker symbol and will be skipped.")

    if not valid_tickers:
        print_error("No valid tickers to analyze. Exiting.")
        return 1

    print_header("Downloading Historical Data")
    price_histories = download_all(valid_tickers, DATA_DIR)
    if not price_histories:
        print_error("No data could be downloaded for any requested ticker. Exiting.")
        return 1

    print_subheader("Benchmark (for Beta calculation)")
    benchmark_history = download_price_history(BENCHMARK_TICKER)
    benchmark_returns = None
    if benchmark_history is not None:
        benchmark_returns = add_indicators(benchmark_history)["Daily_Return"]
        print_success(f"{BENCHMARK_TICKER}: downloaded {len(benchmark_history)} rows for beta comparison")
    else:
        print_warning("Could not download SPY; Beta will be reported as N/A for all stocks.")

    print_header("Running Technical & Performance Analysis")
    summary_rows: list[dict] = []
    all_signals: list[dict] = []
    daily_returns_by_ticker: dict[str, pd.Series] = {}

    for ticker, raw_history in price_histories.items():
        print_subheader(ticker)
        try:
            enriched = add_indicators(raw_history)
            signals = detect_crosses(enriched, ticker)
            metrics = calculate_metrics(enriched, benchmark_returns)

            summary_rows.append(build_summary_row(ticker, enriched, metrics))
            all_signals.extend(signals)
            daily_returns_by_ticker[ticker] = enriched["Daily_Return"]

            chart_path = plot_stock_chart(enriched, ticker, signals, CHARTS_DIR)
            print_success(f"Indicators computed, {len(signals)} cross signal(s) found")
            print_success(f"Chart saved to {chart_path.relative_to(BASE_DIR)}")
        except Exception as exc:
            print_error(f"{ticker}: analysis failed ({exc}); skipping this ticker.")
            continue

    if not summary_rows:
        print_error("Analysis produced no results for any ticker. Exiting.")
        return 1

    print_header("Summary")
    print_summary_table(summary_rows)

    best_ticker_row = max(summary_rows, key=lambda row: row["Total Return"])
    print_header("Best Performing Stock")
    print(f"Ticker:         {best_ticker_row['Ticker']}")
    print(f"Total Return:   {format_percent(best_ticker_row['Total Return'] * 100)}")
    print(f"Annual Return:  {format_percent(best_ticker_row['Annual Return'] * 100)}")
    print(f"Max Drawdown:   {format_percent(best_ticker_row['Maximum Drawdown'] * 100)}")
    beta_value = best_ticker_row["Beta"]
    print(f"Beta:           {beta_value if isinstance(beta_value, str) else f'{beta_value:.3f}'}")

    print_header("Generating Excel Report")
    summary_df = pd.DataFrame(summary_rows)
    signals_df = pd.DataFrame(all_signals) if all_signals else pd.DataFrame(
        columns=["Ticker", "Date", "Signal", "Price"]
    )
    daily_returns_df = build_daily_returns_frame(daily_returns_by_ticker)

    report_path = REPORTS_DIR / REPORT_FILENAME
    generate_excel_report(report_path, summary_df, signals_df, daily_returns_df)
    print_success(f"Excel report saved to {report_path.relative_to(BASE_DIR)}")

    print_header("Files Saved")
    print(f"Price data:    {DATA_DIR.relative_to(BASE_DIR)}/<TICKER>.csv")
    print(f"Charts:        {CHARTS_DIR.relative_to(BASE_DIR)}/<TICKER>_chart.png")
    print(f"Excel report:  {report_path.relative_to(BASE_DIR)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
