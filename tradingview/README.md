# CFI WTI 1H · RSI(5) Candlestick Reversal (Pine Script v6)

Two TradingView scripts:

| File | Type | Purpose |
|---|---|---|
| `wti_rsi5_reversal_indicator.pine` | `indicator()` | Chart markers, labels, pattern boxes, info panel, `alertcondition()` + `alert()` alerts |
| `wti_rsi5_reversal_strategy.pine` | `strategy()` | Same signals, plus orders, stops/targets, sizing, date window, statistics tables |

Both files contain the same **SHARED SIGNAL ENGINE** block (`src/core.pine`). `src/build.sh`
concatenates `*_head.pine + core.pine + *_tail.pine`, so the indicator and the strategy give the same
signals. If you edit the engine, edit `src/core.pine` and run `src/build.sh`. Don't edit only one of
the generated files.

> The scripts were statically reviewed and syntax-parsed, but they have **not** been compiled in
> TradingView by the author. Paste them into the Pine Editor, which is the only authoritative compiler.

---

## 1. Architecture

```
Chart OHLC (CFI WTI, 1H) ──► base series (body, wicks, range, ATR, avg body, RSI, EMA)
                              │
                              ├─► trend context (price action, optional EMA), shifted to the
                              │    candle BEFORE each pattern's first candle
                              ├─► RSI events (reading or fresh cross) + lookback window + episodes
                              ├─► 26 pattern detectors (13 bullish, 13 bearish), each switchable
                              └─► doji state machine (setup on doji ► confirm/expire on later candle)
                                        │
                     priority + de-duplication + conflict rule + barstate.isconfirmed
                                        │
                     buySignal / sellSignal ──► markers, labels, boxes, alerts
                                                └─► (strategy) entry, stop, target, statistics
```

Implementation decisions:

* **Closed candles only.** Final signals are ANDed with `barstate.isconfirmed`. On historical bars
  this is always true. On the live bar it only becomes true on the last tick of the hour. `var`
  state is rolled back between real-time ticks, so intrabar values can't leak into the doji state.
* **No `request.security()`** and no `lookahead`. Every value comes from the current or earlier candles.
* **The signal is drawn on the candle where it becomes known.** Nothing is drawn on an earlier
  candle. The optional pattern box spans the pattern's candles, but it is created on the
  confirmation candle and is only a visual aid.
* **No divisions** in the pattern geometry. All ratio rules are written as multiplications
  (e.g. `loWick >= 2 * body`), so zero-range and zero-body candles can't cause division by zero.
  Zero-range candles (`high == low`) never match any pattern.

### Pine Script limitations that shape the design

| Topic | Limitation | How it is handled |
|---|---|---|
| Email | Pine can't send email. TradingView sends notifications for **alerts you create**, depending on your plan and alert settings. | The script provides `alertcondition()` and `alert()`. You enable "Send email" in the alert dialog. |
| `alertcondition()` text | The message must be a constant string, so it can't contain the pattern name. Placeholders such as `{{ticker}}` and `{{plot("RSI value")}}` work. | For full messages (pattern name, RSI, close, close time), create the alert with **"Any alert() function call"**. |
| `alertcondition()` in strategies | Not available in strategies. | The strategy uses `alert()` only. Use the indicator for alerts. |
| Shared code | Code can only be shared through a published library. | The engine is duplicated byte-for-byte via `src/build.sh`. |
| Commission, slippage, initial capital | `strategy()` arguments must be constants, so inputs can't set them. | Defaults are set in the declaration. Change them in **Settings → Properties**. |
| Fill price | Market orders are filled at the **next** bar's open (+ slippage) by the broker emulator, not at the signal close. Spread isn't modelled. | Documented. Slippage approximates spread. The R:R target is optionally re-anchored to the real fill. |
| Intrabar path | On historical bars the emulator assumes an intrabar path from OHLC. If stop and target are both inside one bar, the result is an assumption. | Use *Bar Magnifier* (Properties, plan-dependent) to use lower-TF data. |
| Per-pattern stats | Not built-in. | Computed from `strategy.closedtrades.*` using the entry comment (= pattern name). |

