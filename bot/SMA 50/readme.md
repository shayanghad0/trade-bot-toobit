# SMA 50 Trading Bot v2.0

Full analysis engine for Spot and Futures (Long/Short) trading signals with 27 analysis modules.

## Quick Start

```bash
python main.py <path_to_candles.json>
```

Example:
```bash
python main.py ../../candles/candles.json
```

## Requirements

```bash
pip install numpy pandas matplotlib mplfinance jdatetime
```

## Output Files

| File | Description |
|------|-------------|
| `sma50_analysis_*.png` | All-in-one chart (SMC + Trade Plan + all analysis data) |
| `sma50_report_*.pdf` | Multi-page PDF report |
| `sma50_complete_*.txt` | Full text report |
| `sma50_data_*.json` | JSON data export |

## Analysis Modules (27 Sections)

### Core Analysis
| # | Module | Description |
|---|--------|-------------|
| 1 | Data Models | Enums, dataclasses, type definitions |
| 2 | Candle Loading | JSON parsing, sequence validation |
| 3 | Technical Indicators | SMA, RSI, MACD, BB, ATR, ADX, CCI, MFI, Stoch, VWAP |
| 4 | Trend Analysis | SMA50 slope, trend direction, strength |
| 5 | Support/Resistance | Dynamic S/R levels, pivot points |
| 6 | Pattern Recognition | Candlestick patterns (engulfing, hammer, doji, etc.) |
| 7 | Volume Analysis | Volume ratio, buy pressure, divergence |
| 8 | Signal Generation | Core BUY/SELL/HOLD signal with confidence |

### Enhanced Analysis
| # | Module | Description |
|---|--------|-------------|
| 9 | Report Generator | Formatted text report |
| 11 | Multi-Timeframe | 1H, 4H, 1D alignment |
| 12 | Fibonacci/Elliott | Fib levels, wave patterns |
| 13 | Volatility Metrics | HV, Sharpe, Sortino, MaxDD, VaR |
| 14 | Market Structure | Order flow, efficiency, activity |
| 15 | Regime Detection | CALM TREND, BB squeeze, trend regime |
| 16 | Advanced Patterns | Chart patterns, divergences |
| 17 | Confidence Scoring | Multi-factor score (0-115) |
| 18 | Enhanced Generator | Combined analysis engine |

### Trading Tools
| # | Module | Description |
|---|--------|-------------|
| 21 | Backtesting | SMA50 strategy backtest, win rate, Sharpe |
| 22 | Alert System | Real-time notifications |
| 24 | Data Export | JSON serialization, quick summary |
| 25 | Chart + PDF | All-in-one PNG and PDF generation |
| 26 | PDF Generator | Multi-page PDF report |

## Signal Types

| Signal | Meaning |
|--------|---------|
| STRONG BUY | High confidence buy |
| BUY | Standard buy |
| HOLD | No action (wait) |
| SELL | Standard sell |
| STRONG SELL | High confidence sell |

## Confidence Score

Scored 0-115 based on:
- Trend Strength (0-10)
- Market Phase (0-10)
- Indicator Alignment (0-10)
- Timeframe Alignment (0-10)
- Market Regime (0-10)
- Fibonacci Position (0-5)
- Wave Structure (0-10)
- Order Flow (0-5)
- Risk Metrics (0-5)

## Chart Features

### Left Panel — SMC Chart
- Triple Supertrend (multipliers 1.0, 2.0, 3.0)
- BOS / CHoCH labels
- Order Blocks (blue/red zones)
- Fair Value Gaps (teal/red zones)
- Pivot high/low markers
- Volume bars
- RSI sub-panel

### Right Panel — Trade Plan
- Last 10 candles zoomed
- Entry / SL / TP1 / TP2 / TP3 lines
- Support / Resistance levels
- BUY/SELL badge
- Trade details box

### Data Sections
- Technical Indicators (17 values)
- Support / Resistance (R1-R5, S1-S5)
- Signal Reasons (color-coded)
- Confidence Score (factor breakdown)
- Multi-Timeframe (1H, 4H, 1D)
- Fibonacci Levels
- Volatility & Risk
- Market Regime
- Backtest Results
- Risk Management Guidelines
