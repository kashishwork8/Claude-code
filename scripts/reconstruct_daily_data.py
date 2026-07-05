"""Reconstruct Daily_Units, Market_Data, and Daily_Cash from raw IBKR pulls.

Reads data/raw/*.json (trades, positions, NAV performance series, price history)
and writes data/processed/*.csv consumed by build_portfolio.py.

Closed positions (names no longer held) have real daily prices only for the
window IBKR's ONE_YEAR history reachable for the 18 current holdings; for the
64 tickers that were bought and fully sold within the year, no live/free daily
price API was reachable in this sandbox, so their value is carried at their
last transacted price between trades (a disclosed approximation) rather than
marked-to-market daily. Total NAV and Cash always use IBKR's own reported
performance series, so the equity curve's headline numbers stay authoritative
regardless of that approximation.
"""
import json
import os
from datetime import datetime, timezone

import pandas as pd

RAW = "data/raw"
OUT = "data/processed"
os.makedirs(OUT, exist_ok=True)

CURRENT_TICKERS = ["CGNX", "COPX", "DRAM", "DTC", "EMAAR", "EMIRATESN", "FPS", "GDXJ",
                   "HOOD", "ONDS", "RBRK", "RDDT", "SALIK", "SILJ", "STM", "URNM", "VSH", "WOLF"]
AED_TICKERS = {"DTC", "EMAAR", "EMIRATESN", "SALIK"}

# ---- NAV / master calendar from IBKR performance API (authoritative) ----
perf = json.load(open(f"{RAW}/get_pa_performance_all_periods.json"))
oneY = perf["accounts"]["account"]["periods"]["1Y"]
nav_dates = [datetime.strptime(d, "%Y%m%d").date().isoformat() for d in oneY["dates"]]
nav_values = oneY["nav"]
nav_series = pd.Series(nav_values, index=pd.to_datetime(nav_dates)).sort_index()
nav_series = nav_series[~nav_series.index.duplicated(keep="last")]
master_dates = nav_series.index

print("Master calendar:", master_dates[0].date(), "->", master_dates[-1].date(), f"({len(master_dates)} days)")

# ---- Trades ----
trades = json.load(open(f"{RAW}/trades_combined.json"))
stk_trades = [t for t in trades if t["sec_type"] == "STK"]
df_trades = pd.DataFrame(stk_trades)
df_trades["trade_date"] = pd.to_datetime(df_trades["trade_time"]).dt.tz_localize(None).dt.normalize()
df_trades["signed_size"] = df_trades.apply(lambda r: r["size"] if r["side"] == "BUY" else -r["size"], axis=1)

all_symbols = sorted(df_trades["symbol"].unique())
print("Total STK symbols in trade log:", len(all_symbols))

# ---- Daily Units (all symbols ever traded) ----
units = pd.DataFrame(index=master_dates, columns=all_symbols, dtype=float)
for sym in all_symbols:
    sub = df_trades[df_trades["symbol"] == sym].groupby("trade_date")["signed_size"].sum().sort_index()
    cum = sub.cumsum()
    # reindex onto master calendar, forward filling between trade days, 0 before first trade
    s = cum.reindex(master_dates.union(cum.index)).sort_index()
    s = s.ffill().fillna(0.0)
    s = s.reindex(master_dates)
    units[sym] = s.values

units.index.name = "date"

# ---- Reconcile against live positions (get_account_trades only exposes rolling
# windows, not arbitrary date ranges, so a handful of older fills can fall
# outside every window we can query; without that gap, reconstructed shares
# would silently drift from the real account). Any gap is folded into day 1
# so today's Positions/Dashboard always tie out exactly to the live account. ----
live_positions = json.load(open(f"{RAW}/get_account_positions.json"))["positions"]
live_map = {p["contract_description"].split(" @")[0]: p["position"] for p in live_positions}
for sym in all_symbols:
    real = live_map.get(sym, 0.0)  # tickers absent from live positions are fully closed -> 0
    computed = units[sym].iloc[-1]
    gap = real - computed
    if abs(gap) > 1e-6:
        print(f"Reconciling {sym}: computed {computed} vs live {real}, folding gap {gap} into day 1")
        units[sym] = units[sym] + gap

units.to_csv(f"{OUT}/daily_units.csv")
print("daily_units.csv written:", units.shape)

# ---- Market data: real daily closes for the 18 current holdings + FX ----
market = pd.DataFrame(index=master_dates, columns=CURRENT_TICKERS, dtype=float)
for sym in CURRENT_TICKERS:
    data = json.load(open(f"{RAW}/prices/{sym}.json"))
    idx = pd.to_datetime([t[:10] for t in data["time"]])
    s = pd.Series(data["close"], index=idx).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s = s.reindex(master_dates.union(s.index)).sort_index().ffill().bfill()
    s = s.reindex(master_dates)
    market[sym] = s.values

fx_data = json.load(open(f"{RAW}/prices/USD_AED_FX.json"))
fx_idx = pd.to_datetime([t[:10] for t in fx_data["time"]])
fx_series = pd.Series(fx_data["close"], index=fx_idx).sort_index()
fx_series = fx_series[~fx_series.index.duplicated(keep="last")]
fx_series = fx_series.reindex(master_dates.union(fx_series.index)).sort_index().ffill().bfill().reindex(master_dates)
market["USD_AED"] = fx_series.values

market.index.name = "date"
market.to_csv(f"{OUT}/market_data.csv")
print("market_data.csv written:", market.shape)

# ---- Approximate price series for closed-out tickers (held at last transacted price) ----
closed_symbols = [s for s in all_symbols if s not in CURRENT_TICKERS]
closed_price = pd.DataFrame(index=master_dates, columns=closed_symbols, dtype=float)
for sym in closed_symbols:
    sub = df_trades[df_trades["symbol"] == sym].groupby("trade_date")["price"].last().sort_index()
    s = sub.reindex(master_dates.union(sub.index)).sort_index().ffill()
    s = s.reindex(master_dates)
    closed_price[sym] = s.values
closed_price = closed_price.fillna(0.0)

# ---- Invested value per day (USD), combining real marks + approximated closed marks ----
invested = pd.Series(0.0, index=master_dates)
for sym in CURRENT_TICKERS:
    px = market[sym]
    if sym in AED_TICKERS:
        px = px / market["USD_AED"]
    invested = invested + units[sym].fillna(0.0) * px
for sym in closed_symbols:
    invested = invested + units[sym].fillna(0.0) * closed_price[sym]

daily_cash = pd.DataFrame({
    "date": master_dates,
    "nav": nav_series.reindex(master_dates).values,
    "invested_value": invested.values,
})
daily_cash["cash"] = daily_cash["nav"] - daily_cash["invested_value"]
daily_cash.to_csv(f"{OUT}/daily_cash.csv", index=False)
print("daily_cash.csv written:", daily_cash.shape)
print(daily_cash.tail())