---

## 2. Rules in detail

### RSI
* `RSI = ta.rsi(source, 5)`, OS = 20, OB = 80 (all inputs).
* **Event definition** (input):
  * *Threshold reading* (default): every completed bar with `RSI <= 20` (`>= 80`) is an event.
  * *Fresh cross*: only the bar where `RSI <= 20` and the previous `RSI > 20` (mirror for 80).
* **Lookback** (default 3): the event may be on the pattern-completion candle or up to 3 completed
  candles before it (`ta.barssince(event) <= 3`). *Same candle* mode uses window 0.
  For dojis, the check is made **on the doji candle**, not the confirmation candle.
* RSI does **not** have to come back above 20 / below 80 unless you tick the optional exit filter.

### Trend (price action, lookback N = 3)
* Downtrend at bar *t*: `close[t] < close[t-N]` **and** `lowest(low, N)[t] < low[t-N]` (a lower low).
* Uptrend at bar *t*: `close[t] > close[t-N]` **and** `highest(high, N)[t] > high[t-N]` (a higher high).
* Optional EMA filter (off by default): a downtrend also needs `close < EMA(50)`, an uptrend `close > EMA(50)`.
* The trend is measured on the candle **just before the pattern's first candle**.
* Hammer, hanging man, shooting star, inverted hammer and dojis **always** need the prior trend,
  because it is part of their definition. "Require prior trend for every pattern" (default on) adds
  the requirement to all the others. Turning it off gives more signals of lower quality. Turning on
  the EMA filter gives fewer signals that are more often counter to a longer-term move that is
  already weakening. Measure both in the Strategy Tester.

### Pattern table

Notation for candle *i* (0 = latest closed candle, 1 = previous, …):
`range = H−L`, `body = |C−O|`, `upper = H − max(O,C)`, `lower = min(O,C) − L`,
bull = `C > O`, bear = `C < O`, `mid = (O+C)/2`, `avgBody = SMA(body,14)`,
long body = `body ≥ 1.0·avgBody`, small body = `body ≤ 0.5·avgBody`,
doji = `range > 0 and body ≤ 10%·range`. All numbers are inputs.

