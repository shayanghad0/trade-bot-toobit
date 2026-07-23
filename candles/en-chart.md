# Chart Color Guide

## Candle Colors

| Color | Meaning |
|-------|---------|
| 🟢 Green (`#3fb950`) | Bullish candle (close > open) |
| 🔴 Red (`#f85149`) | Bearish candle (close < open) |

---

## SuperTrend Colors

| Color | Line | Meaning |
|-------|------|---------|
| 🟢 Solid Green | ST 1 | Uptrend (multiplier 1.0) |
| 🔴 Solid Red | ST 1 | Downtrend (multiplier 1.0) |
| 🟢 Dashed Green | ST 2 | Uptrend (multiplier 2.0) |
| 🔴 Dashed Red | ST 2 | Downtrend (multiplier 2.0) |
| 🟢 Dotted Green | ST 3 | Uptrend (multiplier 3.0) |
| 🔴 Dotted Red | ST 3 | Downtrend (multiplier 3.0) |

### How to Read SuperTrend
- **Green** line = **Uptrend** → Buy opportunity
- **Red** line = **Downtrend** → Sell opportunity
- When lines **change color** = Trend reversal occurred

---

## Pivot Point Colors

| Color | Marker | Meaning |
|-------|--------|---------|
| 🔵 Blue (`#58a6ff`) | Dashed line | Pivot High (resistance) |
| 🟠 Orange (`#d29922`) | Dashed line | Pivot Low (support) |
| 🔴 Red | ▼ | Pivot High |
| 🟢 Green | ▲ | Pivot Low |

### How to Read Pivot Points
- **Blue** line = Previous resistance level (price may drop)
- **Orange** line = Previous support level (price may rise)
- When price **breaks above blue** = Buy signal
- When price **breaks below orange** = Sell signal

---

## Smart Money Colors

### BOS (Break of Structure)

| Label Color | Meaning |
|-------------|---------|
| 🔵 Blue (`#58a6ff`) | Bullish BOS (resistance break) |
| 🔴 Red (`#f85149`) | Bearish BOS (support break) |

### CHoCH (Change of Character)

| Label Color | Meaning |
|-------------|---------|
| 🟢 Teal (`#39d353`) | Bullish CHoCH (downtrend → uptrend) |
| 🟠 Orange (`#d29922`) | Bearish CHoCH (uptrend → downtrend) |

### Order Blocks

| Color | Meaning |
|-------|---------|
| 🔵 Blue (`#58a6ff`) | Bullish order block (buy zone) |
| 🔴 Red (`#f85149`) | Bearish order block (sell zone) |

### Fair Value Gaps (FVG)

| Color | Meaning |
|-------|---------|
| 🟢 Teal (`#00d4aa`) | Bullish FVG (upward price gap) |
| 🔴 Red (`#f85149`) | Bearish FVG (downward price gap) |

### How to Read Smart Money
- **[BOS]** = Break of Structure → Trend continuation
- **[CHoCH]** = Change of Character → Trend reversal
- **Blue zone** = Where buyers entered → Watch for price pullback
- **Red zone** = Where sellers entered → Watch for price drop
- **Teal zone** = Bullish price gap → Price may go up

---

## RSI (Relative Strength Index)

| Value | Status | Color | Meaning |
|-------|--------|-------|---------|
| Above 70 | Overbought | 🔴 Red | Price is too high → Likely to drop |
| Between 30-70 | Neutral | 🟠 Orange | Market is normal |
| Below 30 | Oversold | 🟢 Green | Price is too low → Likely to rise |

### How to Read RSI
- RSI **above 70** = Market is **overbought** → Likely to drop
- RSI **below 30** = Market is **oversold** → Likely to rise
- RSI **crosses below 70** = Sell signal
- RSI **crosses above 30** = Buy signal

---

## Chart Panels

| Panel | Content | Description |
|-------|---------|-------------|
| Top (Panel 0) | Candles + Indicators | Main price chart |
| Middle (Panel 1) | Volume | Buy and sell volume |
| Bottom (Panel 2) | RSI | Relative strength of buyers vs sellers |

---

## Info Table (Top-Left)

```
ST 1 : ▲ BULL    → First SuperTrend is bullish
ST 2 : ▼ BEAR    → Second SuperTrend is bearish
ST 3 : ▲ BULL    → Third SuperTrend is bullish
```

---

## Quick Signal Guide

| Signal | Condition | Action |
|--------|-----------|--------|
| Strong Buy | Green ST + RSI below 30 + Bullish CHoCH | Buy |
| Medium Buy | Green ST + Price above Pivot Low | Buy with caution |
| Strong Sell | Red ST + RSI above 70 + Bearish CHoCH | Sell |
| Medium Sell | Red ST + Price below Pivot High | Sell with caution |
| Neutral | Mixed ST + RSI between 30-70 | Wait |
