"""Connect to Interactive Brokers TWS via ib_insync and pull trade history.

Requires TWS or IB Gateway running with API access enabled
(File > Global Configuration > API > Settings > Enable ActiveX and Socket Clients).

Usage:
    python ib_trade_history.py
"""
import argparse
import sys

import pandas as pd
from ib_insync import IB


def connect(host: str, port: int, client_id: int) -> IB:
    ib = IB()
    ib.connect(host, port, clientId=client_id)
    return ib


def fetch_trade_history(ib: IB) -> pd.DataFrame:
    """Pull executed fills for the current session/account.

    ib.reqExecutions() with no filter returns fills from the current
    trading day that TWS still has in memory.
    """
    fills = ib.reqExecutions()

    rows = []
    for fill in fills:
        contract = fill.contract
        execution = fill.execution
        commission = fill.commissionReport
        rows.append({
            "time": execution.time,
            "symbol": contract.symbol,
            "secType": contract.secType,
            "exchange": execution.exchange,
            "side": execution.side,
            "shares": execution.shares,
            "price": execution.price,
            "avgPrice": execution.avgPrice,
            "orderId": execution.orderId,
            "execId": execution.execId,
            "commission": commission.commission if commission else None,
            "realizedPNL": commission.realizedPNL if commission else None,
        })

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Pull IB trade history via ib_insync")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7497)
    parser.add_argument("--client-id", type=int, default=1)
    parser.add_argument("--csv", default=None, help="optional path to save results as CSV")
    args = parser.parse_args()

    ib = connect(args.host, args.port, args.client_id)
    try:
        df = fetch_trade_history(ib)
    finally:
        ib.disconnect()

    if df.empty:
        print("No trade history found for the current session.")
        return

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    print(df)

    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"\nSaved {len(df)} rows to {args.csv}")


if __name__ == "__main__":
    main()