| # | Pattern | Candles | Rule (defaults) | Trend |
|---|---|---|---|---|
| B1 | Hammer | 1 | not doji; `lower ≥ 2·body`; `upper ≤ 0.5·body` | Downtrend (always) |
| B2 | Dragonfly doji | 1 + confirm | doji; `upper ≤ 10%·range`; `lower ≥ 60%·range` | Downtrend (always) |
| B3 | Standard doji (bull) | 1 + confirm | doji and neither dragonfly nor gravestone | Downtrend (always) |
| B4 | Bullish engulfing | 2 | `bear[1]`, `bull[0]`, `O0 ≤ C1`, `C0 ≥ O1`, `body0 > body1` | Optional |
| B5 | Tweezer bottom | 2 | `bear[1]`, `bull[0]`, `|L0 − L1| ≤ tol`; tol = `0.05·ATR(14)` or `5·mintick` | Optional |
| B6 | Morning star | 3 | `bear[2]` long; `[1]` small with `max(O1,C1) ≤ mid2`; `bull[0]`, `body0 > body1`, `C0 ≥ mid2` | Optional |
| B7 | Piercing line | 2 | `bear[1]` long; `bull[0]`; `O0 ≤ C1`; `C0 ≥ C1 + 50%·body1`; `C0 < O1` | Optional |
| B8 | Bullish harami | 2 | `bear[1]` long; `bull[0]`; `max(O0,C0) ≤ O1`, `min(O0,C0) ≥ C1`; `body0 ≤ 0.5·body1` | Optional |
| B9 | Inverted hammer | 1 | not doji; `upper ≥ 2·body`; `lower ≤ 0.5·body` | Downtrend (always) |
| B10 | Three white soldiers | 3 | 3 bulls, each `body ≥ 50%·range`, `upper ≤ 30%·range`; rising closes; each open inside prior body | Optional |
| B11 | Bullish pin bar | 1 | not doji; `lower ≥ 66%·range`; `body ≤ 33%·range`; optional `L0 < L1` | Optional |
| B12 | Three inside up | 3 | bullish harami on [2],[1] and `bull[0]` with `C0 > O2` | Optional |
| B13 | Three outside up | 3 | bullish engulfing on [2],[1] and `bull[0]` with `C0 > C1` | Optional |
| S1 | Shooting star | 1 | inverted-hammer shape | Uptrend (always) |
| S2 | Gravestone doji | 1 + confirm | doji; `lower ≤ 10%·range`; `upper ≥ 60%·range` | Uptrend (always) |
| S3 | Standard doji (bear) | 1 + confirm | as B3 | Uptrend (always) |
| S4 | Bearish engulfing | 2 | `bull[1]`, `bear[0]`, `O0 ≥ C1`, `C0 ≤ O1`, `body0 > body1` | Optional |
| S5 | Tweezer top | 2 | `bull[1]`, `bear[0]`, `|H0 − H1| ≤ tol` | Optional |
| S6 | Evening star | 3 | `bull[2]` long; `[1]` small with `min(O1,C1) ≥ mid2`; `bear[0]`, `body0 > body1`, `C0 ≤ mid2` | Optional |
| S7 | Dark cloud cover | 2 | `bull[1]` long; `bear[0]`; `O0 ≥ C1`; `C0 ≤ C1 − 50%·body1`; `C0 > O1` | Optional |
| S8 | Bearish harami | 2 | `bull[1]` long; `bear[0]`; body inside body1; `body0 ≤ 0.5·body1` | Optional |
| S9 | Hanging man | 1 | hammer shape | Uptrend (always) |
| S10 | Three black crows | 3 | mirror of B10 (`lower ≤ 30%·range`, falling closes, opens inside prior body) | Optional |
| S11 | Bearish pin bar | 1 | not doji; `upper ≥ 66%·range`; `body ≤ 33%·range`; optional `H0 > H1` | Optional |
| S12 | Three inside down | 3 | bearish harami on [2],[1] and `bear[0]` with `C0 < O2` | Optional |
| S13 | Three outside down | 3 | bearish engulfing on [2],[1] and `bear[0]` with `C0 < C1` | Optional |

Approximations (on purpose):
* **Gaps.** The textbook morning/evening star and piercing/dark cloud need price gaps, which a 24-hour CFD
  almost never has. The rules use body-midpoint and `open ≤ prior close` conditions instead.
* **Doji vs other shapes.** The hammer family and pin bars exclude dojis. A doji candle can never
  trigger an immediate signal, including as the last candle of a 2- or 3-candle pattern. It can only
  start a doji setup.
* **Hammer vs pin bar.** Their rules overlap. When both match, the priority order below picks one name.
* **Hammer colour.** Hammer, hanging man and the other hammer-family shapes may close up or down;
  colour isn't required.

### Doji confirmation (state machine)
1. On a doji candle with the prior trend and the RSI condition (checked on the doji candle), a
   setup is stored: high, low, midpoint, name and RSI episode. **No signal on the doji.**
   A diamond marks the pending setup.
2. On each later closed candle:
   * **Confirm** (default): a bullish candle with `close > doji high` (SELL: a bearish candle with `close < doji low`).
     Alternatives: any colour beyond the high/low, or the signal colour beyond the doji midpoint.
   * **Cancel** if a candle closes beyond the opposite extreme (option), or when
     `bars since doji ≥ expiry` (default 1 = only the next candle may confirm).
3. A newer doji replaces an older pending setup. Confirmation is checked before new setups are
   registered.

