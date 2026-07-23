# Price Fetcher & Decoder

Fetch kline (candlestick) data from Toobit exchange and decode it into usable format for the SMA 20 Trading Bot.

## Files

| File | Description |
|------|-------------|
| `price.py` | Fetches raw kline data from Toobit API |
| `decode.py` | Decodes raw JSON into labeled candle objects |

## Workflow

```
price.py → {iranian-date}.json → decode.py → candles.json → SMA 20 Bot
```

## Usage

### Step 1: Fetch Data

```bash
python price.py
```

You will be prompted for:
- **Coin symbol** — e.g. `BTCUSDT`, `ETHUSDT`, `SOLUSDT`
- **Timeframe** — e.g. `1m`, `5m`, `15m`, `1h`, `4h`
- **Candle limit** — e.g. `100`, `150`, `500`

Output: `{iranian-date}.json` (raw kline data)

### Step 2: Decode Data

```bash
python decode.py
```

- Auto-detects the JSON file in current directory
- If multiple files found, lets you choose
- Can also pass filename as argument: `python decode.py 1404-04-01.json`

Output: `candles.json` (decoded candle data)

### Step 3: Run Bot

```bash
python ../"bot/sma 20/main.py" candles.json
```

## Requirements

- Python 3.8+
- `jdatetime` — `pip install jdatetime`
- `toobit` CLI — Must be installed and in PATH

## Kline Fields

Each decoded candle contains:

| Field | Description |
|-------|-------------|
| `open_time` | Candle open timestamp (ms) |
| `open` | Open price |
| `high` | Highest price |
| `low` | Lowest price |
| `close` | Close price |
| `volume` | Base asset volume |
| `quote_volume` | Quote asset volume |
| `trades` | Number of trades |
| `taker_buy_volume` | Taker buy volume |
| `taker_buy_quote_volume` | Taker buy quote volume |
