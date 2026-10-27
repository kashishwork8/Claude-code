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

---

# WTI RSI(5) Pullback Strategy (TradingView / Pine Script)

`wti_rsi_pullback_strategy.pine` is a Pine Script v6 strategy for backtesting on
TradingView. Intended for the `USOIL` CFD on the **1 hour** chart, trading all hours.

## How to use

1. Open TradingView, chart `USOIL`, timeframe 1H.
2. Open the Pine Editor, paste the contents of the `.pine` file, click **Add to chart**.
3. Read results in the **Strategy Tester** tab.

## Rules

**Trend confirmation (EMA 50 on the chart's own candles = 50 hours on 1H)**

- Uptrend: 3 consecutive closes, each above the EMA 50 and above the previous candle's high.
- Downtrend: 3 consecutive closes, each below the EMA 50 and below the previous candle's low.
- Once confirmed, the trend stays in force until the opposite 3-close pattern confirms a flip.
- No confirmed trend means no trades.

**Entries (signal on a completed candle, fill at the next candle's open)**

- Long (uptrend only): RSI(5) reaches or falls below 30 during a pullback, then crosses back above 30.
- Short (downtrend only): RSI(5) reaches or rises above 70 during a rally, then crosses back below 70.
- The trend must hold on both the extreme-RSI candle and the entry candle.
- Only one position at a time. Never long in a downtrend, never short in an uptrend.

**Exits and sizing**

- Take profit: $2.00 price move from the fill price.
- Stop loss: $2.00 price move from the fill price.
- Position size: about $10,000 notional per trade (fractional units, suited to CFDs, not futures).
- Commission and slippage are set to zero by default.

## Inputs

EMA length, RSI length, closes needed to confirm trend, RSI oversold/overbought
levels, take profit and stop loss in dollars, and toggles to enable longs/shorts.

## Caveats

- If a candle touches both the take profit and the stop loss, TradingView assumes the stop was hit first.
- Backtest results are not a prediction of live performance. Add your broker's spread and fees before drawing conclusions.