### Signal resolution and duplicate prevention
* Priority within a direction: 3-candle > 2-candle > 1-candle patterns, in the order of the table above.
  If a doji confirmation and another pattern happen on the same candle, it is **one** signal and the label shows both names.
* Only one signal per direction per candle.
* **One signal per RSI episode** (default on): an episode starts when RSI enters the zone. After a
  BUY, the next BUY needs a new oversold episode. This stops a run of consecutive bullish candles
  inside one oversold dip from firing again and again.
* Optional cooldown in bars.
* BUY and SELL on the same candle: *Skip both* (default), *Prefer BUY* or *Prefer SELL*.

---

## 3. Strategy model

* Entry: market order at the signal candle's close. It fills at the **next candle's open** plus
  slippage (`process_orders_on_close = false`, `calc_on_every_tick = false`).
* Stop (default): beyond the pattern's extreme. For longs, the lowest low of all pattern candles
  (doji setups include the doji and the confirmation candle) minus `0.1·ATR(14)`. Shorts are the
  mirror. Alternative: `1.5·ATR` from the signal close.
* Target (default): `2.0 ×` the risk. On the signal bar the risk is measured from the signal close.
  From the next bar it is re-measured from the actual average fill price (option). The stop doesn't move.
  Alternatives: ATR target, or no target.
* Sizing: percent of equity (default 10% notional), fixed quantity, or risk % of equity divided by
  the stop distance. Quantities are rounded down to the step.
* Direction: long & short / long only / short only. By default only one position is open at a time.
  If you untick that, an opposite signal reverses the position (or only closes it when that direction is disabled).
* Optional date window for in-sample / out-of-sample tests. Positions still open at the window end are closed.
* Defaults: capital 10,000, commission 0%, slippage 3 ticks. **Set these to your CFI account's
  real values**: spread (approximated by slippage), any commission, and overnight financing.
  Financing (swap) isn't modelled by TradingView.
* Pine v6 defaults margin to 100% (no leverage). With *Risk %* sizing an order can need more than
  your equity. Adjust *Margin for long/short positions* in Properties if your CFD leverage allows it.

---

## 4. Installation (Pine Editor)

1. Open TradingView in a browser or the desktop app and log in.
2. **Find the CFI symbol.** Click the symbol search at the top left and type `WTI`, `USOIL` or
   `US Oil`. Look at the source/exchange column for **CFI** (the broker name/logo). Choose the
   spot/CFD listing, not NYMEX `CL1!`. The symbol is shown as `PREFIX:TICKER`. That prefix is
   what the script checks in its info panel. If it isn't `CFI`, change the *Expected broker
   prefix* input to the prefix you see (this check is a warning only). If you trade through CFI's
   TradingView broker connection, open the chart from that connection so you see your broker's prices.
3. Set the chart timeframe to **1 hour** (`1h` in the interval menu).
4. Open **Pine Editor** (bottom panel, or the `{}`/"Pine" icon in the left or bottom toolbar).
5. Click the script-name dropdown/menu → **Create new → Indicator**. Select everything in the editor
   and delete it.
6. Copy the whole content of `wti_rsi5_reversal_indicator.pine` and paste it.
7. Click **Save** (or Ctrl/Cmd+S) and give it a name.
8. Click **Add to chart**. Markers appear on candles that qualified in history. Check the info panel (top right).
9. Repeat steps 5–8 with **Create new → Strategy** and `wti_rsi5_reversal_strategy.pine`.
   You can keep both on the chart, or hide one with the eye icon.
10. Settings: hover over the script name on the chart → ⚙ (gear). The **Inputs** tab has groups 1–12.
    The **Properties** tab (strategy) has capital, order size, commission, slippage, margin and
    Bar Magnifier. Note that the script's own *Position sizing* input sets the size of every order.
11. Optional: add TradingView's built-in **Relative Strength Index** with Length 5 and levels
    20/80 to see RSI in its own pane. The script plots on the price chart.

