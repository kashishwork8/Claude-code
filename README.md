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
