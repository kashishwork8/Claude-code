# StockAnalyzer

A professional, reusable Python tool for downloading historical stock data
and running technical and performance analysis on any set of tickers.

## Overview

StockAnalyzer pulls maximum-available daily price history from Yahoo
Finance (via `yfinance`), computes moving averages and Golden/Death Cross
signals, evaluates return/risk/beta metrics against the S&P 500 (SPY), and
outputs professional charts plus a multi-sheet Excel report — all from a
single command.

The codebase is organized into small, single-responsibility modules under
`src/` so new indicators, metrics, or interfaces (e.g. a dashboard) can be
added without touching the rest of the pipeline.

## Features

- **No hardcoded tickers** — analyze any stocks via CLI flags or an
  interactive prompt.
- **Full price history** — downloads the maximum available daily history
  with split/dividend-adjusted prices.
- **Technical indicators** — daily returns, 50-day MA, 200-day MA via
  vectorized pandas rolling windows.
- **Golden/Death Cross detection** — every crossover event is logged with
  its date, type, and price, and marked on the chart with a clearly
  visible arrow.
- **Performance analytics** — total return, annualized return (CAGR),
  maximum drawdown, and beta vs. SPY (computed automatically even though
  SPY isn't shown as a comparison stock).
- **Best-performer ranking** — ranks all analyzed stocks by total return.
- **Professional charts** — one PNG per stock with price, both moving
  averages, and cross-signal arrows, saved to `charts/`.
- **Excel report** — a formatted `Stock_Analysis_Report.xlsx` with
  `Summary`, `Signals`, and `Daily Returns` worksheets (bold headers,
  auto-sized columns, percentage formatting).
- **Resilient by design** — invalid tickers, missing data, download
  failures, and insufficient history are logged as warnings/errors and
  skipped; one bad symbol never stops the batch.
- **Command-line first** — driven by `argparse` for easy automation and
  scheduling, with an interactive fallback when no flags are given.

## Installation

```bash
git clone <this-repository>
cd StockAnalyzer
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Requirements

- Python 3.10+
- `yfinance`, `pandas`, `numpy`, `matplotlib`, `scipy`, `openpyxl`
  (see `requirements.txt` for pinned minimum versions)
- Internet access (data is pulled live from Yahoo Finance)

## How to Run

**Command-line arguments (recommended — scriptable/automatable):**

```bash
python main.py --tickers MSFT NVDA AAPL META GOOGL AMZN
python main.py --tickers MSFT,NVDA,AAPL
```

**Interactive mode** (no arguments):

```bash
python main.py
```

```
Enter tickers separated by commas:

MSFT,NVDA,AAPL,META,GOOGL,AMZN
```

## Example Output

```
================================================================
                 Downloading Historical Data
================================================================
[OK] MSFT: downloaded 10231 rows (1986-03-13 to 2026-08-03)
[OK] NVDA: downloaded 6801 rows (1999-01-22 to 2026-08-03)

--- Benchmark (for Beta calculation) ---
[OK] SPY: downloaded 8321 rows for beta comparison

================================================================
              Running Technical & Performance Analysis
================================================================
--- MSFT ---
[OK] Indicators computed, 14 cross signal(s) found
[OK] Chart saved to charts/MSFT_chart.png

================================================================
                          Summary
================================================================
Ticker   Total Ret   Annual Ret   Max DD    Beta
------------------------------------------------
MSFT       412.85%       18.22%  -37.15%    0.91
NVDA      2841.60%       36.44%  -66.34%    1.68

================================================================
                    Best Performing Stock
================================================================
Ticker:         NVDA
Total Return:   2841.60%
Annual Return:  36.44%
Max Drawdown:   -66.34%
Beta:           1.680

================================================================
                    Generating Excel Report
================================================================
[OK] Excel report saved to reports/Stock_Analysis_Report.xlsx

================================================================
                        Files Saved
================================================================
Price data:    data/<TICKER>.csv
Charts:        charts/<TICKER>_chart.png
Excel report:  reports/Stock_Analysis_Report.xlsx
```

## Folder Structure

```
StockAnalyzer/
│
├── data/                 # Downloaded price history (CSV per ticker)
├── charts/               # Generated PNG charts (one per ticker)
├── reports/              # Stock_Analysis_Report.xlsx
│
├── src/
│   ├── data_loader.py    # yfinance downloading & CSV persistence
│   ├── indicators.py     # Daily returns, 50/200-day moving averages
│   ├── performance.py    # Total/annual return, max drawdown, beta
│   ├── plotting.py       # Matplotlib chart generation
│   ├── signals.py        # Golden/Death Cross detection
│   └── utils.py          # Validation, console output, Excel formatting
│
├── main.py               # CLI entry point (argparse + orchestration)
├── requirements.txt
├── README.md
└── .gitignore
```

## Screenshots

_Add example chart and Excel report screenshots here after running the tool, e.g.:_

```
charts/MSFT_chart.png
```

## Future Improvements

The architecture is intentionally modular so the following can be added
without major refactoring:

- RSI and MACD indicators (`src/indicators.py`)
- Multi-stock portfolio analysis (weighted returns, correlation matrix)
- Strategy backtesting engine
- Options analytics (implied volatility, Greeks)
- Interactive Streamlit dashboard on top of the existing `src/` modules

## License

For educational and personal research use.