## 5. Email alerts

Use the **indicator** for alerts. It must be on the chart and on the 1H timeframe.

**Option A – full message with the pattern name (recommended)**
1. Click **Alert** (clock icon in the top toolbar), or press Alt+A.
2. *Condition*: choose `WTI RSI5 Reversal` → **Any alert() function call**.
3. *Trigger/frequency*: this is set by the script (`once per bar close`).
4. *Expiration*: set as long as your plan allows, or open-ended if available.
5. *Notifications* tab: tick **Send email** (and app/pop-up if wanted). The email goes to the
   address of your TradingView account.
6. *Message*: leave it as is. The script supplies the text, for example
   `BUY | CFI:WTI | TF 60 | RSI(5) 18.42 | Pattern: Hammer | Close 71.23 | Candle close 2026-10-23 15:00 Europe/London`.
7. Click **Create**. To get BUY only, untick *Send SELL via alert()* in Inputs → group 9 before
   creating the alert (and vice versa).

**Option B – separate BUY / SELL / combined conditions**
1. *Condition*: `WTI RSI5 Reversal` → **WTI RSI5 - BUY** (or **- SELL**, or **- BUY or SELL**).
2. *Trigger*: **Once Per Bar Close**. This is required, otherwise TradingView may evaluate the
   condition intrabar. The script also gates it with `barstate.isconfirmed`.
3. Tick **Send email**, then click **Create**. The message includes ticker, interval, RSI (via `{{plot("RSI value")}}`),
   close and bar **open** time (`{{time}}`, UTC). It doesn't include the pattern name.

Notes: an alert stores the script settings that were active when you created it. **Re-create the alert after
changing inputs**. Email delivery depends on your TradingView plan, alert limits, the email address and spam
filters. Pine itself sends nothing.

## 6. Strategy Tester

1. Add the strategy to the CFI WTI 1H chart.
2. Open **Strategy Tester** (bottom panel tab).
3. **Overview**: net profit, max drawdown, the equity curve and a summary.
4. **Performance Summary** (or *Metrics*, depending on the UI version): net profit (and %),
   gross profit/loss, profit factor, total closed trades, winning/losing trades, percent profitable,
   average trade, average winning/losing trade, max drawdown. Each has **All / Long / Short** columns.
5. **List of Trades**: every trade. The entry signal text is the pattern name, exits are `SL`/`TP`.
6. On the chart: the *summary table* (bottom left) and the *per-pattern table* (bottom right),
   both net of commission and slippage.
7. Use the date-range selector in the Strategy Tester, or Inputs → group 12, to test periods separately.
   The amount of 1H history you can see depends on your plan and the data feed.

### Suggested testing process
1. **In-sample**: choose a window (e.g. the oldest ~60–70% of the available history). Tune only a
   few inputs (RSI thresholds, lookback, trend filter on/off, stop/target).
2. **Out-of-sample**: freeze the settings, then run only on the later 30–40%. Accept the settings
   only if the results there are still acceptable.
3. **Walk-forward**: repeat with rolling windows.
4. **Regimes**: compare trending vs ranging periods and high vs low volatility (e.g. 2020, 2022 and quieter years).
5. **Cost stress**: double the slippage and add commission. Check that the edge survives.
6. Look for a reasonable sample size (dozens of trades per pattern before you trust its row).
   Avoid enabling only the patterns that looked best in-sample.

### Repainting and fill realism
* Signals use only closed candles, and history and real-time behave the same. On a live chart, a
  marker appears only after the hourly candle closes.
* Strategy orders fill at the next open. With a 24-hour CFD the next open is usually close to the
  signal close, but not around session breaks or weekends.
* Historical data has no tick-by-tick spread. Slippage in ticks is a fixed approximation, and the
  spread on WTI CFDs widens around news (EIA inventories, OPEC), rollovers and illiquid hours.
