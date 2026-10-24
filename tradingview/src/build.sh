#!/bin/sh
# Assembles the two TradingView scripts so the shared engine stays identical.
cd "$(dirname "$0")"
cat indicator_head.pine core.pine indicator_tail.pine > ../wti_rsi5_reversal_indicator.pine
cat strategy_head.pine core.pine strategy_tail.pine > ../wti_rsi5_reversal_strategy.pine
