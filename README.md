# IB Trade History

Pulls trade/execution history from Interactive Brokers TWS using `ib_insync`.

## Setup

1. In TWS: File > Global Configuration > API > Settings > enable "Enable ActiveX and Socket Clients", and confirm the socket port (paper trading default is `7497`).
2. `pip install -r requirements.txt`

## Usage

```bash
python ib_trade_history.py --host 127.0.0.1 --port 7497 --client-id 1
```

Optionally save to CSV:

```bash
python ib_trade_history.py --csv trades.csv
```

Note: `IB.reqExecutions()` returns fills TWS still holds in memory for the
current session/day. For older history, use the TWS/IB Gateway "Flex Query"
reports or the `reqExecutions` with an `ExecutionFilter` for historical dates
supported by your account type.

## Portfolio tracking spreadsheet

`scripts/reconstruct_daily_data.py` and `scripts/build_portfolio.py` build
`output/My_Portfolio_BUILT.xlsx`, a formula-driven portfolio tracker.

- `data/raw/` holds raw pulls from the IBKR account (positions, trades,
  performance/NAV history, daily price history) plus `reference_data.json`
  (sector/industry/country per holding).
- `scripts/reconstruct_daily_data.py` turns those into `data/processed/*.csv`:
  a daily shares-held matrix, daily market data, and a daily cash/NAV series
  reconciled against the live account.
- `scripts/build_portfolio.py` reads only those processed files (no network
  calls) and writes the workbook: Data Lake sheets (Trade_Log, Market_Data,
  Reference_Data, Daily_Units, Daily_Cash) hold plain values; every Analytics
  sheet (Dashboard, Positions, Equity_Curve, Sector_Exposure,
  Geographic_Exposure) is 100% Excel formulas referencing the data lakes.

Known limitations (see the build's inline docstrings for detail):
- `get_account_trades` only exposes rolling windows, not arbitrary date
  ranges, so a handful of older fills fall outside every window queryable;
  any such gap is folded into day 1 so current shares/values still tie out
  exactly to the live account.
- Positions that were fully closed out during the year are valued at their
  last transacted price between trades (not a daily market mark), since no
  free daily-price API was reachable from this environment for closed names.
- `Beta` in `Reference_Data` is left blank rather than estimated, since no
  live fundamentals API was reachable when this was built.

Re-run `python3 scripts/reconstruct_daily_data.py && python3
scripts/build_portfolio.py` after refreshing `data/raw/` to rebuild.