* Stop/target ordering inside one candle is assumed from OHLC unless you enable Bar Magnifier.
* CFI's spot/CFD prices, sessions and hourly candle boundaries may differ from NYMEX futures
  (`CL1!`). The CFI feed you chart is what determines the signals. The script contains no
  futures-expiry logic. Ask CFI whether its "spot" WTI price is derived from a futures contract
  with rolls, because a roll can show up as a price jump.

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| Compilation error | Make sure the first line is `//@version=6` and that the **whole** file was pasted (indentation matters; tabs pasted as 4 spaces are fine). The error panel shows the line number. Report that line. |
| "Script could not be translated" after editing | Check that continuation lines are not indented by a multiple of 4 spaces, and that every `if` block is indented by exactly 4 spaces. |
| No markers at all | Info panel: is the timeframe 1H? (signals are off on other timeframes unless you untick the restriction). "warming up" = not enough bars. Try lowering *RSI lookback* restrictions or enabling more patterns. With *One signal per episode* plus *Fresh cross* there will be fewer signals. |
| Prefix warning | Your symbol prefix differs from the *Expected broker prefix* input. Choose the CFI listing, or change/clear the input. |
| Alert never fires | Created on the wrong timeframe/symbol, created before changing inputs, expired, or a BUY/SELL toggle in group 9 is off (Option A). |
| Alerts fire too often / intrabar | For `alertcondition` alerts choose **Once Per Bar Close**. |
| No email | Tick "Send email" in Notifications. Verify your email in TradingView settings and check spam. Plan limits apply. |
| Strategy shows 0 trades | The sizing quantity rounds to 0 (raise *Percent of equity* / *Fixed quantity*, or lower *Quantity rounding step*), margin is too low, or the date window excludes the data. |
| Strategy results differ from the indicator markers | Signals are identical, but trades are skipped while a position is open (one-at-a-time), outside the date window, or for a disabled direction. |
| Too many labels | Only the latest 500 labels/boxes are kept. Older markers (plotshape) remain. |

## 8. Validation checklist

| Requirement | Status |
|---|---|
| Pine v6, single-file indicator and strategy | Implemented (not compiled by the author. Compile in TradingView) |
| RSI(5), OS 20, OB 80, source close, configurable | Implemented |
| RSI lookback, reading vs fresh cross, same-candle vs window | Implemented |
| Optional "RSI back inside band" filter | Implemented (off by default) |
| 11 + extra bullish and bearish patterns, individually switchable | Implemented (13 per side) |
| Objective rules, zero-range/zero-body safe | Implemented (no divisions) |
| Gapped patterns (stars, piercing/dark cloud) | **Approximation** (no-gap variants for a 24h CFD) |
| Trend: price action N = 3, optional EMA | Implemented |
| Doji confirmation, expiry, cancellation, no signal on doji | Implemented |
| Non-repainting, closed candles, no lookahead | Implemented (`barstate.isconfirmed`, no `request.security`) |
| Duplicate / conflict handling | Implemented (priority, episode, cooldown, conflict rule) |
| Markers, labels, pattern name, RSI value, highlighting, trend display, TF warning | Implemented |
| BUY / SELL / combined alerts | Implemented |
| Pattern name in `alertcondition()` message | **Not supported by Pine** (const message). Available via `alert()` |
| Email sending from Pine | **Not supported**. TradingView sends email for alerts you create |
| Strategy: capital, commission, slippage as script inputs | **Pine limitation**. Set in the Properties tab |
| Sizing, SL, TP, R:R, direction, one position | Implemented |
| Built-in stats incl. long/short | Strategy Tester (native) + on-chart table |
| Per-pattern stats | Implemented (on-chart table, derived from closed trades) |
| Spread, swap/financing, tick-accurate fills | **Not modelled natively**. Slippage approximates spread |
| CFI symbol auto-detection | Not possible. You choose the symbol, and the script warns on a prefix mismatch |
