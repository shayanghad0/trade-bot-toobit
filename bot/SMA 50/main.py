#!/usr/bin/env python3
"""
SMA 50 Trading Bot - Trend Direction & Dynamic Support/Resistance
================================================================
Full analysis engine for Spot and Futures (Long/Short) trading signals.

Features:
  - SMA 50 trend direction analysis
  - Dynamic support/resistance levels
  - Multi-timeframe confirmation
  - Volume analysis and divergence detection
  - RSI, MACD, Bollinger Bands integration
  - Candlestick pattern recognition
  - Risk management and position sizing
  - Detailed reasoning output for every signal
  - Spot buy/sell and Futures long/short recommendations

Usage:
  python main.py <path_to_candles.json>

Author: Toobit Trading Engine
Version: 2.0
"""

import json
import sys
import os
import math
import warnings
warnings.filterwarnings("ignore")
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics
import io

try:
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    import matplotlib.patches as mpatches
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.ticker import FuncFormatter
    import matplotlib.patheffects as pe
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("[WARNING] matplotlib/numpy/pandas not installed. Chart export disabled.")
    print("  Install: pip install matplotlib numpy pandas")

try:
    import mplfinance as mpf
    HAS_MPLFINANCE = True
except ImportError:
    HAS_MPLFINANCE = False

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "font.size": 10,
    "font.family": "Vazirmatn",
    "figure.facecolor": "#0d1117",
    "axes.facecolor": "#0d1117",
    "savefig.facecolor": "#0d1117",
})

COLORS = {
    "bg": "#0d1117",
    "bg2": "#161b22",
    "bg3": "#1c2333",
    "grid": "#21262d",
    "text": "#c9d1d9",
    "text_dim": "#8b949e",
    "green": "#3fb950",
    "green_dim": "#238636",
    "red": "#f85149",
    "red_dim": "#da3633",
    "blue": "#58a6ff",
    "orange": "#d29922",
    "purple": "#bc8cff",
    "teal": "#39d353",
    "cyan": "#00d4aa",
    "yellow": "#e3b341",
    "pink": "#f778ba",
    "white": "#f0f6fc",
}


# ============================================================================
# SECTION 1: DATA MODELS AND ENUMS
# ============================================================================

class SignalType(Enum):
    STRONG_BUY = "STRONG BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG SELL"


class TrendDirection(Enum):
    STRONG_UP = "STRONG UPTREND"
    UP = "UPTREND"
    SIDEWAYS = "SIDEWAYS"
    DOWN = "DOWNTREND"
    STRONG_DOWN = "STRONG DOWNTREND"


class MarketPhase(Enum):
    ACCUMULATION = "ACCUMULATION"
    MARKUP = "MARKUP"
    DISTRIBUTION = "DISTRIBUTION"
    MARKDOWN = "MARKDOWN"
    SIDEWAYS = "SIDEWAYS"


class CandlePattern(Enum):
    DOJI = "DOJI"
    HAMMER = "HAMMER"
    INVERTED_HAMMER = "INVERTED HAMMER"
    ENGULFING_BULLISH = "BULLISH ENGULFING"
    ENGULFING_BEARISH = "BEARISH ENGULFING"
    MORNING_STAR = "MORNING STAR"
    EVENING_STAR = "EVENING STAR"
    THREE_WHITE_SOLDIERS = "THREE WHITE SOLDIERS"
    THREE_BLACK_CROWS = "THREE BLACK CROWS"
    HARAMI_BULLISH = "BULLISH HARAMI"
    HARAMI_BEARISH = "BEARISH HARAMI"
    PIERCING_LINE = "PIERCING LINE"
    DARK_CLOUD_COVER = "DARK CLOUD COVER"
    SHOOTING_STAR = "SHOOTING STAR"
    HANGING_MAN = "HANGING MAN"
    SPINNING_TOP = "SPINNING TOP"
    NONE = "NONE"


@dataclass
class Candle:
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    trades: int
    taker_buy_volume: float
    taker_buy_quote_volume: float

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def upper_shadow(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_shadow(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def total_range(self) -> float:
        return self.high - self.low

    @property
    def body_to_range_ratio(self) -> float:
        if self.total_range == 0:
            return 0
        return self.body_size / self.total_range

    @property
    def buy_pressure(self) -> float:
        total_vol = self.taker_buy_volume + (self.volume - self.taker_buy_volume)
        if total_vol == 0:
            return 0.5
        return self.taker_buy_volume / total_vol

    @property
    def timestamp(self) -> datetime:
        return datetime.fromtimestamp(self.open_time / 1000, tz=timezone.utc)


@dataclass
class IndicatorValues:
    sma50: float = 0.0
    sma50_prev: float = 0.0
    sma50_prev2: float = 0.0
    ema12: float = 0.0
    ema26: float = 0.0
    macd_line: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    macd_histogram_prev: float = 0.0
    rsi: float = 50.0
    rsi_prev: float = 50.0
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    bb_width: float = 0.0
    atr: float = 0.0
    atr_percent: float = 0.0
    obv: float = 0.0
    obv_sma: float = 0.0
    volume_sma: float = 0.0
    stoch_k: float = 50.0
    stoch_d: float = 50.0
    vwap: float = 0.0
    momentum: float = 0.0
    roc: float = 0.0
    adx: float = 0.0
    plus_di: float = 0.0
    minus_di: float = 0.0
    cci: float = 0.0
    mfi: float = 50.0
    williams_r: float = -50.0


@dataclass
class SupportResistance:
    levels: List[float] = field(default_factory=list)
    types: List[str] = field(default_factory=list)
    strength: List[float] = field(default_factory=list)
    touches: List[int] = field(default_factory=list)


@dataclass
class SignalResult:
    signal_type: SignalType = SignalType.HOLD
    confidence: float = 0.0
    spot_action: str = "HOLD"
    futures_action: str = "HOLD"
    leverage_suggestion: str = "None"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit_1: float = 0.0
    take_profit_2: float = 0.0
    take_profit_3: float = 0.0
    risk_reward_ratio: float = 0.0
    position_size_pct: float = 0.0
    trend_direction: TrendDirection = TrendDirection.SIDEWAYS
    market_phase: MarketPhase = MarketPhase.SIDEWAYS
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    indicators_summary: Dict[str, Any] = field(default_factory=dict)
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    patterns_detected: List[str] = field(default_factory=list)
    volume_analysis: str = ""
    risk_assessment: str = ""


# ============================================================================
# SECTION 2: CANDLE LOADING AND VALIDATION
# ============================================================================

def load_candles(file_path: str) -> List[Candle]:
    """Load and validate candle data from JSON file."""
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        sys.exit(1)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {file_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}")
        sys.exit(1)

    if not isinstance(raw_data, list):
        print(f"[ERROR] Expected JSON array, got {type(raw_data).__name__}")
        sys.exit(1)

    candles = []
    for i, item in enumerate(raw_data):
        try:
            candle = Candle(
                open_time=int(item['open_time']),
                open=float(item['open']),
                high=float(item['high']),
                low=float(item['low']),
                close=float(item['close']),
                volume=float(item['volume']),
                quote_volume=float(item.get('quote_volume', 0)),
                trades=int(item.get('trades', 0)),
                taker_buy_volume=float(item.get('taker_buy_volume', 0)),
                taker_buy_quote_volume=float(item.get('taker_buy_quote_volume', 0))
            )
            if candle.high < candle.low:
                print(f"[WARNING] Candle {i}: high < low, skipping")
                continue
            if candle.volume <= 0:
                print(f"[WARNING] Candle {i}: zero volume, using minimal")
                candle.volume = 0.0001
            candles.append(candle)
        except (KeyError, ValueError) as e:
            print(f"[WARNING] Candle {i}: parse error ({e}), skipping")
            continue

    if len(candles) < 30:
        print(f"[ERROR] Need at least 60 candles for SMA 50, got {len(candles)}")
        sys.exit(1)

    print(f"[INFO] Loaded {len(candles)} candles successfully")
    return candles


def validate_candle_sequence(candles: List[Candle]) -> bool:
    """Validate candle time sequence and data integrity."""
    issues = []
    for i in range(1, len(candles)):
        if candles[i].open_time <= candles[i-1].open_time:
            issues.append(f"Candle {i}: non-increasing timestamp")
        if candles[i].high > candles[i].high * 1.1:
            issues.append(f"Candle {i}: suspicious high value")
        if candles[i].low < 0:
            issues.append(f"Candle {i}: negative low value")
    if issues:
        print(f"[WARNING] Data quality issues: {len(issues)}")
        for issue in issues[:5]:
            print(f"  - {issue}")
    return len(issues) == 0


# ============================================================================
# SECTION 3: TECHNICAL INDICATOR CALCULATIONS
# ============================================================================

class TechnicalIndicators:
    """Comprehensive technical indicator calculation engine."""

    @staticmethod
    def sma(data: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average."""
        if len(data) < period:
            return [0.0] * len(data)
        result = [0.0] * (period - 1)
        window_sum = sum(data[:period])
        result.append(window_sum / period)
        for i in range(period, len(data)):
            window_sum += data[i] - data[i - period]
            result.append(window_sum / period)
        return result

    @staticmethod
    def ema(data: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average."""
        if len(data) < period:
            return [0.0] * len(data)
        multiplier = 2.0 / (period + 1)
        result = [0.0] * (period - 1)
        result.append(sum(data[:period]) / period)
        for i in range(period, len(data)):
            ema_val = (data[i] - result[-1]) * multiplier + result[-1]
            result.append(ema_val)
        return result

    @staticmethod
    def rsi(closes: List[float], period: int = 14) -> List[float]:
        """Calculate Relative Strength Index."""
        if len(closes) < period + 1:
            return [50.0] * len(closes)
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        result = [50.0] * period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100.0 - (100.0 / (1.0 + rs)))
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                result.append(100.0)
            else:
                rs = avg_gain / avg_loss
                result.append(100.0 - (100.0 / (1.0 + rs)))
        return result

    @staticmethod
    def macd(closes: List[float], fast: int = 12, slow: int = 26,
             signal: int = 9) -> Tuple[List[float], List[float], List[float]]:
        """Calculate MACD line, signal, and histogram."""
        ema_fast = TechnicalIndicators.ema(closes, fast)
        ema_slow = TechnicalIndicators.ema(closes, slow)
        macd_line = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
        valid_macd = [m for m in macd_line if m != 0]
        if len(valid_macd) >= signal:
            signal_line = TechnicalIndicators.ema(valid_macd, signal)
            padding = len(macd_line) - len(signal_line)
            signal_line = [0.0] * padding + signal_line
        else:
            signal_line = [0.0] * len(macd_line)
        histogram = [macd_line[i] - signal_line[i] for i in range(len(macd_line))]
        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger_bands(closes: List[float], period: int = 20,
                        std_dev: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
        """Calculate Bollinger Bands."""
        if len(closes) < period:
            return closes[:], closes[:], closes[:]
        sma_vals = TechnicalIndicators.sma(closes, period)
        upper = []
        lower = []
        for i in range(len(closes)):
            if i < period - 1:
                upper.append(closes[i])
                lower.append(closes[i])
            else:
                window = closes[i - period + 1:i + 1]
                std = statistics.stdev(window) if len(window) > 1 else 0
                upper.append(sma_vals[i] + std_dev * std)
                lower.append(sma_vals[i] - std_dev * std)
        return upper, sma_vals, lower

    @staticmethod
    def atr(candles: List[Candle], period: int = 14) -> List[float]:
        """Calculate Average True Range."""
        if len(candles) < 2:
            return [0.0] * len(candles)
        tr_values = [candles[0].total_range]
        for i in range(1, len(candles)):
            tr = max(
                candles[i].high - candles[i].low,
                abs(candles[i].high - candles[i-1].close),
                abs(candles[i].low - candles[i-1].close)
            )
            tr_values.append(tr)
        if len(tr_values) < period:
            return tr_values
        atr_values = [0.0] * (period - 1)
        atr_values.append(sum(tr_values[:period]) / period)
        for i in range(period, len(tr_values)):
            atr_val = (atr_values[-1] * (period - 1) + tr_values[i]) / period
            atr_values.append(atr_val)
        return atr_values

    @staticmethod
    def stochastic(candles: List[Candle], k_period: int = 14,
                   d_period: int = 3) -> Tuple[List[float], List[float]]:
        """Calculate Stochastic Oscillator."""
        k_values = []
        for i in range(len(candles)):
            if i < k_period - 1:
                k_values.append(50.0)
                continue
            window = candles[i - k_period + 1:i + 1]
            highest = max(c.high for c in window)
            lowest = min(c.low for c in window)
            if highest == lowest:
                k_values.append(50.0)
            else:
                k_values.append(((candles[i].close - lowest) / (highest - lowest)) * 100)
        d_values = TechnicalIndicators.sma(k_values, d_period)
        return k_values, d_values

    @staticmethod
    def obv(candles: List[Candle]) -> List[float]:
        """Calculate On-Balance Volume."""
        if not candles:
            return []
        obv_values = [0.0]
        for i in range(1, len(candles)):
            if candles[i].close > candles[i-1].close:
                obv_values.append(obv_values[-1] + candles[i].volume)
            elif candles[i].close < candles[i-1].close:
                obv_values.append(obv_values[-1] - candles[i].volume)
            else:
                obv_values.append(obv_values[-1])
        return obv_values

    @staticmethod
    def vwap(candles: List[Candle]) -> List[float]:
        """Calculate Volume Weighted Average Price."""
        if not candles:
            return []
        cumulative_volume = 0.0
        cumulative_tp_volume = 0.0
        vwap_values = []
        for c in candles:
            typical_price = (c.high + c.low + c.close) / 3.0
            cumulative_volume += c.volume
            cumulative_tp_volume += typical_price * c.volume
            if cumulative_volume > 0:
                vwap_values.append(cumulative_tp_volume / cumulative_volume)
            else:
                vwap_values.append(typical_price)
        return vwap_values

    @staticmethod
    def momentum(closes: List[float], period: int = 10) -> List[float]:
        """Calculate Momentum indicator."""
        result = [0.0] * period
        for i in range(period, len(closes)):
            result.append(closes[i] - closes[i - period])
        return result

    @staticmethod
    def rate_of_change(closes: List[float], period: int = 10) -> List[float]:
        """Calculate Rate of Change."""
        result = [0.0] * period
        for i in range(period, len(closes)):
            if closes[i - period] != 0:
                result.append(((closes[i] - closes[i - period]) / closes[i - period]) * 100)
            else:
                result.append(0.0)
        return result

    @staticmethod
    def adx(candles: List[Candle], period: int = 14) -> Tuple[List[float], List[float], List[float]]:
        """Calculate Average Directional Index with +DI and -DI."""
        if len(candles) < period + 1:
            return [25.0] * len(candles), [25.0] * len(candles), [25.0] * len(candles)
        plus_dm = [0.0]
        minus_dm = [0.0]
        tr_vals = [candles[0].total_range]
        for i in range(1, len(candles)):
            up_move = candles[i].high - candles[i-1].high
            down_move = candles[i-1].low - candles[i].low
            plus_dm.append(max(up_move, 0) if up_move > down_move else 0)
            minus_dm.append(max(down_move, 0) if down_move > up_move else 0)
            tr = max(
                candles[i].high - candles[i].low,
                abs(candles[i].high - candles[i-1].close),
                abs(candles[i].low - candles[i-1].close)
            )
            tr_vals.append(tr)
        atr_vals = TechnicalIndicators.atr(candles, period)
        plus_di = []
        minus_di = []
        adx_vals = []
        dx_vals = []
        for i in range(len(candles)):
            if i < period or atr_vals[i] == 0:
                plus_di.append(25.0)
                minus_di.append(25.0)
                adx_vals.append(25.0)
                dx_vals.append(0.0)
            else:
                pdi = (plus_dm[i] / atr_vals[i]) * 100
                mdi = (minus_dm[i] / atr_vals[i]) * 100
                plus_di.append(pdi)
                minus_di.append(mdi)
                if pdi + mdi == 0:
                    dx_vals.append(0.0)
                else:
                    dx_vals.append(abs(pdi - mdi) / (pdi + mdi) * 100)
        adx_sma = TechnicalIndicators.sma(dx_vals, period)
        return adx_sma, plus_di, minus_di

    @staticmethod
    def cci(candles: List[Candle], period: int = 20) -> List[float]:
        """Calculate Commodity Channel Index."""
        if len(candles) < period:
            return [0.0] * len(candles)
        result = []
        for i in range(len(candles)):
            if i < period - 1:
                result.append(0.0)
                continue
            window = candles[i - period + 1:i + 1]
            typical_prices = [(c.high + c.low + c.close) / 3.0 for c in window]
            mean_tp = sum(typical_prices) / period
            mean_dev = sum(abs(tp - mean_tp) for tp in typical_prices) / period
            current_tp = (candles[i].high + candles[i].low + candles[i].close) / 3.0
            if mean_dev == 0:
                result.append(0.0)
            else:
                result.append((current_tp - mean_tp) / (0.015 * mean_dev))
        return result

    @staticmethod
    def money_flow_index(candles: List[Candle], period: int = 14) -> List[float]:
        """Calculate Money Flow Index."""
        if len(candles) < period:
            return [50.0] * len(candles)
        result = [50.0] * (period - 1)
        for i in range(period - 1, len(candles)):
            window = candles[i - period + 1:i + 1]
            pos_mf = 0.0
            neg_mf = 0.0
            for j in range(len(window)):
                tp = (window[j].high + window[j].low + window[j].close) / 3.0
                mf = tp * window[j].volume
                if j > 0:
                    prev_tp = (window[j-1].high + window[j-1].low + window[j-1].close) / 3.0
                    if tp > prev_tp:
                        pos_mf += mf
                    elif tp < prev_tp:
                        neg_mf += mf
            if neg_mf == 0:
                result.append(100.0)
            else:
                mfr = pos_mf / neg_mf
                result.append(100.0 - (100.0 / (1.0 + mfr)))
        return result

    @staticmethod
    def williams_r(candles: List[Candle], period: int = 14) -> List[float]:
        """Calculate Williams %R."""
        if len(candles) < period:
            return [-50.0] * len(candles)
        result = []
        for i in range(len(candles)):
            if i < period - 1:
                result.append(-50.0)
                continue
            window = candles[i - period + 1:i + 1]
            highest = max(c.high for c in window)
            lowest = min(c.low for c in window)
            if highest == lowest:
                result.append(-50.0)
            else:
                result.append(((highest - candles[i].close) / (highest - lowest)) * -100)
        return result


# ============================================================================
# SECTION 4: TREND ANALYSIS ENGINE
# ============================================================================

class TrendAnalyzer:
    """Comprehensive trend direction and strength analysis."""

    @staticmethod
    def analyze_trend_direction(candles: List[Candle], indicators: IndicatorValues,
                                 sma50_values: List[float]) -> TrendDirection:
        """Determine overall trend direction using multiple factors."""
        score = 0
        max_score = 100

        current_price = candles[-1].close
        prev_price = candles[-2].close if len(candles) > 1 else current_price

        if current_price > indicators.sma50:
            score += 15
        else:
            score -= 15

        sma_slope = indicators.sma50 - indicators.sma50_prev
        prev_slope = indicators.sma50_prev - indicators.sma50_prev2
        if sma_slope > 0 and prev_slope > 0:
            score += 15
        elif sma_slope < 0 and prev_slope < 0:
            score -= 15
        elif sma_slope > 0:
            score += 5
        else:
            score -= 5

        if indicators.macd_line > indicators.macd_signal:
            score += 10
        else:
            score -= 10

        if indicators.macd_histogram > 0 and indicators.macd_histogram_prev > 0:
            score += 5
        elif indicators.macd_histogram < 0 and indicators.macd_histogram_prev < 0:
            score -= 5

        if indicators.rsi > 60:
            score += 10
        elif indicators.rsi < 40:
            score -= 10
        elif indicators.rsi > 50:
            score += 3
        else:
            score -= 3

        if indicators.adx > 25:
            if indicators.plus_di > indicators.minus_di:
                score += 10
            else:
                score -= 10
        elif indicators.adx > 20:
            if indicators.plus_di > indicators.minus_di:
                score += 5
            else:
                score -= 5

        recent_closes = [c.close for c in candles[-10:]]
        if len(recent_closes) >= 5:
            first_half = sum(recent_closes[:5]) / 5
            second_half = sum(recent_closes[5:]) / 10
            if second_half > first_half * 1.01:
                score += 10
            elif second_half < first_half * 0.99:
                score -= 10

        upper_cross = False
        lower_cross = False
        for i in range(max(1, len(sma50_values) - 5), len(sma50_values)):
            if candles[i].close > sma50_values[i] and candles[i-1].close <= sma50_values[i-1]:
                upper_cross = True
            if candles[i].close < sma50_values[i] and candles[i-1].close >= sma50_values[i-1]:
                lower_cross = True

        if upper_cross:
            score += 10
        if lower_cross:
            score -= 10

        if indicators.vwap < current_price:
            score += 5
        else:
            score -= 5

        if score >= 40:
            return TrendDirection.STRONG_UP
        elif score >= 20:
            return TrendDirection.UP
        elif score >= -20:
            return TrendDirection.SIDEWAYS
        elif score >= -40:
            return TrendDirection.DOWN
        else:
            return TrendDirection.STRONG_DOWN

    @staticmethod
    def analyze_market_phase(candles: List[Candle], indicators: IndicatorValues,
                             sma50_values: List[float]) -> MarketPhase:
        """Determine current market phase."""
        closes = [c.close for c in candles]
        volumes = [c.volume for c in candles]

        if len(closes) < 40:
            return MarketPhase.SIDEWAYS

        recent_avg = sum(closes[-10:]) / 10
        older_avg = sum(closes[-40:-30]) / 10
        mid_avg = sum(closes[-20:-10]) / 10

        recent_vol_avg = sum(volumes[-10:]) / 10
        older_vol_avg = sum(volumes[-30:-20]) / 10

        if recent_avg > mid_avg > older_avg:
            if recent_vol_avg > older_vol_avg * 1.2:
                return MarketPhase.MARKUP
            return MarketPhase.ACCUMULATION
        elif recent_avg < mid_avg < older_avg:
            if recent_vol_avg > older_vol_avg * 1.2:
                return MarketPhase.MARKDOWN
            return MarketPhase.DISTRIBUTION
        elif recent_avg > older_avg:
            return MarketPhase.MARKUP
        elif recent_avg < older_avg:
            return MarketPhase.MARKDOWN
        return MarketPhase.SIDEWAYS

    @staticmethod
    def calculate_trend_strength(score: float) -> float:
        """Calculate trend strength as percentage (0-100)."""
        normalized = min(abs(score), 80) / 80
        return round(normalized * 100, 1)


# ============================================================================
# SECTION 5: SUPPORT AND RESISTANCE DETECTION
# ============================================================================

class SupportResistanceDetector:
    """Dynamic support and resistance level detection."""

    @staticmethod
    def find_levels(candles: List[Candle], lookback: int = 50,
                    sensitivity: float = 0.5) -> SupportResistance:
        """Find support and resistance levels using multiple methods."""
        sr = SupportResistance()

        pivots = SupportResistanceDetector._find_pivot_points(candles, lookback)
        sr.levels.extend([p[0] for p in pivots])
        sr.types.extend([p[1] for p in pivots])
        sr.touches.extend([p[2] for p in pivots])

        horizontal = SupportResistanceDetector._find_horizontal_levels(candles, lookback)
        sr.levels.extend([h[0] for h in horizontal])
        sr.types.extend([h[1] for h in horizontal])
        sr.touches.extend([h[2] for h in horizontal])

        sr.strength = [min(t * 10, 100) for t in sr.touches]

        if sr.levels:
            sr.levels, sr.types, sr.strength, sr.touches = zip(
                *sorted(zip(sr.levels, sr.types, sr.strength, sr.touches),
                        key=lambda x: x[0])
            )
            sr.levels = list(sr.levels)
            sr.types = list(sr.types)
            sr.strength = list(sr.strength)
            sr.touches = list(sr.touches)

        return sr

    @staticmethod
    def _find_pivot_points(candles: List[Candle], lookback: int) -> List[Tuple]:
        """Find pivot high and low points."""
        pivots = []
        half_window = max(2, lookback // 20)
        start = max(half_window, len(candles) - lookback)
        for i in range(start, len(candles) - half_window):
            is_high = True
            is_low = True
            for j in range(i - half_window, i + half_window + 1):
                if j == i or j < 0 or j >= len(candles):
                    continue
                if candles[j].high >= candles[i].high:
                    is_high = False
                if candles[j].low <= candles[i].low:
                    is_low = False
            if is_high:
                pivots.append((candles[i].high, 'resistance', 1))
            if is_low:
                pivots.append((candles[i].low, 'support', 1))
        return pivots

    @staticmethod
    def _find_horizontal_levels(candles: List[Candle], lookback: int) -> List[Tuple]:
        """Find horizontal support/resistance levels by clustering."""
        all_prices = []
        start = max(0, len(candles) - lookback)
        for c in candles[start:]:
            all_prices.extend([c.high, c.low, c.open, c.close])
        if not all_prices:
            return []

        price_range = max(all_prices) - min(all_prices)
        if price_range == 0:
            return []

        cluster_threshold = price_range * 0.01
        sorted_prices = sorted(all_prices)
        clusters = []
        current_cluster = [sorted_prices[0]]
        for i in range(1, len(sorted_prices)):
            if sorted_prices[i] - sorted_prices[i-1] <= cluster_threshold:
                current_cluster.append(sorted_prices[i])
            else:
                if len(current_cluster) >= 3:
                    clusters.append(current_cluster)
                current_cluster = [sorted_prices[i]]
        if len(current_cluster) >= 3:
            clusters.append(current_cluster)

        levels = []
        for cluster in clusters:
            avg_price = sum(cluster) / len(cluster)
            touch_count = len(cluster)
            close_to_high = sum(1 for p in cluster if p > avg_price)
            close_to_low = sum(1 for p in cluster if p < avg_price)
            if close_to_high > close_to_low:
                level_type = 'resistance'
            else:
                level_type = 'support'
            levels.append((avg_price, level_type, touch_count))
        return levels

    @staticmethod
    def get_nearest_levels(sr: SupportResistance, current_price: float,
                           count: int = 3) -> Tuple[List[float], List[float]]:
        """Get nearest support and resistance levels."""
        supports = []
        resistances = []
        for level, stype in zip(sr.levels, sr.types):
            if level < current_price and stype == 'support':
                supports.append(level)
            elif level > current_price and stype == 'resistance':
                resistances.append(level)
        supports.sort(reverse=True)
        resistances.sort()
        return supports[:count], resistances[:count]

    @staticmethod
    def calculate_dynamic_levels(candles: List[Candle],
                                  indicators: IndicatorValues) -> Tuple[List[float], List[float]]:
        """Calculate dynamic support/resistance from indicators."""
        current_price = candles[-1].close
        supports = []
        resistances = []

        if indicators.sma50 > 0:
            if indicators.sma50 < current_price:
                supports.append(indicators.sma50)
            else:
                resistances.append(indicators.sma50)

        if indicators.bb_lower > 0:
            supports.append(indicators.bb_lower)
            resistances.append(indicators.bb_upper)

        if indicators.vwap > 0:
            if indicators.vwap < current_price:
                supports.append(indicators.vwap)
            else:
                resistances.append(indicators.vwap)

        for i in range(max(0, len(candles)-10), len(candles)):
            if candles[i].low not in supports:
                if candles[i].low < current_price:
                    supports.append(candles[i].low)
            if candles[i].high not in resistances:
                if candles[i].high > current_price:
                    resistances.append(candles[i].high)

        supports = sorted(set(supports), reverse=True)[:5]
        resistances = sorted(set(resistances))[:5]
        return supports, resistances


# ============================================================================
# SECTION 6: CANDLESTICK PATTERN RECOGNITION
# ============================================================================

class PatternRecognizer:
    """Candlestick pattern recognition engine."""

    @staticmethod
    def detect_patterns(candles: List[Candle]) -> List[CandlePattern]:
        """Detect all candlestick patterns in recent candles."""
        if len(candles) < 3:
            return [CandlePattern.NONE]

        patterns = []
        c = candles[-1]
        c_prev = candles[-2]
        c_prev2 = candles[-3] if len(candles) > 2 else None

        avg_body = statistics.mean([x.body_size for x in candles[-20:]]) if len(candles) >= 20 else c.body_size
        avg_range = statistics.mean([x.total_range for x in candles[-20:]]) if len(candles) >= 20 else c.total_range

        if c.total_range > 0 and c.body_size / c.total_range < 0.1:
            patterns.append(CandlePattern.DOJI)
        elif c.total_range > 0 and c.body_size / c.total_range < 0.2:
            patterns.append(CandlePattern.SPINNING_TOP)

        if (c.lower_shadow > c.body_size * 2 and
            c.upper_shadow < c.body_size * 0.5 and
            c.body_size > avg_body * 0.3):
            if c.is_bullish:
                patterns.append(CandlePattern.HAMMER)
            else:
                patterns.append(CandlePattern.HANGING_MAN)

        if (c.upper_shadow > c.body_size * 2 and
            c.lower_shadow < c.body_size * 0.5 and
            c.body_size > avg_body * 0.3):
            if c.is_bearish:
                patterns.append(CandlePattern.SHOOTING_STAR)
            else:
                patterns.append(CandlePattern.INVERTED_HAMMER)

        if (c_prev.is_bearish and c.is_bullish and
            c.close > c_prev.open and c.open < c_prev.close):
            patterns.append(CandlePattern.ENGULFING_BULLISH)

        if (c_prev.is_bullish and c.is_bearish and
            c.close < c_prev.open and c.open > c_prev.close):
            patterns.append(CandlePattern.ENGULFING_BEARISH)

        if c_prev2 and len(candles) > 2:
            if (c_prev2.is_bearish and c_prev2.body_size > avg_body * 0.5 and
                c_prev.is_bearish and c_prev.body_size < avg_body * 0.3 and
                c.is_bullish and c.body_size > avg_body * 0.5 and
                c.close > (c_prev2.open + c_prev2.close) / 2):
                patterns.append(CandlePattern.MORNING_STAR)

            if (c_prev2.is_bullish and c_prev2.body_size > avg_body * 0.5 and
                c_prev.is_bullish and c_prev.body_size < avg_body * 0.3 and
                c.is_bearish and c.body_size > avg_body * 0.5 and
                c.close < (c_prev2.open + c_prev2.close) / 2):
                patterns.append(CandlePattern.EVENING_STAR)

        if (c.is_bullish and c_prev.is_bullish and c_prev2 and c_prev2.is_bullish and
            c.close > c_prev.close > c_prev2.close and
            c.open > c_prev.open > c_prev2.open):
            patterns.append(CandlePattern.THREE_WHITE_SOLDIERS)

        if (c.is_bearish and c_prev.is_bearish and c_prev2 and c_prev2.is_bearish and
            c.close < c_prev.close < c_prev2.close and
            c.open < c_prev.open < c_prev2.open):
            patterns.append(CandlePattern.THREE_BLACK_CROWS)

        if (c_prev.is_bearish and c.is_bullish and
            c.open > c_prev.close and c.close < c_prev.open and
            c.close > (c_prev.open + c_prev.close) / 2):
            patterns.append(CandlePattern.PIERCING_LINE)

        if (c_prev.is_bullish and c.is_bearish and
            c.open < c_prev.close and c.close > c_prev.open and
            c.close < (c_prev.open + c_prev.close) / 2):
            patterns.append(CandlePattern.DARK_CLOUD_COVER)

        if (c_prev.is_bullish and c.is_bearish and
            c.open < c_prev.close and c.close > c_prev.open and
            c.close < c_prev.close and c.open > c_prev.open):
            patterns.append(CandlePattern.HARAMI_BEARISH)

        if (c_prev.is_bearish and c.is_bullish and
            c.open > c_prev.close and c.close < c_prev.open and
            c.close > c_prev.close and c.open < c_prev.open):
            patterns.append(CandlePattern.HARAMI_BULLISH)

        return patterns if patterns else [CandlePattern.NONE]

    @staticmethod
    def pattern_bullish_score(patterns: List[CandlePattern]) -> int:
        """Calculate bullish score from patterns."""
        score = 0
        bullish_patterns = [
            CandlePattern.HAMMER, CandlePattern.ENGULFING_BULLISH,
            CandlePattern.MORNING_STAR, CandlePattern.THREE_WHITE_SOLDIERS,
            CandlePattern.PIERCING_LINE, CandlePattern.HARAMI_BULLISH,
            CandlePattern.INVERTED_HAMMER
        ]
        for p in patterns:
            if p in bullish_patterns:
                if p in [CandlePattern.ENGULFING_BULLISH, CandlePattern.MORNING_STAR,
                         CandlePattern.THREE_WHITE_SOLDIERS]:
                    score += 3
                else:
                    score += 1
        return score

    @staticmethod
    def pattern_bearish_score(patterns: List[CandlePattern]) -> int:
        """Calculate bearish score from patterns."""
        score = 0
        bearish_patterns = [
            CandlePattern.SHOOTING_STAR, CandlePattern.ENGULFING_BEARISH,
            CandlePattern.EVENING_STAR, CandlePattern.THREE_BLACK_CROWS,
            CandlePattern.DARK_CLOUD_COVER, CandlePattern.HARAMI_BEARISH,
            CandlePattern.HANGING_MAN
        ]
        for p in patterns:
            if p in bearish_patterns:
                if p in [CandlePattern.ENGULFING_BEARISH, CandlePattern.EVENING_STAR,
                         CandlePattern.THREE_BLACK_CROWS]:
                    score += 3
                else:
                    score += 1
        return score


# ============================================================================
# SECTION 7: VOLUME ANALYSIS
# ============================================================================

class VolumeAnalyzer:
    """Volume analysis and divergence detection."""

    @staticmethod
    def analyze_volume(candles: List[Candle], volume_sma: float) -> Dict[str, Any]:
        """Comprehensive volume analysis."""
        result = {
            'current_volume': candles[-1].volume,
            'avg_volume': volume_sma,
            'volume_ratio': candles[-1].volume / volume_sma if volume_sma > 0 else 1.0,
            'buy_pressure': candles[-1].buy_pressure,
            'trend': 'normal',
            'divergence': 'none',
            'accumulation': False,
            'distribution': False
        }

        vol_ratio = result['volume_ratio']
        if vol_ratio > 2.0:
            result['trend'] = 'extreme_high'
        elif vol_ratio > 1.5:
            result['trend'] = 'high'
        elif vol_ratio > 0.8:
            result['trend'] = 'normal'
        elif vol_ratio > 0.5:
            result['trend'] = 'low'
        else:
            result['trend'] = 'extreme_low'

        recent = candles[-10:] if len(candles) >= 10 else candles
        price_change = (recent[-1].close - recent[0].open) / recent[0].open
        volume_trend = [(c.taker_buy_volume / c.volume if c.volume > 0 else 0.5) for c in recent]
        avg_buy = sum(volume_trend) / len(volume_trend)

        if price_change > 0.01 and avg_buy < 0.45:
            result['divergence'] = 'bearish'
        elif price_change < -0.01 and avg_buy > 0.55:
            result['divergence'] = 'bullish'
        else:
            result['divergence'] = 'none'

        total_buy = sum(c.taker_buy_volume for c in recent[-5:])
        total_vol = sum(c.volume for c in recent[-5:])
        if total_vol > 0 and total_buy / total_vol > 0.55:
            result['accumulation'] = True
        elif total_vol > 0 and total_buy / total_vol < 0.45:
            result['distribution'] = True

        return result

    @staticmethod
    def volume_confirmation(vol_data: Dict[str, Any], signal_direction: str) -> float:
        """Check if volume confirms the signal direction."""
        confirmation = 0.5
        ratio = vol_data['volume_ratio']
        buy_p = vol_data['buy_pressure']

        if signal_direction == 'bullish':
            if ratio > 1.5 and buy_p > 0.6:
                confirmation = 1.0
            elif ratio > 1.2 and buy_p > 0.55:
                confirmation = 0.8
            elif ratio > 1.0 and buy_p > 0.5:
                confirmation = 0.6
            elif buy_p < 0.4:
                confirmation = 0.2
            elif vol_data['divergence'] == 'bullish':
                confirmation = 0.7
        elif signal_direction == 'bearish':
            if ratio > 1.5 and buy_p < 0.4:
                confirmation = 1.0
            elif ratio > 1.2 and buy_p < 0.45:
                confirmation = 0.8
            elif ratio > 1.0 and buy_p < 0.5:
                confirmation = 0.6
            elif buy_p > 0.6:
                confirmation = 0.2
            elif vol_data['divergence'] == 'bearish':
                confirmation = 0.7
        return confirmation


# ============================================================================
# SECTION 8: SIGNAL GENERATION ENGINE
# ============================================================================

class SignalGenerator:
    """Main signal generation engine combining all analysis components."""

    def __init__(self, candles: List[Candle]):
        self.candles = candles
        self.closes = [c.close for c in candles]
        self.indicators = IndicatorValues()
        self.sr = SupportResistance()
        self.ti = TechnicalIndicators()
        self.ta = TrendAnalyzer()
        self.srd = SupportResistanceDetector()
        self.pr = PatternRecognizer()
        self.va = VolumeAnalyzer()
        self.sma50_values = []
        self.sma200_values = []
        self.ema12_values = []
        self.ema26_values = []
        self.macd_line = []
        self.macd_signal = []
        self.macd_histogram = []
        self.rsi_values = []
        self.bb_upper = []
        self.bb_middle = []
        self.bb_lower = []
        self.atr_values = []
        self.stoch_k = []
        self.stoch_d = []
        self.obv_values = []
        self.vwap_values = []
        self.momentum_values = []
        self.roc_values = []
        self.adx_values = []
        self.plus_di_values = []
        self.minus_di_values = []
        self.cci_values = []
        self.mfi_values = []
        self.williams_r_values = []

    def calculate_all_indicators(self):
        """Calculate all technical indicators."""
        print("[INFO] Calculating technical indicators...")

        self.sma50_values = self.ti.sma(self.closes, 50)
        self.sma200_values = self.ti.sma(self.closes, min(200, len(self.closes) - 1))
        self.ema12_values = self.ti.ema(self.closes, 12)
        self.ema26_values = self.ti.ema(self.closes, 26)
        self.macd_line, self.macd_signal, self.macd_histogram = self.ti.macd(self.closes)
        self.rsi_values = self.ti.rsi(self.closes)
        self.bb_upper, self.bb_middle, self.bb_lower = self.ti.bollinger_bands(self.closes)
        self.atr_values = self.ti.atr(self.candles)
        self.stoch_k, self.stoch_d = self.ti.stochastic(self.candles)
        self.obv_values = self.ti.obv(self.candles)
        self.vwap_values = self.ti.vwap(self.candles)
        self.momentum_values = self.ti.momentum(self.closes)
        self.roc_values = self.ti.rate_of_change(self.closes)
        self.adx_values, self.plus_di_values, self.minus_di_values = self.ti.adx(self.candles)
        self.cci_values = self.ti.cci(self.candles)
        self.mfi_values = self.ti.money_flow_index(self.candles)
        self.williams_r_values = self.ti.williams_r(self.candles)

        i = len(self.candles) - 1
        self.indicators.sma50 = self.sma50_values[i]
        self.indicators.sma50_prev = self.sma50_values[i-1] if i > 0 else self.sma50_values[i]
        self.indicators.sma50_prev2 = self.sma50_values[i-2] if i > 1 else self.sma50_values[i]
        self.indicators.ema12 = self.ema12_values[i]
        self.indicators.ema26 = self.ema26_values[i]
        self.indicators.macd_line = self.macd_line[i]
        self.indicators.macd_signal = self.macd_signal[i]
        self.indicators.macd_histogram = self.macd_histogram[i]
        self.indicators.macd_histogram_prev = self.macd_histogram[i-1] if i > 0 else 0
        self.indicators.rsi = self.rsi_values[i]
        self.indicators.rsi_prev = self.rsi_values[i-1] if i > 0 else 50
        self.indicators.bb_upper = self.bb_upper[i]
        self.indicators.bb_middle = self.bb_middle[i]
        self.indicators.bb_lower = self.bb_lower[i]
        self.indicators.bb_width = ((self.bb_upper[i] - self.bb_lower[i]) /
                                     self.bb_middle[i] * 100) if self.bb_middle[i] > 0 else 0
        self.indicators.atr = self.atr_values[i]
        self.indicators.atr_percent = (self.atr_values[i] / self.closes[i] * 100) if self.closes[i] > 0 else 0
        self.indicators.obv = self.obv_values[i]
        self.indicators.obv_sma = sum(self.obv_values[-20:]) / min(20, len(self.obv_values))
        self.indicators.volume_sma = sum(c.volume for c in self.candles[-20:]) / min(20, len(self.candles))
        self.indicators.stoch_k = self.stoch_k[i]
        self.indicators.stoch_d = self.stoch_d[i]
        self.indicators.vwap = self.vwap_values[i]
        self.indicators.momentum = self.momentum_values[i]
        self.indicators.roc = self.roc_values[i]
        self.indicators.adx = self.adx_values[i]
        self.indicators.plus_di = self.plus_di_values[i]
        self.indicators.minus_di = self.minus_di_values[i]
        self.indicators.cci = self.cci_values[i]
        self.indicators.mfi = self.mfi_values[i]
        self.indicators.williams_r = self.williams_r_values[i]

        print(f"[INFO] SMA50: {self.indicators.sma50:.2f}")
        print(f"[INFO] RSI: {self.indicators.rsi:.2f}")
        print(f"[INFO] MACD: {self.indicators.macd_line:.4f}")
        print(f"[INFO] ATR: {self.indicators.atr:.2f} ({self.indicators.atr_percent:.2f}%)")

    def generate_signal(self) -> SignalResult:
        """Generate the final trading signal with full analysis."""
        print("\n" + "=" * 70)
        print("  SMA 50 TRADING BOT - TREND & DYNAMIC SUPPORT/RESISTANCE ANALYSIS")
        print("=" * 70)

        self.calculate_all_indicators()

        result = SignalResult()
        current_price = self.candles[-1].close
        prev_price = self.candles[-2].close if len(self.candles) > 1 else current_price

        trend_direction = self.ta.analyze_trend_direction(
            self.candles, self.indicators, self.sma50_values
        )
        market_phase = self.ta.analyze_market_phase(
            self.candles, self.indicators, self.sma50_values
        )
        result.trend_direction = trend_direction
        result.market_phase = market_phase

        self.sr = self.srd.find_levels(self.candles)
        nearest_supports, nearest_resistances = self.srd.get_nearest_levels(
            self.sr, current_price
        )
        dyn_supports, dyn_resistances = self.srd.calculate_dynamic_levels(
            self.candles, self.indicators
        )
        all_supports = sorted(set(nearest_supports + dyn_supports), reverse=True)[:5]
        all_resistances = sorted(set(nearest_resistances + dyn_resistances))[:5]
        result.support_levels = all_supports
        result.resistance_levels = all_resistances

        patterns = self.pr.detect_patterns(self.candles)
        bullish_pattern_score = self.pr.pattern_bullish_score(patterns)
        bearish_pattern_score = self.pr.pattern_bearish_score(patterns)
        result.patterns_detected = [p.value for p in patterns if p != CandlePattern.NONE]

        vol_data = self.va.analyze_volume(self.candles, self.indicators.volume_sma)
        result.volume_analysis = self._format_volume_analysis(vol_data)

        bull_score = 0
        bear_score = 0
        reasons_bull = []
        reasons_bear = []
        warnings = []

        self._evaluate_sma50_position(current_price, bull_score, bear_score,
                                       reasons_bull, reasons_bear)
        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_sma50_position(
            current_price, bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_sma50_slope(
            bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_rsi(
            bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_macd(
            bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_bollinger(
            current_price, bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_adx(
            bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_stochastic(
            bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_obv(
            bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_vwap(
            current_price, bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_momentum(
            bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_cci(
            bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_mfi(
            bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_williams_r(
            bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_volume_analysis(
            vol_data, bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_trend_alignment(
            trend_direction, bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score, bear_score, reasons_bull, reasons_bear = self._evaluate_market_phase(
            market_phase, bull_score, bear_score, reasons_bull, reasons_bear
        )

        bull_score += bullish_pattern_score
        bear_score += bearish_pattern_score

        vol_confirmation = self.va.volume_confirmation(
            vol_data, 'bullish' if bull_score > bear_score else 'bearish'
        )

        sma_distance = abs(current_price - self.indicators.sma50) / self.indicators.sma50 * 100
        if sma_distance > 8:
            warnings.append(f"Price {sma_distance:.1f}% away from SMA50 - overextension risk")
        if sma_distance > 15:
            warnings.append("Extreme deviation from SMA50 - pullback likely")

        if self.indicators.rsi > 80:
            warnings.append("RSI in extreme overbought territory")
        elif self.indicators.rsi < 20:
            warnings.append("RSI in extreme oversold territory")

        if self.indicators.atr_percent > 5:
            warnings.append("High volatility environment - use wider stops")
        elif self.indicators.atr_percent < 1:
            warnings.append("Low volatility - breakout may be imminent")

        net_score = bull_score - bear_score
        confidence = min(abs(net_score) * 5, 95)

        if net_score >= 15:
            result.signal_type = SignalType.STRONG_BUY
            result.spot_action = "BUY"
            result.futures_action = "LONG"
        elif net_score >= 8:
            result.signal_type = SignalType.BUY
            result.spot_action = "BUY"
            result.futures_action = "LONG"
        elif net_score <= -15:
            result.signal_type = SignalType.STRONG_SELL
            result.spot_action = "SELL"
            result.futures_action = "SHORT"
        elif net_score <= -8:
            result.signal_type = SignalType.SELL
            result.spot_action = "SELL"
            result.futures_action = "SHORT"
        else:
            result.signal_type = SignalType.HOLD
            result.spot_action = "HOLD"
            result.futures_action = "HOLD"

        result.confidence = confidence
        result.reasons = reasons_bull if net_score > 0 else reasons_bear
        if net_score > 0:
            result.reasons = reasons_bull
        else:
            result.reasons = reasons_bear
        result.warnings = warnings

        if result.signal_type != SignalType.HOLD:
            result.entry_price = current_price
            result.stop_loss = self._calculate_stop_loss(
                current_price, trend_direction, all_supports, all_resistances
            )
            result.take_profit_1 = self._calculate_take_profit_1(
                current_price, trend_direction, all_supports, all_resistances
            )
            result.take_profit_2 = self._calculate_take_profit_2(
                current_price, trend_direction, all_supports, all_resistances
            )
            result.take_profit_3 = self._calculate_take_profit_3(
                current_price, trend_direction, all_supports, all_resistances
            )
            result.risk_reward_ratio = self._calculate_risk_reward(
                current_price, result.stop_loss, result.take_profit_1
            )
            result.position_size_pct = self._calculate_position_size(
                confidence, self.indicators.atr_percent
            )
            result.leverage_suggestion = self._suggest_leverage(
                trend_direction, self.indicators.atr_percent, confidence
            )

        result.indicators_summary = {
            'SMA50': f"{self.indicators.sma50:.2f}",
            'SMA50 Slope': f"{self.indicators.sma50 - self.indicators.sma50_prev:.2f}",
            'RSI(14)': f"{self.indicators.rsi:.2f}",
            'MACD': f"{self.indicators.macd_line:.4f}",
            'MACD Signal': f"{self.indicators.macd_signal:.4f}",
            'MACD Histogram': f"{self.indicators.macd_histogram:.4f}",
            'BB Upper': f"{self.indicators.bb_upper:.2f}",
            'BB Lower': f"{self.indicators.bb_lower:.2f}",
            'BB Width': f"{self.indicators.bb_width:.2f}%",
            'ATR(14)': f"{self.indicators.atr:.2f}",
            'ATR %': f"{self.indicators.atr_percent:.2f}%",
            'Stoch K': f"{self.indicators.stoch_k:.2f}",
            'Stoch D': f"{self.indicators.stoch_d:.2f}",
            'ADX': f"{self.indicators.adx:.2f}",
            '+DI': f"{self.indicators.plus_di:.2f}",
            '-DI': f"{self.indicators.minus_di:.2f}",
            'CCI(20)': f"{self.indicators.cci:.2f}",
            'MFI(14)': f"{self.indicators.mfi:.2f}",
            'Williams %R': f"{self.indicators.williams_r:.2f}",
            'VWAP': f"{self.indicators.vwap:.2f}",
            'Momentum': f"{self.indicators.momentum:.2f}",
            'ROC': f"{self.indicators.roc:.2f}%",
            'OBV Trend': 'Up' if self.indicators.obv > self.indicators.obv_sma else 'Down',
            'Volume Ratio': f"{vol_data['volume_ratio']:.2f}",
            'Buy Pressure': f"{vol_data['buy_pressure']:.2%}"
        }

        return result

    def _evaluate_sma50_position(self, price, bull, bear, reasons_b, reasons_s):
        """Evaluate price position relative to SMA50."""
        if price > self.indicators.sma50:
            bull += 3
            reasons_b.append(f"Price ({price:.2f}) is ABOVE SMA50 ({self.indicators.sma50:.2f}) - bullish bias")
        else:
            bear += 3
            reasons_s.append(f"Price ({price:.2f}) is BELOW SMA50 ({self.indicators.sma50:.2f}) - bearish bias")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_sma50_slope(self, bull, bear, reasons_b, reasons_s):
        """Evaluate SMA50 slope for trend direction."""
        slope = self.indicators.sma50 - self.indicators.sma50_prev
        prev_slope = self.indicators.sma50_prev - self.indicators.sma50_prev2
        if slope > 0 and prev_slope > 0:
            bull += 2
            reasons_b.append(f"SMA50 slope is POSITIVE ({slope:.2f}) - consistent uptrend")
        elif slope < 0 and prev_slope < 0:
            bear += 2
            reasons_s.append(f"SMA50 slope is NEGATIVE ({slope:.2f}) - consistent downtrend")
        elif slope > 0:
            bull += 1
            reasons_b.append(f"SMA50 slope turning positive ({slope:.2f}) - potential reversal")
        else:
            bear += 1
            reasons_s.append(f"SMA50 slope turning negative ({slope:.2f}) - potential reversal")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_rsi(self, bull, bear, reasons_b, reasons_s):
        """Evaluate RSI for overbought/oversold conditions."""
        rsi = self.indicators.rsi
        if rsi < 30:
            bull += 3
            reasons_b.append(f"RSI ({rsi:.1f}) is OVERSOLD - potential bounce")
        elif rsi < 40:
            bull += 1
            reasons_b.append(f"RSI ({rsi:.1f}) approaching oversold zone")
        elif rsi > 70:
            bear += 3
            reasons_s.append(f"RSI ({rsi:.1f}) is OVERBOUGHT - potential pullback")
        elif rsi > 60:
            bear += 1
            reasons_s.append(f"RSI ({rsi:.1f}) approaching overbought zone")
        if self.indicators.rsi > self.indicators.rsi_prev and rsi < 50:
            bull += 1
            reasons_b.append("RSI rising from low levels - momentum building")
        elif self.indicators.rsi < self.indicators.rsi_prev and rsi > 50:
            bear += 1
            reasons_s.append("RSI falling from high levels - momentum fading")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_macd(self, bull, bear, reasons_b, reasons_s):
        """Evaluate MACD for trend and momentum signals."""
        macd = self.indicators.macd_line
        signal = self.indicators.macd_signal
        hist = self.indicators.macd_histogram
        hist_prev = self.indicators.macd_histogram_prev
        if macd > signal:
            bull += 2
            reasons_b.append(f"MACD ({macd:.4f}) above Signal ({signal:.4f}) - bullish momentum")
        else:
            bear += 2
            reasons_s.append(f"MACD ({macd:.4f}) below Signal ({signal:.4f}) - bearish momentum")
        if hist > 0 and hist_prev > 0 and hist > hist_prev:
            bull += 1
            reasons_b.append("MACD histogram expanding upward - strengthening momentum")
        elif hist < 0 and hist_prev < 0 and hist < hist_prev:
            bear += 1
            reasons_s.append("MACD histogram expanding downward - weakening momentum")
        if hist > 0 and hist_prev <= 0:
            bull += 2
            reasons_b.append("MACD BULLISH CROSSOVER - strong buy signal")
        elif hist < 0 and hist_prev >= 0:
            bear += 2
            reasons_s.append("MACD BEARISH CROSSOVER - strong sell signal")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_bollinger(self, price, bull, bear, reasons_b, reasons_s):
        """Evaluate Bollinger Band position."""
        if price <= self.indicators.bb_lower:
            bull += 2
            reasons_b.append(f"Price at lower Bollinger Band ({self.indicators.bb_lower:.2f}) - oversold")
        elif price >= self.indicators.bb_upper:
            bear += 2
            reasons_s.append(f"Price at upper Bollinger Band ({self.indicators.bb_upper:.2f}) - overbought")
        elif price < self.indicators.bb_middle:
            bull += 1
            reasons_b.append("Price below BB middle - room to move up")
        else:
            bear += 1
            reasons_s.append("Price above BB middle - room to move down")
        if self.indicators.bb_width < 3:
            reasons_b.append("BB squeeze detected - breakout imminent")
            reasons_s.append("BB squeeze detected - breakout imminent")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_adx(self, bull, bear, reasons_b, reasons_s):
        """Evaluate ADX for trend strength."""
        adx = self.indicators.adx
        if adx > 25:
            if self.indicators.plus_di > self.indicators.minus_di:
                bull += 2
                reasons_b.append(f"ADX ({adx:.1f}) + DI > -DI - strong uptrend")
            else:
                bear += 2
                reasons_s.append(f"ADX ({adx:.1f}) -DI > +DI - strong downtrend")
        elif adx > 20:
            if self.indicators.plus_di > self.indicators.minus_di:
                bull += 1
                reasons_b.append(f"ADX ({adx:.1f}) - moderate uptrend")
            else:
                bear += 1
                reasons_s.append(f"ADX ({adx:.1f}) - moderate downtrend")
        else:
            reasons_b.append(f"ADX ({adx:.1f}) - weak/no trend, ranging market")
            reasons_s.append(f"ADX ({adx:.1f}) - weak/no trend, ranging market")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_stochastic(self, bull, bear, reasons_b, reasons_s):
        """Evaluate Stochastic Oscillator."""
        k = self.indicators.stoch_k
        d = self.indicators.stoch_d
        if k < 20:
            bull += 2
            reasons_b.append(f"Stochastic ({k:.1f}/{d:.1f}) in OVERSOLD zone")
        elif k > 80:
            bear += 2
            reasons_s.append(f"Stochastic ({k:.1f}/{d:.1f}) in OVERBOUGHT zone")
        if k > d and k < 80:
            bull += 1
            reasons_b.append("Stochastic K above D - bullish crossover")
        elif k < d and k > 20:
            bear += 1
            reasons_s.append("Stochastic K below D - bearish crossover")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_obv(self, bull, bear, reasons_b, reasons_s):
        """Evaluate On-Balance Volume."""
        if self.indicators.obv > self.indicators.obv_sma:
            bull += 1
            reasons_b.append("OBV above its SMA - volume supports uptrend")
        else:
            bear += 1
            reasons_s.append("OBV below its SMA - volume supports downtrend")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_vwap(self, price, bull, bear, reasons_b, reasons_s):
        """Evaluate VWAP position."""
        if price > self.indicators.vwap:
            bull += 1
            reasons_b.append(f"Price ({price:.2f}) above VWAP ({self.indicators.vwap:.2f}) - bullish")
        else:
            bear += 1
            reasons_s.append(f"Price ({price:.2f}) below VWAP ({self.indicators.vwap:.2f}) - bearish")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_momentum(self, bull, bear, reasons_b, reasons_s):
        """Evaluate momentum indicators."""
        mom = self.indicators.momentum
        roc = self.indicators.roc
        if mom > 0:
            bull += 1
            reasons_b.append(f"Momentum ({mom:.2f}) positive - upward pressure")
        else:
            bear += 1
            reasons_s.append(f"Momentum ({mom:.2f}) negative - downward pressure")
        if roc > 2:
            bull += 1
            reasons_b.append(f"ROC ({roc:.2f}%) strong positive - accelerating up")
        elif roc < -2:
            bear += 1
            reasons_s.append(f"ROC ({roc:.2f}%) strong negative - accelerating down")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_cci(self, bull, bear, reasons_b, reasons_s):
        """Evaluate CCI."""
        cci = self.indicators.cci
        if cci < -100:
            bull += 1
            reasons_b.append(f"CCI ({cci:.1f}) oversold - potential reversal up")
        elif cci > 100:
            bear += 1
            reasons_s.append(f"CCI ({cci:.1f}) overbought - potential reversal down")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_mfi(self, bull, bear, reasons_b, reasons_s):
        """Evaluate Money Flow Index."""
        mfi = self.indicators.mfi
        if mfi < 20:
            bull += 2
            reasons_b.append(f"MFI ({mfi:.1f}) oversold - money flowing in potential")
        elif mfi > 80:
            bear += 2
            reasons_s.append(f"MFI ({mfi:.1f}) overbought - money flowing out potential")
        elif mfi < 40:
            bull += 1
            reasons_b.append(f"MFI ({mfi:.1f}) low - accumulation possible")
        elif mfi > 60:
            bear += 1
            reasons_s.append(f"MFI ({mfi:.1f}) high - distribution possible")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_williams_r(self, bull, bear, reasons_b, reasons_s):
        """Evaluate Williams %R."""
        wr = self.indicators.williams_r
        if wr < -80:
            bull += 1
            reasons_b.append(f"Williams %R ({wr:.1f}) oversold zone")
        elif wr > -20:
            bear += 1
            reasons_s.append(f"Williams %R ({wr:.1f}) overbought zone")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_volume_analysis(self, vol_data, bull, bear, reasons_b, reasons_s):
        """Evaluate volume analysis results."""
        ratio = vol_data['volume_ratio']
        buy_p = vol_data['buy_pressure']
        if ratio > 1.5 and buy_p > 0.55:
            bull += 2
            reasons_b.append(f"High volume ({ratio:.1f}x avg) with {buy_p:.0%} buying - strong accumulation")
        elif ratio > 1.5 and buy_p < 0.45:
            bear += 2
            reasons_s.append(f"High volume ({ratio:.1f}x avg) with {(1-buy_p):.0%} selling - strong distribution")
        if vol_data['divergence'] == 'bullish':
            bull += 1
            reasons_b.append("Bullish volume divergence detected")
        elif vol_data['divergence'] == 'bearish':
            bear += 1
            reasons_s.append("Bearish volume divergence detected")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_trend_alignment(self, trend, bull, bear, reasons_b, reasons_s):
        """Evaluate trend direction alignment."""
        if trend == TrendDirection.STRONG_UP:
            bull += 3
            reasons_b.append("Strong uptrend confirmed by multiple indicators")
        elif trend == TrendDirection.UP:
            bull += 2
            reasons_b.append("Uptrend in progress")
        elif trend == TrendDirection.STRONG_DOWN:
            bear += 3
            reasons_s.append("Strong downtrend confirmed by multiple indicators")
        elif trend == TrendDirection.DOWN:
            bear += 2
            reasons_s.append("Downtrend in progress")
        else:
            reasons_b.append("Market in sideways/consolidation phase")
            reasons_s.append("Market in sideways/consolidation phase")
        return bull, bear, reasons_b, reasons_s

    def _evaluate_market_phase(self, phase, bull, bear, reasons_b, reasons_s):
        """Evaluate market phase."""
        if phase == MarketPhase.ACCUMULATION:
            bull += 2
            reasons_b.append("Market in ACCUMULATION phase - smart money buying")
        elif phase == MarketPhase.MARKUP:
            bull += 2
            reasons_b.append("Market in MARKUP phase - trend continuation likely")
        elif phase == MarketPhase.DISTRIBUTION:
            bear += 2
            reasons_s.append("Market in DISTRIBUTION phase - smart money selling")
        elif phase == MarketPhase.MARKDOWN:
            bear += 2
            reasons_s.append("Market in MARKDOWN phase - trend continuation likely")
        return bull, bear, reasons_b, reasons_s

    def _calculate_stop_loss(self, price: float, trend: TrendDirection,
                              supports: List[float], resistances: List[float]) -> float:
        """Calculate optimal stop loss level."""
        atr = self.indicators.atr
        if trend in [TrendDirection.UP, TrendDirection.STRONG_UP]:
            sl_atr = price - (atr * 1.5)
            sl_support = supports[0] - (atr * 0.3) if supports else sl_atr
            return max(sl_atr, sl_support)
        else:
            sl_atr = price + (atr * 1.5)
            sl_resistance = resistances[0] + (atr * 0.3) if resistances else sl_atr
            return min(sl_atr, sl_resistance)

    def _calculate_take_profit_1(self, price: float, trend: TrendDirection,
                                  supports: List[float], resistances: List[float]) -> float:
        """Calculate first take profit level."""
        atr = self.indicators.atr
        if trend in [TrendDirection.UP, TrendDirection.STRONG_UP]:
            tp_atr = price + (atr * 2.0)
            tp_resist = resistances[0] if resistances else tp_atr
            return min(tp_atr, tp_resist)
        else:
            tp_atr = price - (atr * 2.0)
            tp_support = supports[0] if supports else tp_atr
            return max(tp_atr, tp_support)

    def _calculate_take_profit_2(self, price: float, trend: TrendDirection,
                                  supports: List[float], resistances: List[float]) -> float:
        """Calculate second take profit level."""
        atr = self.indicators.atr
        if trend in [TrendDirection.UP, TrendDirection.STRONG_UP]:
            tp_atr = price + (atr * 3.5)
            tp_resist = resistances[1] if len(resistances) > 1 else tp_atr
            return min(tp_atr, tp_resist)
        else:
            tp_atr = price - (atr * 3.5)
            tp_support = supports[1] if len(supports) > 1 else tp_atr
            return max(tp_atr, tp_support)

    def _calculate_take_profit_3(self, price: float, trend: TrendDirection,
                                  supports: List[float], resistances: List[float]) -> float:
        """Calculate third take profit level (extended)."""
        atr = self.indicators.atr
        if trend in [TrendDirection.UP, TrendDirection.STRONG_UP]:
            tp_atr = price + (atr * 5.0)
            tp_resist = resistances[2] if len(resistances) > 2 else tp_atr
            return min(tp_atr, tp_resist)
        else:
            tp_atr = price - (atr * 5.0)
            tp_support = supports[2] if len(supports) > 2 else tp_atr
            return max(tp_atr, tp_support)

    def _calculate_risk_reward(self, entry: float, sl: float, tp: float) -> float:
        """Calculate risk/reward ratio."""
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk == 0:
            return 0
        return round(reward / risk, 2)

    def _calculate_position_size(self, confidence: float, atr_percent: float) -> float:
        """Calculate recommended position size percentage."""
        base_size = 2.0
        confidence_factor = confidence / 100
        volatility_factor = max(0.5, 1.0 - (atr_percent / 10))
        size = base_size * confidence_factor * volatility_factor
        return round(min(max(size, 0.5), 5.0), 2)

    def _suggest_leverage(self, trend: TrendDirection, atr_percent: float,
                           confidence: float) -> str:
        """Suggest appropriate leverage level."""
        if atr_percent > 5:
            base_lev = "2x-3x"
        elif atr_percent > 3:
            base_lev = "3x-5x"
        elif atr_percent > 2:
            base_lev = "5x-10x"
        else:
            base_lev = "10x-20x"
        if trend in [TrendDirection.STRONG_UP, TrendDirection.STRONG_DOWN]:
            return f"{base_lev} (Strong trend)"
        elif trend == TrendDirection.SIDEWAYS:
            return f"1x-2x (Sideways - low confidence)"
        return base_lev

    def _format_volume_analysis(self, vol_data: Dict[str, Any]) -> str:
        """Format volume analysis for display."""
        lines = []
        lines.append(f"Current Volume: {vol_data['current_volume']:.2f}")
        lines.append(f"Average Volume: {vol_data['avg_volume']:.2f}")
        lines.append(f"Volume Ratio: {vol_data['volume_ratio']:.2f}x")
        lines.append(f"Buy Pressure: {vol_data['buy_pressure']:.1%}")
        lines.append(f"Volume Trend: {vol_data['trend'].upper()}")
        lines.append(f"Divergence: {vol_data['divergence'].upper()}")
        lines.append(f"Accumulation: {'YES' if vol_data['accumulation'] else 'NO'}")
        lines.append(f"Distribution: {'YES' if vol_data['distribution'] else 'NO'}")
        return "\n".join(lines)


# ============================================================================
# SECTION 9: REPORT GENERATOR
# ============================================================================

class ReportGenerator:
    """Generate comprehensive trading analysis reports."""

    @staticmethod
    def generate_report(result: SignalResult, candles: List[Candle],
                       indicators: IndicatorValues) -> str:
        """Generate the full analysis report."""
        current_price = candles[-1].close
        c = candles[-1]
        lines = []

        lines.append("")
        lines.append("=" * 70)
        lines.append("         SMA 50 TRADING BOT - COMPLETE ANALYSIS REPORT")
        lines.append("=" * 70)
        lines.append("")

        lines.append(f"  Analysis Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(f"  Last Candle:   {c.timestamp.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"  Candles Used:  {len(candles)}")
        lines.append("")

        lines.append("-" * 70)
        lines.append("  CURRENT MARKET DATA")
        lines.append("-" * 70)
        lines.append(f"  Open:    {c.open:.2f}")
        lines.append(f"  High:    {c.high:.2f}")
        lines.append(f"  Low:     {c.low:.2f}")
        lines.append(f"  Close:   {c.close:.2f}")
        lines.append(f"  Volume:  {c.volume:.2f}")
        lines.append(f"  Range:   {c.total_range:.2f}")
        lines.append(f"  Body:    {c.body_size:.2f} ({'Bullish' if c.is_bullish else 'Bearish'})")
        lines.append(f"  Buy Pressure: {c.buy_pressure:.1%}")
        lines.append("")

        lines.append("-" * 70)
        lines.append("  SIGNAL SUMMARY")
        lines.append("-" * 70)
        signal_display = result.signal_type.value
        lines.append(f"  >>> OVERALL SIGNAL: {signal_display} <<<")
        lines.append(f"  Confidence:       {result.confidence:.1f}%")
        lines.append(f"  Trend Direction:  {result.trend_direction.value}")
        lines.append(f"  Market Phase:     {result.market_phase.value}")
        lines.append("")

        lines.append("-" * 70)
        lines.append("  TRADING ACTIONS")
        lines.append("-" * 70)
        lines.append(f"  SPOT:    {result.spot_action}")
        lines.append(f"  FUTURES: {result.futures_action}")
        if result.signal_type != SignalType.HOLD:
            lines.append(f"  Leverage: {result.leverage_suggestion}")
            lines.append(f"  Position Size: {result.position_size_pct:.2f}% of portfolio")
        lines.append("")

        if result.signal_type != SignalType.HOLD:
            lines.append("-" * 70)
            lines.append("  TRADE PLAN")
            lines.append("-" * 70)
            lines.append(f"  Entry Price:     {result.entry_price:.2f}")
            lines.append(f"  Stop Loss:       {result.stop_loss:.2f}")
            lines.append(f"  Take Profit 1:   {result.take_profit_1:.2f}")
            lines.append(f"  Take Profit 2:   {result.take_profit_2:.2f}")
            lines.append(f"  Take Profit 3:   {result.take_profit_3:.2f}")
            lines.append(f"  Risk/Reward:     {result.risk_reward_ratio:.2f}")

            sl_pct = abs(result.entry_price - result.stop_loss) / result.entry_price * 100
            tp1_pct = abs(result.take_profit_1 - result.entry_price) / result.entry_price * 100
            lines.append(f"  Stop Loss %:     {sl_pct:.2f}%")
            lines.append(f"  Take Profit 1 %: {tp1_pct:.2f}%")
            lines.append("")

            lines.append("  Position Sizing Strategy:")
            lines.append(f"    - Risk per trade: {result.position_size_pct:.2f}% of portfolio")
            lines.append(f"    - ATR-based stop: {indicators.atr:.2f} ({indicators.atr_percent:.2f}%)")
            lines.append(f"    - Max loss if SL hit: {result.position_size_pct * sl_pct / 100:.2f}%")
            lines.append("")

        lines.append("-" * 70)
        lines.append("  SUPPORT & RESISTANCE LEVELS")
        lines.append("-" * 70)
        if result.resistance_levels:
            lines.append("  Resistance Levels:")
            for i, r in enumerate(result.resistance_levels):
                dist = (r - current_price) / current_price * 100
                lines.append(f"    R{i+1}: {r:.2f} (+{dist:.2f}%)")
        if result.support_levels:
            lines.append("  Support Levels:")
            for i, s in enumerate(result.support_levels):
                dist = (current_price - s) / current_price * 100
                lines.append(f"    S{i+1}: {s:.2f} (-{dist:.2f}%)")
        lines.append("")

        lines.append("-" * 70)
        lines.append("  TECHNICAL INDICATORS")
        lines.append("-" * 70)
        for key, value in result.indicators_summary.items():
            lines.append(f"  {key:20s}: {value}")
        lines.append("")

        lines.append("-" * 70)
        lines.append("  VOLUME ANALYSIS")
        lines.append("-" * 70)
        lines.append(result.volume_analysis)
        lines.append("")

        if result.patterns_detected:
            lines.append("-" * 70)
            lines.append("  CANDLESTICK PATTERNS DETECTED")
            lines.append("-" * 70)
            for p in result.patterns_detected:
                lines.append(f"    - {p}")
            lines.append("")

        lines.append("-" * 70)
        lines.append("  SIGNAL REASONS")
        lines.append("-" * 70)
        for i, reason in enumerate(result.reasons, 1):
            lines.append(f"  {i:2d}. {reason}")
        lines.append("")

        if result.warnings:
            lines.append("-" * 70)
            lines.append("  RISK WARNINGS")
            lines.append("-" * 70)
            for w in result.warnings:
                lines.append(f"  WARNING: {w}")
            lines.append("")

        lines.append("-" * 70)
        lines.append("  RISK MANAGEMENT GUIDELINES")
        lines.append("-" * 70)
        if result.signal_type != SignalType.HOLD:
            lines.append("  1. Never risk more than 2% of your portfolio on a single trade")
            lines.append("  2. Always set stop loss before entering the position")
            lines.append("  3. Take partial profits at TP1 (30%), TP2 (40%), TP3 (30%)")
            lines.append("  4. Move stop loss to breakeven after TP1 is hit")
            lines.append("  5. Monitor volume for confirmation of trend continuation")
            lines.append("  6. If ATR increases significantly, tighten stop loss")
            lines.append("  7. Do not chase if price moves more than 1 ATR from entry")
            lines.append("  8. Check for major news/events that could affect the market")
        else:
            lines.append("  HOLD signal - no active trade recommended")
            lines.append("  Wait for clearer signal before entering any position")
            lines.append("  Monitor key support/resistance levels for breakout")
        lines.append("")

        if result.futures_action != "HOLD":
            lines.append("-" * 70)
            lines.append("  FUTURES-SPECIFIC NOTES")
            lines.append("-" * 70)
            if result.futures_action == "LONG":
                lines.append("  - Long position recommended for perpetual futures")
                lines.append("  - Consider funding rate before entry")
                lines.append("  - Use cross margin for flexibility")
                lines.append("  - Set liquidation buffer of 2x the stop loss distance")
            elif result.futures_action == "SHORT":
                lines.append("  - Short position recommended for perpetual futures")
                lines.append("  - Check funding rate (positive = sellers earn)")
                lines.append("  - Use cross margin for flexibility")
                lines.append("  - Set liquidation buffer of 2x the stop loss distance")
            lines.append(f"  - Suggested Leverage: {result.leverage_suggestion}")
            lines.append("  - Auto-deposit margin: Enable if available")
            lines.append("  - Monitor liquidation price closely")
            lines.append("")

        lines.append("-" * 70)
        lines.append("  SPOT TRADING NOTES")
        lines.append("-" * 70)
        if result.spot_action == "BUY":
            lines.append("  - Spot BUY signal for long-term accumulation")
            lines.append("  - Consider DCA (Dollar Cost Averaging) approach")
            lines.append("  - Set limit orders at support levels")
            lines.append("  - Store assets in secure wallet after purchase")
        elif result.spot_action == "SELL":
            lines.append("  - Spot SELL signal - consider reducing position")
            lines.append("  - Take profits on existing holdings")
            lines.append("  - Consider setting limit sell orders at resistance")
            lines.append("  - Re-evaluate after pullback to support")
        else:
            lines.append("  - No action recommended for spot trading")
            lines.append("  - Hold existing positions")
            lines.append("  - Wait for clearer entry/exit signal")
        lines.append("")

        lines.append("=" * 70)
        lines.append("  DISCLAIMER: This is technical analysis for educational purposes")
        lines.append("  only. Trading involves significant risk. Always do your own")
        lines.append("  research and never invest more than you can afford to lose.")
        lines.append("=" * 70)
        lines.append("")

        return "\n".join(lines)


# ============================================================================
# SECTION 10: MAIN EXECUTION
# ============================================================================

def main():
    """Main entry point for the SMA 50 Trading Bot."""
    print("\n" + "=" * 70)
    print("  SMA 50 TRADING BOT v2.0")
    print("  Trend Direction & Dynamic Support/Resistance Analyzer")
    print("=" * 70)
    print()

    if len(sys.argv) < 2:
        print("[USAGE] python main.py <path_to_candles.json>")
        print("[EXAMPLE] python main.py ../../candles/candles.json")
        print()
        default_path = os.path.join(os.path.dirname(__file__), '..', '..', 'candles', 'candles.json')
        default_path = os.path.normpath(default_path)
        if os.path.exists(default_path):
            print(f"[INFO] Using default path: {default_path}")
            file_path = default_path
        else:
            print("[ERROR] No candle file specified and default not found")
            sys.exit(1)
    else:
        file_path = sys.argv[1]

    print(f"[INFO] Loading candles from: {file_path}")
    candles = load_candles(file_path)
    validate_candle_sequence(candles)

    print(f"\n[INFO] Analyzing {len(candles)} candles...")
    print(f"[INFO] Date range: {candles[0].timestamp.strftime('%Y-%m-%d')} to {candles[-1].timestamp.strftime('%Y-%m-%d')}")
    print(f"[INFO] Price range: {min(c.low for c in candles):.2f} - {max(c.high for c in candles):.2f}")
    print()

    generator = SignalGenerator(candles)
    result = generator.generate_signal()

    report = ReportGenerator.generate_report(result, candles, generator.indicators)
    print(report)

    report_filename = f"sma50_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path = os.path.join(os.path.dirname(__file__), report_filename)
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"[INFO] Report saved to: {report_path}")
    except Exception as e:
        print(f"[WARNING] Could not save report: {e}")

    print("\n[INFO] Analysis complete!")
    return result


# ============================================================================
# SECTION 11: MULTI-TIMEFRAME ANALYSIS
# ============================================================================

class MultiTimeframeAnalyzer:
    """Analyze price action across multiple simulated timeframes."""

    @staticmethod
    def aggregate_candles(candles: List[Candle], multiplier: int) -> List[Candle]:
        """Aggregate candles into higher timeframes."""
        if multiplier <= 1:
            return candles
        aggregated = []
        for i in range(0, len(candles), multiplier):
            group = candles[i:i + multiplier]
            if not group:
                continue
            agg_candle = Candle(
                open_time=group[0].open_time,
                open=group[0].open,
                high=max(c.high for c in group),
                low=min(c.low for c in group),
                close=group[-1].close,
                volume=sum(c.volume for c in group),
                quote_volume=sum(c.quote_volume for c in group),
                trades=sum(c.trades for c in group),
                taker_buy_volume=sum(c.taker_buy_volume for c in group),
                taker_buy_quote_volume=sum(c.taker_buy_quote_volume for c in group)
            )
            aggregated.append(agg_candle)
        return aggregated

    @staticmethod
    def analyze_timeframes(candles: List[Candle]) -> Dict[str, Dict[str, Any]]:
        """Perform multi-timeframe analysis."""
        timeframes = {
            '1H': 1,
            '4H': 4,
            '1D': 24
        }
        results = {}
        for tf_name, multiplier in timeframes.items():
            agg = MultiTimeframeAnalyzer.aggregate_candles(candles, multiplier)
            if len(agg) < 30:
                results[tf_name] = {
                    'trend': 'INSUFFICIENT DATA',
                    'sma50': 0,
                    'rsi': 50,
                    'macd': 0,
                    'signal': 'HOLD',
                    'strength': 0,
                    'close': agg[-1].close if agg else 0
                }
                continue
            closes = [c.close for c in agg]
            ti = TechnicalIndicators()
            sma50 = ti.sma(closes, 50)
            rsi = ti.rsi(closes)
            macd_line, macd_signal, macd_hist = ti.macd(closes)
            ema12 = ti.ema(closes, 12)
            ema26 = ti.ema(closes, 26)
            i = len(agg) - 1
            current_close = agg[i].close
            sma_val = sma50[i]
            rsi_val = rsi[i]
            macd_val = macd_line[i]
            signal_val = macd_signal[i]
            hist_val = macd_hist[i]
            hist_prev = macd_hist[i-1] if i > 0 else 0
            score = 0
            if current_close > sma_val:
                score += 2
            else:
                score -= 2
            if rsi_val > 60:
                score += 1
            elif rsi_val < 40:
                score -= 1
            if macd_val > signal_val:
                score += 2
            else:
                score -= 2
            if hist_val > hist_prev:
                score += 1
            else:
                score -= 1
            sma_slope = sma50[i] - sma50[i-1] if i > 0 else 0
            if sma_slope > 0:
                score += 1
            else:
                score -= 1
            if score >= 3:
                trend = 'BULLISH'
                sig = 'BUY'
            elif score <= -3:
                trend = 'BEARISH'
                sig = 'SELL'
            else:
                trend = 'NEUTRAL'
                sig = 'HOLD'
            results[tf_name] = {
                'trend': trend,
                'sma50': sma_val,
                'rsi': rsi_val,
                'macd': macd_val,
                'macd_signal': signal_val,
                'macd_hist': hist_val,
                'ema12': ema12[i],
                'ema26': ema26[i],
                'signal': sig,
                'strength': abs(score),
                'close': current_close,
                'sma_slope': sma_slope,
                'score': score
            }
        return results

    @staticmethod
    def get_htf_alignment(tf_results: Dict[str, Dict]) -> Tuple[str, float]:
        """Check if higher timeframes align with the signal."""
        bullish_count = 0
        bearish_count = 0
        total = len(tf_results)
        for tf, data in tf_results.items():
            if data['trend'] == 'BULLISH':
                bullish_count += 1
            elif data['trend'] == 'BEARISH':
                bearish_count += 1
        if bullish_count == total:
            return 'STRONG_BULLISH', 100.0
        elif bearish_count == total:
            return 'STRONG_BEARISH', 100.0
        elif bullish_count > bearish_count:
            alignment = bullish_count / total * 100
            return 'MODERATE_BULLISH', alignment
        elif bearish_count > bullish_count:
            alignment = bearish_count / total * 100
            return 'MODERATE_BEARISH', alignment
        else:
            return 'MIXED', 50.0


# ============================================================================
# SECTION 12: WAVE AND FIBONACCI ANALYSIS
# ============================================================================

class FibonacciAnalyzer:
    """Fibonacci retracement and extension analysis."""

    @staticmethod
    def find_swing_points(candles: List[Candle], lookback: int = 50) -> Dict[str, Any]:
        """Find swing high and swing low points."""
        start = max(0, len(candles) - lookback)
        recent = candles[start:]
        swing_high = max(c.high for c in recent)
        swing_low = min(c.low for c in recent)
        swing_high_idx = 0
        swing_low_idx = 0
        for i, c in enumerate(recent):
            if c.high == swing_high:
                swing_high_idx = i
            if c.low == swing_low:
                swing_low_idx = i
        direction = 'UP' if swing_low_idx < swing_high_idx else 'DOWN'
        return {
            'swing_high': swing_high,
            'swing_low': swing_low,
            'swing_high_idx': swing_high_idx,
            'swing_low_idx': swing_low_idx,
            'direction': direction,
            'range': swing_high - swing_low
        }

    @staticmethod
    def calculate_fib_levels(swing_high: float, swing_low: float,
                              direction: str = 'UP') -> Dict[str, float]:
        """Calculate Fibonacci retracement levels."""
        fib_ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        levels = {}
        price_range = swing_high - swing_low
        for ratio in fib_ratios:
            if direction == 'UP':
                level = swing_high - (price_range * ratio)
            else:
                level = swing_low + (price_range * ratio)
            levels[f"Fib {ratio:.1%}"] = round(level, 2)
        return levels

    @staticmethod
    def calculate_fib_extensions(swing_high: float, swing_low: float,
                                  direction: str = 'UP') -> Dict[str, float]:
        """Calculate Fibonacci extension levels."""
        extension_ratios = [1.272, 1.618, 2.0, 2.618, 3.618]
        levels = {}
        price_range = swing_high - swing_low
        for ratio in extension_ratios:
            if direction == 'UP':
                level = swing_high + (price_range * (ratio - 1.0))
            else:
                level = swing_low - (price_range * (ratio - 1.0))
            levels[f"Ext {ratio:.1%}"] = round(level, 2)
        return levels

    @staticmethod
    def analyze_fib_position(current_price: float,
                              fib_levels: Dict[str, float]) -> Dict[str, Any]:
        """Analyze current price position relative to Fibonacci levels."""
        sorted_levels = sorted(fib_levels.items(), key=lambda x: x[1])
        nearest_support = None
        nearest_resistance = None
        for name, level in sorted_levels:
            if level < current_price:
                nearest_support = (name, level)
            elif level > current_price and nearest_resistance is None:
                nearest_resistance = (name, level)
        result = {
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'in_golden_zone': False,
            'in_discount_zone': False,
            'price_position': 'unknown'
        }
        if nearest_support and nearest_resistance:
            support_level = nearest_support[1]
            resistance_level = nearest_resistance[1]
            position = (current_price - support_level) / (resistance_level - support_level)
            if 0.382 <= position <= 0.618:
                result['in_golden_zone'] = True
                result['price_position'] = 'GOLDEN ZONE (Optimal Entry)'
            elif position < 0.382:
                result['in_discount_zone'] = True
                result['price_position'] = 'DISCOUNT ZONE'
            else:
                result['price_position'] = 'PREMIUM ZONE'
        return result


class ElliottWaveAnalyzer:
    """Simplified Elliott Wave pattern detection."""

    @staticmethod
    def detect_wave_structure(candles: List[Candle], lookback: int = 30) -> Dict[str, Any]:
        """Detect potential Elliott Wave structure."""
        start = max(0, len(candles) - lookback)
        recent = candles[start:]
        if len(recent) < 10:
            return {'pattern': 'INSUFFICIENT DATA', 'confidence': 0, 'direction': 'NONE'}
        closes = [c.close for c in recent]
        highs = [c.high for c in recent]
        lows = [c.low for c in recent]
        peaks = []
        troughs = []
        for i in range(2, len(closes) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                peaks.append((i, highs[i]))
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                troughs.append((i, lows[i]))
        if len(peaks) < 2 or len(troughs) < 2:
            return {'pattern': 'INSUFFICIENT SWINGS', 'confidence': 0, 'direction': 'NONE'}
        all_swings = [(p[0], p[1], 'peak') for p in peaks] + \
                     [(t[0], t[1], 'trough') for t in troughs]
        all_swings.sort(key=lambda x: x[0])
        wave_count = len(all_swings)
        if wave_count >= 5:
            trend_direction = 'UP' if all_swings[-1][1] > all_swings[0][1] else 'DOWN'
            if trend_direction == 'UP':
                impulse_waves = sum(1 for i in range(1, len(all_swings))
                                   if all_swings[i][2] == 'peak' and
                                   all_swings[i-1][2] == 'trough' and
                                   all_swings[i][1] > all_swings[i-1][1])
            else:
                impulse_waves = sum(1 for i in range(1, len(all_swings))
                                   if all_swings[i][2] == 'trough' and
                                   all_swings[i-1][2] == 'peak' and
                                   all_swings[i][1] < all_swings[i-1][1])
            confidence = min(impulse_waves * 15 + wave_count * 5, 80)
            if wave_count == 5:
                pattern = 'IMPULSE WAVE (5-wave)'
            elif wave_count == 3:
                pattern = 'CORRECTIVE WAVE (3-wave)'
            elif wave_count >= 7:
                pattern = f'EXTENDED WAVE ({wave_count}-wave)'
            else:
                pattern = f'WAVE STRUCTURE ({wave_count} swings)'
        else:
            pattern = 'DEVELOPING PATTERN'
            trend_direction = 'SIDEWAYS'
            confidence = 20
        return {
            'pattern': pattern,
            'direction': trend_direction,
            'confidence': confidence,
            'swings': wave_count,
            'peaks': len(peaks),
            'troughs': len(troughs),
            'swing_data': all_swings[:10]
        }


# ============================================================================
# SECTION 13: VOLATILITY AND RISK METRICS
# ============================================================================

class VolatilityAnalyzer:
    """Advanced volatility and risk metrics calculation."""

    @staticmethod
    def calculate_historical_volatility(closes: List[float], period: int = 20) -> List[float]:
        """Calculate historical volatility using log returns."""
        if len(closes) < period + 1:
            return [0.0] * len(closes)
        log_returns = []
        for i in range(1, len(closes)):
            if closes[i-1] > 0 and closes[i] > 0:
                log_returns.append(math.log(closes[i] / closes[i-1]))
            else:
                log_returns.append(0.0)
        hv = [0.0] * period
        for i in range(period, len(log_returns)):
            window = log_returns[i - period + 1:i + 1]
            if len(window) > 1:
                std = statistics.stdev(window)
                hv.append(std * math.sqrt(365) * 100)
            else:
                hv.append(0.0)
        hv.insert(0, 0.0)
        return hv

    @staticmethod
    def calculate_sharpe_ratio(closes: List[float], risk_free_rate: float = 0.02,
                                period: int = 30) -> float:
        """Calculate annualized Sharpe ratio."""
        if len(closes) < period + 1:
            return 0.0
        returns = []
        for i in range(max(1, len(closes) - period), len(closes)):
            if closes[i-1] > 0:
                returns.append((closes[i] - closes[i-1]) / closes[i-1])
        if not returns:
            return 0.0
        avg_return = statistics.mean(returns)
        daily_rf = risk_free_rate / 365
        excess_returns = [r - daily_rf for r in returns]
        if not excess_returns or statistics.stdev(excess_returns) == 0:
            return 0.0
        sharpe = (statistics.mean(excess_returns) / statistics.stdev(excess_returns)) * math.sqrt(365)
        return round(sharpe, 2)

    @staticmethod
    def calculate_sortino_ratio(closes: List[float], risk_free_rate: float = 0.02,
                                 period: int = 30) -> float:
        """Calculate Sortino ratio (downside deviation only)."""
        if len(closes) < period + 1:
            return 0.0
        returns = []
        for i in range(max(1, len(closes) - period), len(closes)):
            if closes[i-1] > 0:
                returns.append((closes[i] - closes[i-1]) / closes[i-1])
        if not returns:
            return 0.0
        daily_rf = risk_free_rate / 365
        excess_returns = [r - daily_rf for r in returns]
        downside_returns = [r for r in excess_returns if r < 0]
        if not downside_returns:
            return 5.0 if statistics.mean(excess_returns) > 0 else 0.0
        downside_std = statistics.stdev(downside_returns) if len(downside_returns) > 1 else 0.01
        if downside_std == 0:
            return 5.0 if statistics.mean(excess_returns) > 0 else 0.0
        sortino = (statistics.mean(excess_returns) / downside_std) * math.sqrt(365)
        return round(sortino, 2)

    @staticmethod
    def calculate_max_drawdown(closes: List[float]) -> Dict[str, float]:
        """Calculate maximum drawdown and related metrics."""
        if not closes:
            return {'max_drawdown': 0, 'max_drawdown_pct': 0, 'current_drawdown': 0}
        peak = closes[0]
        max_dd = 0
        max_dd_pct = 0
        current_peak = closes[0]
        for price in closes:
            if price > current_peak:
                current_peak = price
            dd = current_peak - price
            dd_pct = (dd / current_peak * 100) if current_peak > 0 else 0
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
                max_dd = dd
        current_dd = current_peak - closes[-1]
        current_dd_pct = (current_dd / current_peak * 100) if current_peak > 0 else 0
        return {
            'max_drawdown': round(max_dd, 2),
            'max_drawdown_pct': round(max_dd_pct, 2),
            'current_drawdown': round(current_dd, 2),
            'current_drawdown_pct': round(current_dd_pct, 2)
        }

    @staticmethod
    def calculate_var(closes: List[float], confidence: float = 0.95,
                      period: int = 30) -> float:
        """Calculate Value at Risk (VaR)."""
        if len(closes) < period + 1:
            return 0.0
        returns = []
        for i in range(max(1, len(closes) - period), len(closes)):
            if closes[i-1] > 0:
                returns.append((closes[i] - closes[i-1]) / closes[i-1])
        if not returns:
            return 0.0
        sorted_returns = sorted(returns)
        idx = int((1 - confidence) * len(sorted_returns))
        idx = max(0, min(idx, len(sorted_returns) - 1))
        var = abs(sorted_returns[idx]) * 100
        return round(var, 2)

    @staticmethod
    def calculate_position_risk(entry_price: float, stop_loss: float,
                                 position_size_pct: float,
                                 portfolio_value: float) -> Dict[str, float]:
        """Calculate detailed position risk metrics."""
        risk_per_unit = abs(entry_price - stop_loss)
        risk_pct = risk_per_unit / entry_price * 100
        position_value = portfolio_value * (position_size_pct / 100)
        units = position_value / entry_price if entry_price > 0 else 0
        max_loss = units * risk_per_unit
        max_loss_pct = max_loss / portfolio_value * 100 if portfolio_value > 0 else 0
        return {
            'risk_per_unit': round(risk_per_unit, 2),
            'risk_pct': round(risk_pct, 2),
            'position_value': round(position_value, 2),
            'units': round(units, 6),
            'max_loss': round(max_loss, 2),
            'max_loss_pct': round(max_loss_pct, 2)
        }


# ============================================================================
# SECTION 14: MARKET STRUCTURE ANALYSIS
# ============================================================================

class MarketStructureAnalyzer:
    """Analyze market structure and institutional order flow."""

    @staticmethod
    def analyze_order_flow(candles: List[Candle], lookback: int = 20) -> Dict[str, Any]:
        """Analyze order flow patterns."""
        start = max(0, len(candles) - lookback)
        recent = candles[start:]
        total_volume = sum(c.volume for c in recent)
        total_buy_volume = sum(c.taker_buy_volume for c in recent)
        total_sell_volume = total_volume - total_buy_volume
        buy_ratio = total_buy_volume / total_volume if total_volume > 0 else 0.5
        consecutive_bullish = 0
        consecutive_bearish = 0
        max_consecutive_bullish = 0
        max_consecutive_bearish = 0
        for c in recent:
            if c.is_bullish:
                consecutive_bullish += 1
                consecutive_bearish = 0
                max_consecutive_bullish = max(max_consecutive_bullish, consecutive_bullish)
            else:
                consecutive_bearish += 1
                consecutive_bullish = 0
                max_consecutive_bearish = max(max_consecutive_bearish, consecutive_bearish)
        large_bars = 0
        small_bars = 0
        avg_range = statistics.mean([c.total_range for c in recent]) if recent else 0
        for c in recent:
            if c.total_range > avg_range * 1.5:
                large_bars += 1
            elif c.total_range < avg_range * 0.5:
                small_bars += 1
        result = {
            'buy_volume_ratio': round(buy_ratio, 4),
            'sell_volume_ratio': round(1 - buy_ratio, 4),
            'total_volume': round(total_volume, 2),
            'total_buy_volume': round(total_buy_volume, 2),
            'total_sell_volume': round(total_sell_volume, 2),
            'max_consecutive_bullish': max_consecutive_bullish,
            'max_consecutive_bearish': max_consecutive_bearish,
            'large_bars': large_bars,
            'small_bars': small_bars,
            'avg_range': round(avg_range, 2),
            'flow_bias': 'BUYERS' if buy_ratio > 0.55 else 'SELLERS' if buy_ratio < 0.45 else 'BALANCED',
            'activity_level': 'HIGH' if large_bars > len(recent) * 0.3 else
                            'LOW' if small_bars > len(recent) * 0.5 else 'NORMAL'
        }
        return result

    @staticmethod
    def detect_liquidity_zones(candles: List[Candle]) -> Dict[str, List[float]]:
        """Detect potential liquidity zones (areas of high trading activity)."""
        price_volume_map = defaultdict(float)
        for c in candles:
            typical_price = (c.high + c.low + c.close) / 3.0
            bucket = round(typical_price, 0)
            price_volume_map[bucket] += c.volume
        sorted_zones = sorted(price_volume_map.items(), key=lambda x: x[1], reverse=True)
        high_liquidity = [z[0] for z in sorted_zones[:10]]
        low_liquidity_zones = []
        price_range = max(c.high for c in candles) - min(c.low for c in candles)
        if price_range > 0:
            step = price_range / 20
            for i in range(20):
                level = min(c.low for c in candles) + (i * step)
                vol_at_level = sum(c.volume for c in candles
                                  if abs((c.high + c.low) / 2 - level) < step)
                if vol_at_level < statistics.mean([c.volume for c in candles]) * 0.3:
                    low_liquidity_zones.append(round(level, 2))
        return {
            'high_liquidity_zones': sorted(high_liquidity),
            'low_liquidity_zones': low_liquidity_zones[:10],
            'high_volume_node': sorted_zones[0][0] if sorted_zones else 0,
            'low_volume_node': low_liquidity_zones[0] if low_liquidity_zones else 0
        }

    @staticmethod
    def analyze_price_efficiency(candles: List[Candle], period: int = 20) -> Dict[str, Any]:
        """Analyze price efficiency (how directly price moves to target)."""
        if len(candles) < period:
            return {'efficiency': 0, 'direction': 'INSUFFICIENT DATA'}
        start = len(candles) - period
        net_move = candles[-1].close - candles[start].open
        total_path = sum(abs(candles[i].close - candles[i-1].close)
                        for i in range(start + 1, len(candles)))
        efficiency = abs(net_move) / total_path * 100 if total_path > 0 else 0
        if net_move > 0:
            direction = 'UPWARD'
        elif net_move < 0:
            direction = 'DOWNWARD'
        else:
            direction = 'SIDEWAYS'
        return {
            'efficiency': round(efficiency, 2),
            'direction': direction,
            'net_move': round(net_move, 2),
            'total_path': round(total_path, 2),
            'efficiency_rating': 'HIGH' if efficiency > 60 else
                               'MEDIUM' if efficiency > 30 else 'LOW'
        }


# ============================================================================
# SECTION 15: CORRELATION AND REGIME DETECTION
# ============================================================================

class MarketRegimeDetector:
    """Detect current market regime (trending, ranging, volatile, etc.)."""

    @staticmethod
    def detect_regime(candles: List[Candle], indicators: IndicatorValues) -> Dict[str, Any]:
        """Detect current market regime."""
        closes = [c.close for c in candles]
        ranges = [c.total_range for c in candles]
        volumes = [c.volume for c in candles]
        recent_ranges = ranges[-20:] if len(ranges) >= 20 else ranges
        recent_volumes = volumes[-20:] if len(volumes) >= 20 else volumes
        avg_range = statistics.mean(recent_ranges) if recent_ranges else 0
        avg_volume = statistics.mean(recent_volumes) if recent_volumes else 0
        latest_range = ranges[-1] if ranges else 0
        latest_volume = volumes[-1] if volumes else 0
        volatility_regime = 'NORMAL'
        if latest_range > avg_range * 2:
            volatility_regime = 'EXTREMELY HIGH'
        elif latest_range > avg_range * 1.5:
            volatility_regime = 'HIGH'
        elif latest_range < avg_range * 0.5:
            volatility_regime = 'LOW'
        elif latest_range < avg_range * 0.3:
            volatility_regime = 'EXTREMELY LOW'
        trend_regime = 'RANGING'
        if indicators.adx > 30:
            trend_regime = 'STRONG TRENDING'
        elif indicators.adx > 20:
            trend_regime = 'TRENDING'
        elif indicators.adx < 15:
            trend_regime = 'DEAD CALM'
        volume_regime = 'NORMAL'
        if latest_volume > avg_volume * 2:
            volume_regime = 'EXTREMELY HIGH'
        elif latest_volume > avg_volume * 1.5:
            volume_regime = 'HIGH'
        elif latest_volume < avg_volume * 0.5:
            volume_regime = 'LOW'
        price_range_pct = (max(c.high for c in candles[-20:]) -
                          min(c.low for c in candles[-20:])) / candles[-1].close * 100
        bb_squeeze = indicators.bb_width < 3
        regime = 'UNKNOWN'
        strategy = ''
        if trend_regime in ['STRONG TRENDING', 'TRENDING']:
            if volatility_regime in ['HIGH', 'EXTREMELY HIGH']:
                regime = 'VOLATILE TREND'
                strategy = 'Trend following with wider stops'
            else:
                regime = 'CALM TREND'
                strategy = 'Trend following with normal stops'
        elif trend_regime in ['RANGING', 'DEAD CALM']:
            if bb_squeeze:
                regime = 'SQUEEZE/BREAKOUT IMMINENT'
                strategy = 'Prepare for breakout, wait for confirmation'
            elif volatility_regime in ['HIGH', 'EXTREMELY HIGH']:
                regime = 'CHOPPY/RANGING HIGH VOL'
                strategy = 'Range trading with caution, avoid large positions'
            else:
                regime = 'CALM RANGING'
                strategy = 'Range trading, buy support sell resistance'
        else:
            regime = 'TRANSITIONING'
            strategy = 'Wait for regime to stabilize'
        return {
            'regime': regime,
            'strategy': strategy,
            'trend_regime': trend_regime,
            'volatility_regime': volatility_regime,
            'volume_regime': volume_regime,
            'bb_squeeze': bb_squeeze,
            'price_range_pct': round(price_range_pct, 2),
            'adx': round(indicators.adx, 2),
            'bb_width': round(indicators.bb_width, 2)
        }


# ============================================================================
# SECTION 16: ADVANCED PATTERN DETECTION
# ============================================================================

class AdvancedPatternDetector:
    """Advanced chart pattern detection beyond basic candlesticks."""

    @staticmethod
    def detect_double_top_bottom(candles: List[Candle],
                                  lookback: int = 40) -> Optional[Dict[str, Any]]:
        """Detect double top or double bottom patterns."""
        start = max(0, len(candles) - lookback)
        recent = candles[start:]
        if len(recent) < 15:
            return None
        highs = [c.high for c in recent]
        lows = [c.low for c in recent]
        peaks = []
        troughs = []
        for i in range(2, len(highs) - 2):
            if highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and \
               highs[i] >= highs[i+1] and highs[i] >= highs[i+2]:
                peaks.append((i, highs[i]))
            if lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and \
               lows[i] <= lows[i+1] and lows[i] <= lows[i+2]:
                troughs.append((i, lows[i]))
        if len(peaks) >= 2:
            p1_idx, p1_val = peaks[-2]
            p2_idx, p2_val = peaks[-1]
            if abs(p1_val - p2_val) / p1_val < 0.02 and p2_idx - p1_idx >= 5:
                neckline = min(lows[p1_idx:p2_idx+1])
                if candles[-1].close < neckline:
                    return {
                        'pattern': 'DOUBLE TOP',
                        'type': 'BEARISH',
                        'peak1': p1_val,
                        'peak2': p2_val,
                        'neckline': neckline,
                        'target': neckline - (p1_val - neckline),
                        'confirmed': True
                    }
                else:
                    return {
                        'pattern': 'DOUBLE TOP (forming)',
                        'type': 'BEARISH',
                        'peak1': p1_val,
                        'peak2': p2_val,
                        'neckline': neckline,
                        'target': neckline - (p1_val - neckline),
                        'confirmed': False
                    }
        if len(troughs) >= 2:
            t1_idx, t1_val = troughs[-2]
            t2_idx, t2_val = troughs[-1]
            if abs(t1_val - t2_val) / t1_val < 0.02 and t2_idx - t1_idx >= 5:
                neckline = max(highs[t1_idx:t2_idx+1])
                if candles[-1].close > neckline:
                    return {
                        'pattern': 'DOUBLE BOTTOM',
                        'type': 'BULLISH',
                        'trough1': t1_val,
                        'trough2': t2_val,
                        'neckline': neckline,
                        'target': neckline + (neckline - t1_val),
                        'confirmed': True
                    }
                else:
                    return {
                        'pattern': 'DOUBLE BOTTOM (forming)',
                        'type': 'BULLISH',
                        'trough1': t1_val,
                        'trough2': t2_val,
                        'neckline': neckline,
                        'target': neckline + (neckline - t1_val),
                        'confirmed': False
                    }
        return None

    @staticmethod
    def detect_head_and_shoulders(candles: List[Candle],
                                   lookback: int = 40) -> Optional[Dict[str, Any]]:
        """Detect head and shoulders or inverse head and shoulders."""
        start = max(0, len(candles) - lookback)
        recent = candles[start:]
        if len(recent) < 20:
            return None
        highs = [c.high for c in recent]
        lows = [c.low for c in recent]
        peaks = []
        troughs = []
        for i in range(2, len(highs) - 2):
            if highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and \
               highs[i] >= highs[i+1] and highs[i] >= highs[i+2]:
                peaks.append((i, highs[i]))
            if lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and \
               lows[i] <= lows[i+1] and lows[i] <= lows[i+2]:
                troughs.append((i, lows[i]))
        if len(peaks) >= 3:
            p1_idx, p1 = peaks[-3]
            p2_idx, p2 = peaks[-2]
            p3_idx, p3 = peaks[-1]
            if p2 > p1 and p2 > p3 and abs(p1 - p3) / p1 < 0.03:
                neckline = min(lows[p1_idx:p3_idx+1])
                if candles[-1].close < neckline:
                    return {
                        'pattern': 'HEAD & SHOULDERS',
                        'type': 'BEARISH',
                        'left_shoulder': p1,
                        'head': p2,
                        'right_shoulder': p3,
                        'neckline': neckline,
                        'target': neckline - (p2 - neckline),
                        'confirmed': True
                    }
        if len(troughs) >= 3:
            t1_idx, t1 = troughs[-3]
            t2_idx, t2 = troughs[-2]
            t3_idx, t3 = troughs[-1]
            if t2 < t1 and t2 < t3 and abs(t1 - t3) / t1 < 0.03:
                neckline = max(highs[t1_idx:t3_idx+1])
                if candles[-1].close > neckline:
                    return {
                        'pattern': 'INVERSE HEAD & SHOULDERS',
                        'type': 'BULLISH',
                        'left_shoulder': t1,
                        'head': t2,
                        'right_shoulder': t3,
                        'neckline': neckline,
                        'target': neckline + (neckline - t2),
                        'confirmed': True
                    }
        return None

    @staticmethod
    def detect_triangle_pattern(candles: List[Candle],
                                 lookback: int = 30) -> Optional[Dict[str, Any]]:
        """Detect ascending, descending, or symmetric triangle patterns."""
        start = max(0, len(candles) - lookback)
        recent = candles[start:]
        if len(recent) < 10:
            return None
        highs = [c.high for c in recent]
        lows = [c.low for c in recent]
        upper_trend = []
        lower_trend = []
        for i in range(len(recent)):
            upper_trend.append(highs[i])
            lower_trend.append(lows[i])
        upper_slope = (upper_trend[-1] - upper_trend[0]) / len(upper_trend)
        lower_slope = (lower_trend[-1] - lower_trend[0]) / len(lower_trend)
        if abs(upper_slope) < 0.001 and lower_slope > 0.001:
            return {
                'pattern': 'ASCENDING TRIANGLE',
                'type': 'BULLISH',
                'upper_bound': max(highs),
                'lower_bound': min(lows[-5:]),
                'slope_upper': round(upper_slope, 4),
                'slope_lower': round(lower_slope, 4)
            }
        elif upper_slope < -0.001 and abs(lower_slope) < 0.001:
            return {
                'pattern': 'DESCENDING TRIANGLE',
                'type': 'BEARISH',
                'upper_bound': max(highs[-5:]),
                'lower_bound': min(lows),
                'slope_upper': round(upper_slope, 4),
                'slope_lower': round(lower_slope, 4)
            }
        elif upper_slope < -0.001 and lower_slope > 0.001:
            return {
                'pattern': 'SYMMETRIC TRIANGLE',
                'type': 'NEUTRAL',
                'upper_bound': max(highs),
                'lower_bound': min(lows),
                'slope_upper': round(upper_slope, 4),
                'slope_lower': round(lower_slope, 4)
            }
        return None

    @staticmethod
    def detect_wedge_pattern(candles: List[Candle],
                              lookback: int = 30) -> Optional[Dict[str, Any]]:
        """Detect rising or falling wedge patterns."""
        start = max(0, len(candles) - lookback)
        recent = candles[start:]
        if len(recent) < 10:
            return None
        highs = [c.high for c in recent]
        lows = [c.low for c in recent]
        upper_slope = (highs[-1] - highs[0]) / len(highs)
        lower_slope = (lows[-1] - lows[0]) / len(lows)
        if upper_slope > 0.001 and lower_slope > 0.001 and upper_slope < lower_slope:
            return {
                'pattern': 'RISING WEDGE',
                'type': 'BEARISH',
                'slope_upper': round(upper_slope, 4),
                'slope_lower': round(lower_slope, 4)
            }
        elif upper_slope < -0.001 and lower_slope < -0.001 and abs(upper_slope) > abs(lower_slope):
            return {
                'pattern': 'FALLING WEDGE',
                'type': 'BULLISH',
                'slope_upper': round(upper_slope, 4),
                'slope_lower': round(lower_slope, 4)
            }
        return None


# ============================================================================
# SECTION 17: SENTIMENT AND CONFIDENCE SCORING
# ============================================================================

class ConfidenceScorer:
    """Calculate overall confidence score from multiple factors."""

    @staticmethod
    def calculate_comprehensive_confidence(
        trend_direction: TrendDirection,
        market_phase: MarketPhase,
        indicators: IndicatorValues,
        patterns: List[CandlePattern],
        vol_data: Dict[str, Any],
        tf_alignment: Dict[str, Any],
        regime: Dict[str, Any],
        fib_analysis: Dict[str, Any],
        wave_analysis: Dict[str, Any],
        order_flow: Dict[str, Any],
        sharpe: float,
        max_dd: Dict[str, float]
    ) -> Dict[str, Any]:
        """Calculate comprehensive confidence score."""
        factors = {}
        trend_score = 0
        if trend_direction in [TrendDirection.STRONG_UP, TrendDirection.STRONG_DOWN]:
            trend_score = 25
        elif trend_direction in [TrendDirection.UP, TrendDirection.DOWN]:
            trend_score = 15
        else:
            trend_score = 5
        factors['trend_strength'] = trend_score
        phase_score = 0
        if market_phase in [MarketPhase.MARKUP, MarketPhase.ACCUMULATION]:
            phase_score = 15
        elif market_phase in [MarketPhase.MARKDOWN, MarketPhase.DISTRIBUTION]:
            phase_score = 15
        else:
            phase_score = 5
        factors['market_phase'] = phase_score
        indicator_score = 0
        if indicators.rsi < 30 or indicators.rsi > 70:
            indicator_score += 5
        if abs(indicators.macd_histogram) > 0:
            indicator_score += 3
        if indicators.adx > 25:
            indicator_score += 5
        if indicators.stoch_k < 20 or indicators.stoch_k > 80:
            indicator_score += 3
        indicator_score = min(indicator_score, 15)
        factors['indicator_alignment'] = indicator_score
        pattern_score = 0
        bullish_patterns = [CandlePattern.ENGULFING_BULLISH, CandlePattern.MORNING_STAR,
                           CandlePattern.HAMMER, CandlePattern.THREE_WHITE_SOLDIERS]
        bearish_patterns = [CandlePattern.ENGULFING_BEARISH, CandlePattern.EVENING_STAR,
                           CandlePattern.SHOOTING_STAR, CandlePattern.THREE_BLACK_CROWS]
        for p in patterns:
            if p in bullish_patterns or p in bearish_patterns:
                pattern_score += 3
        pattern_score = min(pattern_score, 12)
        factors['candlestick_patterns'] = pattern_score
        vol_score = 0
        if vol_data['volume_ratio'] > 1.5:
            vol_score += 5
        if vol_data['divergence'] != 'none':
            vol_score += 3
        if vol_data['accumulation'] or vol_data['distribution']:
            vol_score += 2
        vol_score = min(vol_score, 10)
        factors['volume_analysis'] = vol_score
        tf_score = 0
        if tf_alignment.get('alignment_pct', 0) > 80:
            tf_score = 10
        elif tf_alignment.get('alignment_pct', 0) > 60:
            tf_score = 7
        elif tf_alignment.get('alignment_pct', 0) > 40:
            tf_score = 4
        else:
            tf_score = 1
        factors['timeframe_alignment'] = tf_score
        regime_score = 0
        if regime.get('regime', '') in ['CALM TREND', 'VOLATILE TREND']:
            regime_score = 8
        elif regime.get('regime', '') in ['SQUEEZE/BREAKOUT IMMINENT']:
            regime_score = 6
        elif regime.get('regime', '') in ['CALM RANGING']:
            regime_score = 5
        else:
            regime_score = 2
        factors['market_regime'] = regime_score
        fib_score = 0
        if fib_analysis.get('in_golden_zone', False):
            fib_score = 5
        elif fib_analysis.get('in_discount_zone', False):
            fib_score = 3
        else:
            fib_score = 1
        factors['fibonacci_position'] = fib_score
        wave_score = 0
        if wave_analysis.get('confidence', 0) > 50:
            wave_score = 5
        elif wave_analysis.get('confidence', 0) > 30:
            wave_score = 3
        else:
            wave_score = 1
        factors['wave_structure'] = wave_score
        flow_score = 0
        if order_flow.get('flow_bias', '') in ['BUYERS', 'SELLERS']:
            flow_score = 5
        else:
            flow_score = 2
        factors['order_flow'] = flow_score
        risk_score = 0
        if sharpe > 1:
            risk_score += 3
        elif sharpe > 0:
            risk_score += 1
        if max_dd.get('max_drawdown_pct', 100) < 10:
            risk_score += 2
        risk_score = min(risk_score, 5)
        factors['risk_metrics'] = risk_score
        total = sum(factors.values())
        max_possible = 25 + 15 + 15 + 12 + 10 + 10 + 8 + 5 + 5 + 5 + 5
        confidence_pct = (total / max_possible) * 100
        confidence_pct = min(confidence_pct, 95)
        return {
            'total_score': total,
            'max_possible': max_possible,
            'confidence_pct': round(confidence_pct, 1),
            'factors': factors,
            'rating': 'HIGH' if confidence_pct > 70 else
                     'MEDIUM' if confidence_pct > 45 else 'LOW'
        }


# ============================================================================
# SECTION 18: ENHANCED SIGNAL GENERATOR
# ============================================================================

class EnhancedSignalGenerator:
    """Enhanced signal generator with all advanced analysis modules."""

    def __init__(self, candles: List[Candle]):
        self.candles = candles
        self.closes = [c.close for c in candles]
        self.ti = TechnicalIndicators()
        self.mtf = MultiTimeframeAnalyzer()
        self.fib = FibonacciAnalyzer()
        self.ew = ElliottWaveAnalyzer()
        self.va_vol = VolatilityAnalyzer()
        self.ms = MarketStructureAnalyzer()
        self.mrd = MarketRegimeDetector()
        self.apd = AdvancedPatternDetector()
        self.cs = ConfidenceScorer()
        self.indicators = IndicatorValues()

    def run_full_analysis(self) -> Dict[str, Any]:
        """Run the complete enhanced analysis."""
        print("\n[INFO] Running enhanced analysis modules...")
        closes = self.closes
        i = len(closes) - 1
        sma50 = self.ti.sma(closes, 50)
        sma50_prev = sma50[i-1] if i > 0 else sma50[i]
        sma50_prev2 = sma50[i-2] if i > 1 else sma50[i]
        rsi = self.ti.rsi(closes)
        macd_line, macd_signal, macd_hist = self.ti.macd(closes)
        bb_upper, bb_mid, bb_lower = self.ti.bollinger_bands(closes)
        adx, plus_di, minus_di = self.ti.adx(self.candles)
        stoch_k, stoch_d = self.ti.stochastic(self.candles)
        obv = self.ti.obv(self.candles)
        vwap = self.ti.vwap(self.candles)
        atr = self.ti.atr(self.candles)
        cci = self.ti.cci(self.candles)
        mfi = self.ti.money_flow_index(self.candles)
        wr = self.ti.williams_r(self.candles)
        mom = self.ti.momentum(closes)
        roc = self.ti.rate_of_change(closes)
        self.indicators = IndicatorValues(
            sma50=sma50[i], sma50_prev=sma50_prev, sma50_prev2=sma50_prev2,
            rsi=rsi[i], rsi_prev=rsi[i-1] if i > 0 else 50,
            macd_line=macd_line[i], macd_signal=macd_signal[i],
            macd_histogram=macd_hist[i],
            macd_histogram_prev=macd_hist[i-1] if i > 0 else 0,
            bb_upper=bb_upper[i], bb_middle=bb_mid[i], bb_lower=bb_lower[i],
            bb_width=((bb_upper[i] - bb_lower[i]) / bb_mid[i] * 100) if bb_mid[i] > 0 else 0,
            atr=atr[i], atr_percent=(atr[i] / closes[i] * 100) if closes[i] > 0 else 0,
            obv=obv[i], obv_sma=sum(obv[-20:]) / min(20, len(obv)),
            volume_sma=sum(c.volume for c in self.candles[-20:]) / min(20, len(self.candles)),
            stoch_k=stoch_k[i], stoch_d=stoch_d[i],
            vwap=vwap[i], momentum=mom[i], roc=roc[i],
            adx=adx[i], plus_di=plus_di[i], minus_di=minus_di[i],
            cci=cci[i], mfi=mfi[i], williams_r=wr[i]
        )
        print("[INFO] Multi-timeframe analysis...")
        tf_results = self.mtf.analyze_timeframes(self.candles)
        htf_alignment, alignment_pct = self.mtf.get_htf_alignment(tf_results)
        print("[INFO] Fibonacci analysis...")
        fib_swings = self.fib.find_swing_points(self.candles)
        fib_levels = self.fib.calculate_fib_levels(
            fib_swings['swing_high'], fib_swings['swing_low'], fib_swings['direction']
        )
        fib_ext = self.fib.calculate_fib_extensions(
            fib_swings['swing_high'], fib_swings['swing_low'], fib_swings['direction']
        )
        fib_position = self.fib.analyze_fib_position(closes[-1], fib_levels)
        print("[INFO] Elliott Wave analysis...")
        wave_analysis = self.ew.detect_wave_structure(self.candles)
        print("[INFO] Volatility analysis...")
        hv = self.va_vol.calculate_historical_volatility(closes)
        sharpe = self.va_vol.calculate_sharpe_ratio(closes)
        sortino = self.va_vol.calculate_sortino_ratio(closes)
        max_dd = self.va_vol.calculate_max_drawdown(closes)
        var_95 = self.va_vol.calculate_var(closes, 0.95)
        print("[INFO] Market structure analysis...")
        order_flow = self.ms.analyze_order_flow(self.candles)
        liquidity = self.ms.detect_liquidity_zones(self.candles)
        efficiency = self.ms.analyze_price_efficiency(self.candles)
        print("[INFO] Market regime detection...")
        regime = self.mrd.detect_regime(self.candles, self.indicators)
        print("[INFO] Advanced pattern detection...")
        dt_db = self.apd.detect_double_top_bottom(self.candles)
        hs_ihs = self.apd.detect_head_and_shoulders(self.candles)
        triangle = self.apd.detect_triangle_pattern(self.candles)
        wedge = self.apd.detect_wedge_pattern(self.candles)
        advanced_patterns = []
        if dt_db:
            advanced_patterns.append(dt_db)
        if hs_ihs:
            advanced_patterns.append(hs_ihs)
        if triangle:
            advanced_patterns.append(triangle)
        if wedge:
            advanced_patterns.append(wedge)
        print("[INFO] Calculating confidence score...")
        confidence_data = self.cs.calculate_comprehensive_confidence(
            trend_direction=TrendDirection.SIDEWAYS,
            market_phase=MarketPhase.SIDEWAYS,
            indicators=self.indicators,
            patterns=[],
            vol_data={'volume_ratio': order_flow.get('buy_volume_ratio', 0.5),
                     'divergence': 'none',
                     'accumulation': order_flow.get('flow_bias') == 'BUYERS',
                     'distribution': order_flow.get('flow_bias') == 'SELLERS'},
            tf_alignment={'alignment_pct': alignment_pct},
            regime=regime,
            fib_analysis=fib_position,
            wave_analysis=wave_analysis,
            order_flow=order_flow,
            sharpe=sharpe,
            max_dd=max_dd
        )
        return {
            'indicators': self.indicators,
            'multi_timeframe': tf_results,
            'htf_alignment': htf_alignment,
            'htf_alignment_pct': alignment_pct,
            'fibonacci': {
                'levels': fib_levels,
                'extensions': fib_ext,
                'position': fib_position,
                'swings': fib_swings
            },
            'elliott_wave': wave_analysis,
            'volatility': {
                'historical_volatility': round(hv[-1] if hv else 0, 2),
                'sharpe_ratio': sharpe,
                'sortino_ratio': sortino,
                'max_drawdown': max_dd,
                'var_95': var_95
            },
            'market_structure': {
                'order_flow': order_flow,
                'liquidity_zones': liquidity,
                'efficiency': efficiency
            },
            'regime': regime,
            'advanced_patterns': advanced_patterns,
            'confidence': confidence_data
        }


# ============================================================================
# SECTION 19: ENHANCED REPORT GENERATOR
# ============================================================================

class EnhancedReportGenerator:
    """Generate enhanced analysis reports with advanced metrics."""

    @staticmethod
    def generate_enhanced_section(enhanced_data: Dict[str, Any],
                                   candles: List[Candle]) -> str:
        """Generate additional report sections from enhanced analysis."""
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("         ENHANCED ANALYSIS - ADVANCED METRICS")
        lines.append("=" * 70)
        lines.append("")

        mtf = enhanced_data.get('multi_timeframe', {})
        lines.append("-" * 70)
        lines.append("  MULTI-TIMEFRAME ANALYSIS")
        lines.append("-" * 70)
        for tf, data in mtf.items():
            trend_icon = ">>>" if data['trend'] == 'BULLISH' else "<<<" if data['trend'] == 'BEARISH' else "==="
            lines.append(f"  {tf:4s}: {data['trend']:10s} {trend_icon} "
                        f"SMA50={data.get('sma50', 0):.2f} RSI={data.get('rsi', 50):.1f} "
                        f"MACD={data.get('macd', 0):.4f} Signal={data.get('signal', 'N/A')}")
        htf = enhanced_data.get('htf_alignment', 'N/A')
        htf_pct = enhanced_data.get('htf_alignment_pct', 0)
        lines.append(f"  HTF Alignment: {htf} ({htf_pct:.0f}%)")
        lines.append("")

        fib = enhanced_data.get('fibonacci', {})
        lines.append("-" * 70)
        lines.append("  FIBONACCI ANALYSIS")
        lines.append("-" * 70)
        fib_levels = fib.get('levels', {})
        for name, level in fib_levels.items():
            lines.append(f"    {name:12s}: {level:.2f}")
        fib_ext = fib.get('extensions', {})
        if fib_ext:
            lines.append("  Extensions:")
            for name, level in fib_ext.items():
                lines.append(f"    {name:12s}: {level:.2f}")
        fib_pos = fib.get('position', {})
        lines.append(f"  Price Position: {fib_pos.get('price_position', 'N/A')}")
        lines.append("")

        wave = enhanced_data.get('elliott_wave', {})
        lines.append("-" * 70)
        lines.append("  ELLIOTT WAVE ANALYSIS")
        lines.append("-" * 70)
        lines.append(f"  Pattern:  {wave.get('pattern', 'N/A')}")
        lines.append(f"  Direction: {wave.get('direction', 'N/A')}")
        lines.append(f"  Confidence: {wave.get('confidence', 0)}%")
        lines.append(f"  Swings:   {wave.get('swings', 0)}")
        lines.append("")

        vol = enhanced_data.get('volatility', {})
        lines.append("-" * 70)
        lines.append("  VOLATILITY & RISK METRICS")
        lines.append("-" * 70)
        lines.append(f"  Historical Volatility: {vol.get('historical_volatility', 0):.2f}%")
        lines.append(f"  Sharpe Ratio:         {vol.get('sharpe_ratio', 0):.2f}")
        lines.append(f"  Sortino Ratio:        {vol.get('sortino_ratio', 0):.2f}")
        max_dd = vol.get('max_drawdown', {})
        lines.append(f"  Max Drawdown:         {max_dd.get('max_drawdown_pct', 0):.2f}%")
        lines.append(f"  Current Drawdown:     {max_dd.get('current_drawdown_pct', 0):.2f}%")
        lines.append(f"  VaR (95%):            {vol.get('var_95', 0):.2f}%")
        lines.append("")

        ms = enhanced_data.get('market_structure', {})
        of = ms.get('order_flow', {})
        lines.append("-" * 70)
        lines.append("  MARKET STRUCTURE & ORDER FLOW")
        lines.append("-" * 70)
        lines.append(f"  Buy Volume Ratio:   {of.get('buy_volume_ratio', 0):.1%}")
        lines.append(f"  Sell Volume Ratio:  {of.get('sell_volume_ratio', 0):.1%}")
        lines.append(f"  Flow Bias:          {of.get('flow_bias', 'N/A')}")
        lines.append(f"  Activity Level:     {of.get('activity_level', 'N/A')}")
        lines.append(f"  Max Consec Bullish: {of.get('max_consecutive_bullish', 0)}")
        lines.append(f"  Max Consec Bearish: {of.get('max_consecutive_bearish', 0)}")
        lines.append(f"  Large Bars:         {of.get('large_bars', 0)}")
        lines.append(f"  Small Bars:         {of.get('small_bars', 0)}")
        liq = ms.get('liquidity_zones', {})
        lines.append(f"  High Volume Node:   {liq.get('high_volume_node', 0):.2f}")
        lines.append(f"  Low Volume Node:    {liq.get('low_volume_node', 0):.2f}")
        eff = ms.get('efficiency', {})
        lines.append(f"  Price Efficiency:   {eff.get('efficiency', 0):.1f}% ({eff.get('efficiency_rating', 'N/A')})")
        lines.append(f"  Net Price Move:     {eff.get('net_move', 0):.2f}")
        lines.append("")

        regime = enhanced_data.get('regime', {})
        lines.append("-" * 70)
        lines.append("  MARKET REGIME")
        lines.append("-" * 70)
        lines.append(f"  Current Regime:     {regime.get('regime', 'N/A')}")
        lines.append(f"  Strategy:           {regime.get('strategy', 'N/A')}")
        lines.append(f"  Trend Regime:       {regime.get('trend_regime', 'N/A')}")
        lines.append(f"  Volatility Regime:  {regime.get('volatility_regime', 'N/A')}")
        lines.append(f"  Volume Regime:      {regime.get('volume_regime', 'N/A')}")
        lines.append(f"  BB Squeeze:         {'YES' if regime.get('bb_squeeze', False) else 'NO'}")
        lines.append(f"  Price Range (20):   {regime.get('price_range_pct', 0):.2f}%")
        lines.append("")

        patterns = enhanced_data.get('advanced_patterns', [])
        if patterns:
            lines.append("-" * 70)
            lines.append("  ADVANCED CHART PATTERNS")
            lines.append("-" * 70)
            for p in patterns:
                status = "CONFIRMED" if p.get('confirmed', False) else "FORMING"
                lines.append(f"  - {p.get('pattern', 'N/A')} ({p.get('type', 'N/A')}) [{status}]")
                if 'target' in p:
                    lines.append(f"    Target: {p['target']:.2f}")
                if 'neckline' in p:
                    lines.append(f"    Neckline: {p['neckline']:.2f}")
            lines.append("")

        conf = enhanced_data.get('confidence', {})
        lines.append("-" * 70)
        lines.append("  COMPREHENSIVE CONFIDENCE SCORE")
        lines.append("-" * 70)
        lines.append(f"  Overall Score: {conf.get('total_score', 0)}/{conf.get('max_possible', 100)}")
        lines.append(f"  Confidence:    {conf.get('confidence_pct', 0):.1f}%")
        lines.append(f"  Rating:        {conf.get('rating', 'N/A')}")
        factors = conf.get('factors', {})
        if factors:
            lines.append("  Factor Breakdown:")
            for factor, score in factors.items():
                factor_name = factor.replace('_', ' ').title()
                lines.append(f"    {factor_name:25s}: {score}")
        lines.append("")

        return "\n".join(lines)


# ============================================================================
# SECTION 20: ENHANCED MAIN EXECUTION
# ============================================================================

def main():
    """Main entry point for the SMA 50 Trading Bot with enhanced analysis."""
    print("\n" + "=" * 70)
    print("  SMA 50 TRADING BOT v2.0 - ENHANCED EDITION")
    print("  Trend Direction & Dynamic Support/Resistance Analyzer")
    print("  + Multi-Timeframe, Fibonacci, Elliott Wave, Volatility Analysis")
    print("=" * 70)
    print()

    if len(sys.argv) < 2:
        print("[USAGE] python main.py <path_to_candles.json>")
        print("[EXAMPLE] python main.py ../../candles/candles.json")
        print()
        default_path = os.path.join(os.path.dirname(__file__), '..', '..', 'candles', 'candles.json')
        default_path = os.path.normpath(default_path)
        if os.path.exists(default_path):
            print(f"[INFO] Using default path: {default_path}")
            file_path = default_path
        else:
            print("[ERROR] No candle file specified and default not found")
            sys.exit(1)
    else:
        file_path = sys.argv[1]

    print(f"[INFO] Loading candles from: {file_path}")
    candles = load_candles(file_path)
    validate_candle_sequence(candles)

    print(f"\n[INFO] Analyzing {len(candles)} candles...")
    print(f"[INFO] Date range: {candles[0].timestamp.strftime('%Y-%m-%d')} to {candles[-1].timestamp.strftime('%Y-%m-%d')}")
    print(f"[INFO] Price range: {min(c.low for c in candles):.2f} - {max(c.high for c in candles):.2f}")
    print()

    print("[INFO] Running core signal analysis...")
    generator = SignalGenerator(candles)
    result = generator.generate_signal()

    print("[INFO] Running enhanced analysis modules...")
    enhanced = EnhancedSignalGenerator(candles)
    enhanced_data = enhanced.run_full_analysis()

    core_report = ReportGenerator.generate_report(result, candles, generator.indicators)
    enhanced_report = EnhancedReportGenerator.generate_enhanced_section(enhanced_data, candles)

    full_report = core_report + enhanced_report
    print(full_report)

    report_filename = f"sma50_full_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path = os.path.join(os.path.dirname(__file__), report_filename)
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(full_report)
        print(f"[INFO] Full report saved to: {report_path}")
    except Exception as e:
        print(f"[WARNING] Could not save report: {e}")

    print("\n[INFO] Analysis complete!")
    return result, enhanced_data


# ============================================================================
# SECTION 21: BACKTESTING ENGINE
# ============================================================================

class BacktestEngine:
    """Simple backtesting engine to validate strategy performance."""

    def __init__(self, candles: List[Candle]):
        self.candles = candles
        self.closes = [c.close for c in candles]

    def run_sma50_backtest(self, initial_capital: float = 10000.0,
                            commission_pct: float = 0.1) -> Dict[str, Any]:
        """Backtest SMA 50 crossover strategy."""
        print("[BACKTEST] Running SMA 50 backtest...")
        ti = TechnicalIndicators()
        sma50 = ti.sma(self.closes, 50)
        rsi = ti.rsi(self.closes)
        macd_line, macd_signal, macd_hist = ti.macd(self.closes)
        capital = initial_capital
        position = 0.0
        entry_price = 0.0
        trades = []
        equity_curve = [initial_capital]
        winning_trades = 0
        losing_trades = 0
        total_profit = 0.0
        total_loss = 0.0
        max_equity = initial_capital
        max_drawdown = 0.0
        for i in range(21, len(self.candles)):
            price = self.closes[i]
            prev_price = self.closes[i-1]
            sma_val = sma50[i]
            prev_sma = sma50[i-1]
            rsi_val = rsi[i]
            macd_val = macd_line[i]
            macd_sig = macd_signal[i]
            buy_signal = False
            sell_signal = False
            if prev_price <= prev_sma and price > sma_val:
                if rsi_val < 70 and macd_val > macd_sig:
                    buy_signal = True
            elif prev_price >= prev_sma and price < sma_val:
                if rsi_val > 30 and macd_val < macd_sig:
                    sell_signal = True
            if buy_signal and position == 0:
                commission = capital * (commission_pct / 100)
                investable = capital - commission
                position = investable / price
                entry_price = price
                capital = 0
                trades.append({
                    'type': 'BUY',
                    'price': price,
                    'time': self.candles[i].timestamp.strftime('%Y-%m-%d %H:%M'),
                    'capital': investable
                })
            elif sell_signal and position > 0:
                revenue = position * price
                commission = revenue * (commission_pct / 100)
                net_revenue = revenue - commission
                pnl = net_revenue - (position * entry_price)
                pnl_pct = (price - entry_price) / entry_price * 100
                capital = net_revenue
                if pnl > 0:
                    winning_trades += 1
                    total_profit += pnl
                else:
                    losing_trades += 1
                    total_loss += abs(pnl)
                trades.append({
                    'type': 'SELL',
                    'price': price,
                    'time': self.candles[i].timestamp.strftime('%Y-%m-%d %H:%M'),
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 2)
                })
                position = 0
            current_equity = capital + (position * price)
            equity_curve.append(current_equity)
            if current_equity > max_equity:
                max_equity = current_equity
            dd = (max_equity - current_equity) / max_equity * 100
            if dd > max_drawdown:
                max_drawdown = dd
        if position > 0:
            final_price = self.closes[-1]
            revenue = position * final_price
            commission = revenue * (commission_pct / 100)
            net_revenue = revenue - commission
            pnl = net_revenue - (position * entry_price)
            pnl_pct = (final_price - entry_price) / entry_price * 100
            capital = net_revenue
            if pnl > 0:
                winning_trades += 1
                total_profit += pnl
            else:
                losing_trades += 1
                total_loss += abs(pnl)
            trades.append({
                'type': 'SELL (FINAL)',
                'price': final_price,
                'time': self.candles[-1].timestamp.strftime('%Y-%m-%d %H:%M'),
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2)
            })
            position = 0
        total_trades = winning_trades + losing_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_profit = (total_profit / winning_trades) if winning_trades > 0 else 0
        avg_loss = (total_loss / losing_trades) if losing_trades > 0 else 0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
        final_capital = capital
        total_return = (final_capital - initial_capital) / initial_capital * 100
        buy_hold_return = (self.closes[-1] - self.closes[21]) / self.closes[21] * 100
        if len(equity_curve) > 1:
            returns = [(equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                      for i in range(1, len(equity_curve)) if equity_curve[i-1] > 0]
            if returns and statistics.stdev(returns) > 0:
                sharpe = (statistics.mean(returns) / statistics.stdev(returns)) * math.sqrt(252)
            else:
                sharpe = 0
        else:
            sharpe = 0
        result = {
            'initial_capital': initial_capital,
            'final_capital': round(final_capital, 2),
            'total_return_pct': round(total_return, 2),
            'buy_hold_return_pct': round(buy_hold_return, 2),
            'alpha': round(total_return - buy_hold_return, 2),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 1),
            'total_profit': round(total_profit, 2),
            'total_loss': round(total_loss, 2),
            'avg_profit_per_trade': round(avg_profit, 2),
            'avg_loss_per_trade': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown': round(max_drawdown, 2),
            'sharpe_ratio': round(sharpe, 2),
            'trades': trades[-20:],
            'commission_pct': commission_pct
        }
        print(f"[BACKTEST] Completed: {total_trades} trades, "
              f"Win Rate: {win_rate:.1f}%, Return: {total_return:.2f}%")
        return result

    def format_backtest_report(self, bt_result: Dict[str, Any]) -> str:
        """Format backtest results for display."""
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("         BACKTEST RESULTS - SMA 50 STRATEGY")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"  Initial Capital:    ${bt_result['initial_capital']:,.2f}")
        lines.append(f"  Final Capital:      ${bt_result['final_capital']:,.2f}")
        lines.append(f"  Total Return:       {bt_result['total_return_pct']:.2f}%")
        lines.append(f"  Buy & Hold Return:  {bt_result['buy_hold_return_pct']:.2f}%")
        lines.append(f"  Alpha (Excess):     {bt_result['alpha']:.2f}%")
        lines.append("")
        lines.append("-" * 70)
        lines.append("  TRADE STATISTICS")
        lines.append("-" * 70)
        lines.append(f"  Total Trades:       {bt_result['total_trades']}")
        lines.append(f"  Winning Trades:     {bt_result['winning_trades']}")
        lines.append(f"  Losing Trades:      {bt_result['losing_trades']}")
        lines.append(f"  Win Rate:           {bt_result['win_rate']:.1f}%")
        lines.append(f"  Profit Factor:      {bt_result['profit_factor']:.2f}")
        lines.append("")
        lines.append("-" * 70)
        lines.append("  RISK METRICS")
        lines.append("-" * 70)
        lines.append(f"  Total Profit:       ${bt_result['total_profit']:,.2f}")
        lines.append(f"  Total Loss:         ${bt_result['total_loss']:,.2f}")
        lines.append(f"  Avg Profit/Trade:   ${bt_result['avg_profit_per_trade']:,.2f}")
        lines.append(f"  Avg Loss/Trade:     ${bt_result['avg_loss_per_trade']:,.2f}")
        lines.append(f"  Max Drawdown:       {bt_result['max_drawdown']:.2f}%")
        lines.append(f"  Sharpe Ratio:       {bt_result['sharpe_ratio']:.2f}")
        lines.append(f"  Commission:         {bt_result['commission_pct']:.2f}%")
        lines.append("")
        if bt_result['trades']:
            lines.append("-" * 70)
            lines.append("  RECENT TRADES")
            lines.append("-" * 70)
            for t in bt_result['trades'][-10:]:
                if 'pnl' in t:
                    lines.append(f"  {t['type']:12s} @ {t['price']:10.2f} "
                                f"on {t['time']} PnL: ${t['pnl']:+,.2f} ({t['pnl_pct']:+.2f}%)")
                else:
                    lines.append(f"  {t['type']:12s} @ {t['price']:10.2f} "
                                f"on {t['time']} Capital: ${t['capital']:,.2f}")
            lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)


# ============================================================================
# SECTION 22: ALERT AND NOTIFICATION SYSTEM
# ============================================================================

class AlertSystem:
    """Generate alerts and notifications based on analysis results."""

    @staticmethod
    def check_alerts(candles: List[Candle], indicators: IndicatorValues,
                     result: SignalResult) -> List[Dict[str, Any]]:
        """Check for various alert conditions."""
        alerts = []
        current_price = candles[-1].close
        prev_price = candles[-2].close if len(candles) > 1 else current_price

        if result.signal_type in [SignalType.STRONG_BUY, SignalType.STRONG_SELL]:
            alerts.append({
                'type': 'SIGNAL',
                'priority': 'HIGH',
                'message': f"Strong {result.signal_type.value} signal detected!",
                'action': result.signal_type.value
            })

        if indicators.rsi < 25:
            alerts.append({
                'type': 'OVERSOLD',
                'priority': 'HIGH',
                'message': f"RSI extremely oversold at {indicators.rsi:.1f}",
                'action': 'POTENTIAL BUY'
            })
        elif indicators.rsi > 75:
            alerts.append({
                'type': 'OVERBOUGHT',
                'priority': 'HIGH',
                'message': f"RSI extremely overbought at {indicators.rsi:.1f}",
                'action': 'POTENTIAL SELL'
            })

        if indicators.macd_histogram > 0 and indicators.macd_histogram_prev <= 0:
            alerts.append({
                'type': 'MACD_CROSS',
                'priority': 'MEDIUM',
                'message': "MACD bullish crossover detected",
                'action': 'BUY SIGNAL'
            })
        elif indicators.macd_histogram < 0 and indicators.macd_histogram_prev >= 0:
            alerts.append({
                'type': 'MACD_CROSS',
                'priority': 'MEDIUM',
                'message': "MACD bearish crossover detected",
                'action': 'SELL SIGNAL'
            })

        prev_above_sma = candles[-2].close > indicators.sma50_prev if len(candles) > 1 else False
        curr_above_sma = current_price > indicators.sma50
        if not prev_above_sma and curr_above_sma:
            alerts.append({
                'type': 'SMA_CROSS',
                'priority': 'HIGH',
                'message': f"Price crossed above SMA50 ({indicators.sma50:.2f})",
                'action': 'BULLISH CROSSOVER'
            })
        elif prev_above_sma and not curr_above_sma:
            alerts.append({
                'type': 'SMA_CROSS',
                'priority': 'HIGH',
                'message': f"Price crossed below SMA50 ({indicators.sma50:.2f})",
                'action': 'BEARISH CROSSOVER'
            })

        if current_price <= indicators.bb_lower * 1.01:
            alerts.append({
                'type': 'BOLLINGER',
                'priority': 'MEDIUM',
                'message': f"Price near lower Bollinger Band ({indicators.bb_lower:.2f})",
                'action': 'POTENTIAL BOUNCE'
            })
        elif current_price >= indicators.bb_upper * 0.99:
            alerts.append({
                'type': 'BOLLINGER',
                'priority': 'MEDIUM',
                'message': f"Price near upper Bollinger Band ({indicators.bb_upper:.2f})",
                'action': 'POTENTIAL REVERSAL'
            })

        if indicators.adx > 30:
            direction = "UP" if indicators.plus_di > indicators.minus_di else "DOWN"
            alerts.append({
                'type': 'STRONG_TREND',
                'priority': 'MEDIUM',
                'message': f"Strong trend detected (ADX: {indicators.adx:.1f}) direction: {direction}",
                'action': f'FOLLOW {direction} TREND'
            })

        if indicators.atr_percent > 5:
            alerts.append({
                'type': 'HIGH_VOLATILITY',
                'priority': 'LOW',
                'message': f"High volatility detected (ATR: {indicators.atr_percent:.2f}%)",
                'action': 'USE WIDER STOPS'
            })

        if result.warnings:
            for w in result.warnings:
                alerts.append({
                    'type': 'RISK_WARNING',
                    'priority': 'HIGH',
                    'message': w,
                    'action': 'CAUTION'
                })

        if len(candles) >= 3:
            last3_bullish = all(c.is_bullish for c in candles[-3:])
            last3_bearish = all(c.is_bearish for c in candles[-3:])
            if last3_bullish:
                alerts.append({
                    'type': 'PATTERN',
                    'priority': 'LOW',
                    'message': "Three consecutive bullish candles",
                    'action': 'MOMENTUM BUILDING'
                })
            if last3_bearish:
                alerts.append({
                    'type': 'PATTERN',
                    'priority': 'LOW',
                    'message': "Three consecutive bearish candles",
                    'action': 'MOMENTUM BUILDING'
                })

        alerts.sort(key=lambda x: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}.get(x['priority'], 3))
        return alerts

    @staticmethod
    def format_alerts(alerts: List[Dict[str, Any]]) -> str:
        """Format alerts for display."""
        if not alerts:
            return "\n  No alerts triggered.\n"
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("         ALERTS & NOTIFICATIONS")
        lines.append("=" * 70)
        lines.append("")
        for alert in alerts:
            priority_icon = "!!!" if alert['priority'] == 'HIGH' else \
                           "!" if alert['priority'] == 'MEDIUM' else ">"
            lines.append(f"  [{priority_icon}] {alert['priority']:6s} | {alert['type']}")
            lines.append(f"       Message: {alert['message']}")
            lines.append(f"       Action:  {alert['action']}")
            lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)


# ============================================================================
# SECTION 23: UTILITY FUNCTIONS
# ============================================================================

def format_timestamp(ts_ms: int) -> str:
    """Convert millisecond timestamp to formatted string."""
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def calculate_price_change_pct(old_price: float, new_price: float) -> float:
    """Calculate percentage price change."""
    if old_price == 0:
        return 0.0
    return (new_price - old_price) / old_price * 100


def format_currency(value: float, decimals: int = 2) -> str:
    """Format a number as currency."""
    return f"${value:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a number as percentage."""
    return f"{value:.{decimals}f}%"


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def moving_average(data: List[float], period: int) -> List[float]:
    """Simple moving average helper."""
    if len(data) < period:
        return [0.0] * len(data)
    result = [0.0] * (period - 1)
    window_sum = sum(data[:period])
    result.append(window_sum / period)
    for i in range(period, len(data)):
        window_sum += data[i] - data[i - period]
        result.append(window_sum / period)
    return result


def exponential_moving_average(data: List[float], period: int) -> List[float]:
    """Exponential moving average helper."""
    if len(data) < period:
        return [0.0] * len(data)
    multiplier = 2.0 / (period + 1)
    result = [0.0] * (period - 1)
    result.append(sum(data[:period]) / period)
    for i in range(period, len(data)):
        ema_val = (data[i] - result[-1]) * multiplier + result[-1]
        result.append(ema_val)
    return result


def standard_deviation(data: List[float]) -> float:
    """Calculate standard deviation."""
    if len(data) < 2:
        return 0.0
    return statistics.stdev(data)


def linear_regression_slope(data: List[float]) -> float:
    """Calculate linear regression slope."""
    n = len(data)
    if n < 2:
        return 0.0
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(data) / n
    numerator = sum((x[i] - x_mean) * (data[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def r_squared(data: List[float]) -> float:
    """Calculate R-squared value for trend strength."""
    n = len(data)
    if n < 2:
        return 0.0
    slope = linear_regression_slope(data)
    mean_y = sum(data) / n
    ss_res = sum((data[i] - (slope * i + data[0])) ** 2 for i in range(n))
    ss_tot = sum((y - mean_y) ** 2 for y in data)
    if ss_tot == 0:
        return 0.0
    return max(0, 1 - (ss_res / ss_tot))


def calculate_correlation(x: List[float], y: List[float]) -> float:
    """Calculate Pearson correlation coefficient."""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    x = x[:n]
    y = y[:n]
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denom_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    denom_y = sum((y[i] - mean_y) ** 2 for i in range(n))
    denominator = math.sqrt(denom_x * denom_y)
    if denominator == 0:
        return 0.0
    return numerator / denominator


def detect_divergence(prices: List[float], indicator: List[float],
                      lookback: int = 14) -> str:
    """Detect bullish or bearish divergence between price and indicator."""
    if len(prices) < lookback or len(indicator) < lookback:
        return "INSUFFICIENT DATA"
    recent_prices = prices[-lookback:]
    recent_ind = indicator[-lookback:]
    price_trend = linear_regression_slope(recent_prices)
    ind_trend = linear_regression_slope(recent_ind)
    if price_trend > 0 and ind_trend < 0:
        return "BEARISH DIVERGENCE"
    elif price_trend < 0 and ind_trend > 0:
        return "BULLISH DIVERGENCE"
    elif price_trend > 0 and ind_trend > 0:
        return "NO DIVERGENCE (CONVERGENT)"
    elif price_trend < 0 and ind_trend < 0:
        return "NO DIVERGENCE (CONVERGENT)"
    else:
        return "NO DIVERGENCE (FLAT)"


def calculate_pivot_points(high: float, low: float, close: float) -> Dict[str, float]:
    """Calculate standard pivot points."""
    pivot = (high + low + close) / 3.0
    r1 = 2 * pivot - low
    r2 = pivot + (high - low)
    r3 = high + 2 * (pivot - low)
    s1 = 2 * pivot - high
    s2 = pivot - (high - low)
    s3 = low - 2 * (high - pivot)
    return {
        'pivot': round(pivot, 2),
        'r1': round(r1, 2),
        'r2': round(r2, 2),
        'r3': round(r3, 2),
        's1': round(s1, 2),
        's2': round(s2, 2),
        's3': round(s3, 2)
    }


def calculate_camarilla_pivots(high: float, low: float, close: float) -> Dict[str, float]:
    """Calculate Camarilla pivot points."""
    diff = high - low
    return {
        'r4': round(close + diff * 1.1 / 2, 2),
        'r3': round(close + diff * 1.1 / 4, 2),
        'r2': round(close + diff * 1.1 / 6, 2),
        'r1': round(close + diff * 1.1 / 12, 2),
        's1': round(close - diff * 1.1 / 12, 2),
        's2': round(close - diff * 1.1 / 6, 2),
        's3': round(close - diff * 1.1 / 4, 2),
        's4': round(close - diff * 1.1 / 2, 2)
    }


def calculate_woodie_pivots(high: float, low: float, close: float,
                             open_price: float = None) -> Dict[str, float]:
    """Calculate Woodie pivot points."""
    if open_price is None:
        open_price = close
    pivot = (high + low + 2 * open_price) / 4.0
    r1 = 2 * pivot - low
    r2 = pivot + (high - low)
    s1 = 2 * pivot - high
    s2 = pivot - (high - low)
    return {
        'pivot': round(pivot, 2),
        'r1': round(r1, 2),
        'r2': round(r2, 2),
        's1': round(s1, 2),
        's2': round(s2, 2)
    }


def calculate_fibonacci_pivot(high: float, low: float, close: float) -> Dict[str, float]:
    """Calculate Fibonacci pivot points."""
    pivot = (high + low + close) / 3.0
    r1 = pivot + 0.382 * (high - low)
    r2 = pivot + 0.618 * (high - low)
    r3 = pivot + 1.000 * (high - low)
    s1 = pivot - 0.382 * (high - low)
    s2 = pivot - 0.618 * (high - low)
    s3 = pivot - 1.000 * (high - low)
    return {
        'pivot': round(pivot, 2),
        'r1': round(r1, 2),
        'r2': round(r2, 2),
        'r3': round(r3, 2),
        's1': round(s1, 2),
        's2': round(s2, 2),
        's3': round(s3, 2)
    }


def format_pivot_report(candles: List[Candle]) -> str:
    """Generate pivot points report."""
    c = candles[-1]
    standard = calculate_pivot_points(c.high, c.low, c.close)
    camarilla = calculate_camarilla_pivots(c.high, c.low, c.close)
    woodie = calculate_woodie_pivots(c.high, c.low, c.close, c.open)
    fibonacci = calculate_fibonacci_pivot(c.high, c.low, c.close)
    lines = []
    lines.append("")
    lines.append("-" * 70)
    lines.append("  PIVOT POINTS ANALYSIS")
    lines.append("-" * 70)
    lines.append(f"  {'Type':10s} {'Pivot':>10s} {'R1':>10s} {'R2':>10s} {'R3':>10s} "
                f"{'S1':>10s} {'S2':>10s} {'S3':>10s}")
    lines.append(f"  {'Standard':10s} {standard['pivot']:>10.2f} {standard['r1']:>10.2f} "
                f"{standard['r2']:>10.2f} {standard['r3']:>10.2f} "
                f"{standard['s1']:>10.2f} {standard['s2']:>10.2f} {standard['s3']:>10.2f}")
    lines.append(f"  {'Fibonacci':10s} {fibonacci['pivot']:>10.2f} {fibonacci['r1']:>10.2f} "
                f"{fibonacci['r2']:>10.2f} {fibonacci['r3']:>10.2f} "
                f"{fibonacci['s1']:>10.2f} {fibonacci['s2']:>10.2f} {fibonacci['s3']:>10.2f}")
    lines.append(f"  {'Woodie':10s} {woodie['pivot']:>10.2f} {woodie['r1']:>10.2f} "
                f"{woodie['r2']:>10.2f} {'N/A':>10s} "
                f"{woodie['s1']:>10.2f} {woodie['s2']:>10.2f} {'N/A':>10s}")
    lines.append(f"  {'Camarilla':10s} {'N/A':>10s} {camarilla['r1']:>10.2f} "
                f"{camarilla['r2']:>10.2f} {camarilla['r3']:>10.2f} "
                f"{camarilla['s1']:>10.2f} {camarilla['s2']:>10.2f} {camarilla['s3']:>10.2f}")
    lines.append("")
    lines.append(f"  Camarilla R4: {camarilla['r4']:.2f} | Camarilla S4: {camarilla['s4']:.2f}")
    lines.append("")
    return "\n".join(lines)


# ============================================================================
# SECTION 24: DATA EXPORT AND SERIALIZATION
# ============================================================================

class DataExporter:
    """Export analysis data to various formats."""

    @staticmethod
    def to_json(result: SignalResult, enhanced_data: Dict[str, Any],
                bt_result: Optional[Dict[str, Any]] = None) -> str:
        """Export analysis results to JSON format."""
        export_data = {
            'analysis_time': datetime.now(timezone.utc).isoformat(),
            'signal': {
                'type': result.signal_type.value,
                'confidence': result.confidence,
                'spot_action': result.spot_action,
                'futures_action': result.futures_action,
                'leverage_suggestion': result.leverage_suggestion,
                'entry_price': result.entry_price,
                'stop_loss': result.stop_loss,
                'take_profit_1': result.take_profit_1,
                'take_profit_2': result.take_profit_2,
                'take_profit_3': result.take_profit_3,
                'risk_reward_ratio': result.risk_reward_ratio,
                'position_size_pct': result.position_size_pct,
                'trend_direction': result.trend_direction.value,
                'market_phase': result.market_phase.value,
                'reasons': result.reasons,
                'warnings': result.warnings,
                'support_levels': result.support_levels,
                'resistance_levels': result.resistance_levels,
                'patterns_detected': result.patterns_detected
            },
            'indicators': result.indicators_summary,
            'volume_analysis': result.volume_analysis
        }
        if enhanced_data:
            mtf = enhanced_data.get('multi_timeframe', {})
            export_data['multi_timeframe'] = {
                tf: {
                    'trend': data['trend'],
                    'signal': data['signal'],
                    'sma50': data.get('sma50', 0),
                    'rsi': data.get('rsi', 50)
                }
                for tf, data in mtf.items()
            }
            regime = enhanced_data.get('regime', {})
            export_data['market_regime'] = {
                'regime': regime.get('regime', 'N/A'),
                'strategy': regime.get('strategy', 'N/A')
            }
            vol = enhanced_data.get('volatility', {})
            export_data['volatility'] = {
                'historical_volatility': vol.get('historical_volatility', 0),
                'sharpe_ratio': vol.get('sharpe_ratio', 0),
                'max_drawdown_pct': vol.get('max_drawdown', {}).get('max_drawdown_pct', 0)
            }
            conf = enhanced_data.get('confidence', {})
            export_data['confidence'] = {
                'pct': conf.get('confidence_pct', 0),
                'rating': conf.get('rating', 'LOW'),
                'factors': conf.get('factors', {})
            }
        if bt_result:
            export_data['backtest'] = {
                'total_return_pct': bt_result.get('total_return_pct', 0),
                'win_rate': bt_result.get('win_rate', 0),
                'profit_factor': bt_result.get('profit_factor', 0),
                'max_drawdown': bt_result.get('max_drawdown', 0),
                'total_trades': bt_result.get('total_trades', 0)
            }
        return json.dumps(export_data, indent=2, default=str)

    @staticmethod
    def save_json(data: str, filepath: str):
        """Save JSON data to file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(data)
            print(f"[EXPORT] JSON saved to: {filepath}")
        except Exception as e:
            print(f"[ERROR] Failed to save JSON: {e}")

    @staticmethod
    def generate_quick_summary(result: SignalResult) -> str:
        """Generate a quick one-line summary."""
        return (f"SIGNAL: {result.signal_type.value} | "
                f"Confidence: {result.confidence:.0f}% | "
                f"Spot: {result.spot_action} | "
                f"Futures: {result.futures_action} | "
                f"Trend: {result.trend_direction.value}")


# ============================================================================
# SECTION 25: CONSOLIDATED CHART + PDF (ONE PNG, ONE PDF)
# ============================================================================

C = COLORS


def _draw_candle(ax, x, o, h, l, c, w=0.6):
    color = C["green"] if c >= o else C["red"]
    body_bot = min(o, c)
    body_h = abs(c - o)
    if body_h == 0:
        body_h = (h - l) * 0.01
    ax.bar(x, body_h, w, bottom=body_bot, color=color, edgecolor=color, linewidth=0.4, alpha=0.92, zorder=3)
    ax.plot([x, x], [l, body_bot], color=color, linewidth=0.7, zorder=3)
    ax.plot([x, x], [body_bot + body_h, h], color=color, linewidth=0.7, zorder=3)


def _text(ax, x, y, txt, fs=9, color=C["text"], ha="left", va="top", fw="normal", ff="monospace", **kw):
    ax.text(x, y, txt, fontsize=fs, color=color, ha=ha, va=va, fontweight=fw, fontfamily=ff,
            transform=ax.transAxes, clip_on=False, **kw)


def _box(ax, x, y, w, h, fc=C["bg2"], ec=C["grid"], lw=1, alpha=0.95):
    ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=lw,
                               alpha=alpha, transform=ax.transAxes, clip_on=False, zorder=1))


class BeautifulChartGenerator:
    """Two-panel chart: SMC (candles.py style) + Last 10 candles with trade plan."""

    def __init__(self, candles: List[Candle]):
        self.candles = candles
        self.closes = np.array([c.close for c in candles])
        self.opens = np.array([c.open for c in candles])
        self.highs = np.array([c.high for c in candles])
        self.lows = np.array([c.low for c in candles])
        self.volumes = np.array([c.volume for c in candles])
        self.ti = TechnicalIndicators()

    def _supertrend(self, h, l, c, length=10, multiplier=1.0):
        hl2 = (h + l) / 2.0
        tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
        tr[0] = h[0] - l[0]
        atr = pd.Series(tr).ewm(span=length, adjust=False).mean().values
        upper = hl2 + multiplier * atr
        lower = hl2 - multiplier * atr
        n = len(c)
        fu, fl = np.copy(upper), np.copy(lower)
        d = np.ones(n, dtype=int)
        for i in range(1, n):
            fu[i] = upper[i] if upper[i] < fu[i-1] or c[i-1] > fu[i-1] else fu[i-1]
            fl[i] = lower[i] if lower[i] > fl[i-1] or c[i-1] < fl[i-1] else fl[i-1]
            if d[i-1] == 1 and c[i] < fl[i]:
                d[i] = -1
            elif d[i-1] == -1 and c[i] > fu[i]:
                d[i] = 1
            else:
                d[i] = d[i-1]
        return pd.Series(np.where(d == 1, fl, fu)), pd.Series(d)

    def _pivots(self, h, l, left=5, right=5):
        n = len(h)
        ph, pl = np.full(n, np.nan), np.full(n, np.nan)
        for i in range(left, n - right):
            if h[i] == max(h[i-left:i+right+1]):
                ph[i] = h[i]
            if l[i] == min(l[i-left:i+right+1]):
                pl[i] = l[i]
        return pd.Series(ph), pd.Series(pl)

    def _smart_money(self, swing_length=5):
        o, h, l, c = self.opens, self.highs, self.lows, self.closes
        n = len(c)
        ph, pl = self._pivots(pd.Series(h), pd.Series(l), swing_length, swing_length)
        phv, plv = ph.values, pl.values
        bos_bull = np.zeros(n, dtype=bool)
        bos_bear = np.zeros(n, dtype=bool)
        choch_bull = np.zeros(n, dtype=bool)
        choch_bear = np.zeros(n, dtype=bool)
        bob, bol = np.full(n, np.nan), np.full(n, np.nan)
        beb, bel = np.full(n, np.nan), np.full(n, np.nan)
        fbt, fbb = np.full(n, np.nan), np.full(n, np.nan)
        fvet, fveb = np.full(n, np.nan), np.full(n, np.nan)
        csh, csl = np.nan, np.nan
        ct = 0
        for i in range(1, n):
            if not np.isnan(phv[i]):
                csh = phv[i]
            if not np.isnan(plv[i]):
                csl = plv[i]
            if not np.isnan(csh) and c[i] > csh and c[i-1] <= csh:
                (choch_bull if ct == -1 else bos_bull)[i] = True
                ct = 1
            if not np.isnan(csl) and c[i] < csl and c[i-1] >= csl:
                (choch_bear if ct == 1 else bos_bear)[i] = True
                ct = -1
        for i in range(1, n):
            if bos_bull[i] or choch_bull[i]:
                for j in range(i-1, max(i-6, -1), -1):
                    if c[j] < o[j]:
                        bob[i], bol[i] = h[j], l[j]
                        break
            if bos_bear[i] or choch_bear[i]:
                for j in range(i-1, max(i-6, -1), -1):
                    if c[j] > o[j]:
                        beb[i], bel[i] = h[j], l[j]
                        break
        for i in range(2, n):
            if l[i] > h[i-2]:
                fbt[i], fbb[i] = l[i], h[i-2]
            if h[i] < l[i-2]:
                fvet[i], fveb[i] = l[i-2], h[i]
        return {"bos_bull": bos_bull, "bos_bear": bos_bear, "choch_bull": choch_bull,
                "choch_bear": choch_bear, "bob": bob, "bol": bol, "beb": beb,
                "bel": bel, "fbt": fbt, "fbb": fbb, "fvet": fvet, "fveb": fveb}

    def _render_smc_to_buffer(self):
        BG, BG2, GRD = C["bg"], C["bg2"], C["grid"]
        TXT, GRN, RED = C["text"], C["green"], C["red"]
        BLU, PRP, ORG = C["blue"], C["purple"], C["orange"]
        TEA, CYN = C["teal"], C["cyan"]

        df = pd.DataFrame({"Open": self.opens, "High": self.highs, "Low": self.lows,
                           "Close": self.closes, "Volume": self.volumes})
        dates = pd.date_range(end=self.candles[-1].timestamp, periods=len(self.candles), freq="1h")
        df.index = dates[:len(df)]

        st1, d1 = self._supertrend(self.highs, self.lows, self.closes, 10, 1.0)
        st2, d2 = self._supertrend(self.highs, self.lows, self.closes, 10, 2.0)
        st3, d3 = self._supertrend(self.highs, self.lows, self.closes, 10, 3.0)
        delta = pd.Series(self.closes).diff()
        gain = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
        rv = 100 - (100 / (1 + gain / loss))
        ph, pl = self._pivots(pd.Series(self.highs), pd.Series(self.lows), 5, 5)
        sm = self._smart_money(5)

        def split(v, d):
            um, dm = (d == 1).copy(), (d == -1).copy()
            for i in range(1, len(v)):
                if d.iloc[i] != d.iloc[i-1]:
                    (um if d.iloc[i] == 1 else dm).iloc[i-1] = True
            u, dd = v.copy().astype(float), v.copy().astype(float)
            u[~um] = np.nan
            dd[~dm] = np.nan
            return u, dd

        s1u, s1d = split(st1, d1)
        s2u, s2d = split(st2, d2)
        s3u, s3d = split(st3, d3)
        rsi_70 = pd.Series([70] * len(df), index=df.index)
        rsi_30 = pd.Series([30] * len(df), index=df.index)

        ap = [
            mpf.make_addplot(s1u, color=GRN, width=2.5),
            mpf.make_addplot(s1d, color=RED, width=2.5),
            mpf.make_addplot(s2u, color=GRN, width=1.5, linestyle="--"),
            mpf.make_addplot(s2d, color=RED, width=1.5, linestyle="--"),
            mpf.make_addplot(s3u, color=GRN, width=1, linestyle=":"),
            mpf.make_addplot(s3d, color=RED, width=1, linestyle=":"),
            mpf.make_addplot(ph, type="scatter", marker="v", markersize=50, color=RED),
            mpf.make_addplot(pl, type="scatter", marker="^", markersize=50, color=GRN),
            mpf.make_addplot(rv, color=PRP, width=1.8, panel=2, ylabel="RSI"),
            mpf.make_addplot(rsi_70, color="#555555", width=0.8, linestyle="--", panel=2),
            mpf.make_addplot(rsi_30, color="#555555", width=0.8, linestyle="--", panel=2),
        ]

        mc = mpf.make_marketcolors(up=GRN, down=RED, edge={"up": GRN, "down": RED},
                                    wick={"up": GRN, "down": RED}, volume={"up": GRN, "down": RED})
        style = mpf.make_mpf_style(base_mpf_style="nightclouds", marketcolors=mc, facecolor=BG,
                                    figcolor=BG, gridstyle="-", gridcolor=GRD, y_on_right=True,
                                    rc={"axes.labelcolor": TXT, "axes.edgecolor": GRD,
                                        "xtick.color": TXT, "ytick.color": TXT,
                                        "figure.facecolor": BG, "savefig.facecolor": BG})

        fig, axes = mpf.plot(df, type="candle", style=style, volume=True, addplot=ap,
                              figsize=(26, 18), panel_ratios=(5, 1.2, 1.5),
                              tight_layout=True, xrotation=0, returnfig=True)
        for a in axes:
            a.set_facecolor(BG)
        ax = axes[0]

        for i in range(len(df)):
            if sm["bos_bull"][i]:
                ax.text(i, self.lows[i] * 0.996, "BOS", fontsize=7, color="white", ha="center", va="top",
                        fontweight="bold", bbox=dict(boxstyle="round,pad=0.15", facecolor=BLU, edgecolor="none", alpha=0.95))
            if sm["bos_bear"][i]:
                ax.text(i, self.highs[i] * 1.004, "BOS", fontsize=7, color="white", ha="center", va="bottom",
                        fontweight="bold", bbox=dict(boxstyle="round,pad=0.15", facecolor=RED, edgecolor="none", alpha=0.95))
            if sm["choch_bull"][i]:
                ax.text(i, self.lows[i] * 0.996, "CHoCH", fontsize=7, color="white", ha="center", va="top",
                        fontweight="bold", bbox=dict(boxstyle="round,pad=0.15", facecolor=TEA, edgecolor="none", alpha=0.95))
            if sm["choch_bear"][i]:
                ax.text(i, self.highs[i] * 1.004, "CHoCH", fontsize=7, color="white", ha="center", va="bottom",
                        fontweight="bold", bbox=dict(boxstyle="round,pad=0.15", facecolor=ORG, edgecolor="none", alpha=0.95))

        hv, lv = self.highs, self.lows
        for i in range(len(df)):
            if not np.isnan(sm["bob"][i]):
                t, b = sm["bob"][i], sm["bol"][i]
                e = next((j for j in range(i+1, len(df)) if lv[j] < b), len(df))
                ax.add_patch(plt.Rectangle((i-0.5, b), e-i, t-b, facecolor=BLU, alpha=0.1, edgecolor=BLU, linewidth=0.5))
            if not np.isnan(sm["beb"][i]):
                t, b = sm["beb"][i], sm["bel"][i]
                e = next((j for j in range(i+1, len(df)) if hv[j] > t), len(df))
                ax.add_patch(plt.Rectangle((i-0.5, b), e-i, t-b, facecolor=RED, alpha=0.1, edgecolor=RED, linewidth=0.5))
        for i in range(len(df)):
            if not np.isnan(sm["fbt"][i]):
                t, b = sm["fbt"][i], sm["fbb"][i]
                e = next((j for j in range(i+1, len(df)) if lv[j] <= b), len(df))
                ax.add_patch(plt.Rectangle((i-0.5, b), e-i, t-b, facecolor=CYN, alpha=0.1, edgecolor=CYN, linewidth=0.5))
            if not np.isnan(sm["fvet"][i]):
                t, b = sm["fvet"][i], sm["fveb"][i]
                e = next((j for j in range(i+1, len(df)) if hv[j] >= t), len(df))
                ax.add_patch(plt.Rectangle((i-0.5, b), e-i, t-b, facecolor=RED, alpha=0.1, edgecolor=RED, linewidth=0.5))

        fig.text(0.5, 0.97, "SMART MONEY CONCEPTS  \u00b7  TRIPLE SUPERTREND  \u00b7  RSI",
                 fontsize=14, fontweight="bold", color=TXT, ha="center")
        rsi_now = rv.iloc[-1]
        rsi_clr = RED if rsi_now > 70 else GRN if rsi_now < 30 else ORG
        rsi_lbl = "OVERBOUGHT" if rsi_now > 70 else "OVERSOLD" if rsi_now < 30 else "NEUTRAL"
        axes[2].text(0.01, 0.92, f"  RSI(14): {rsi_now:.1f}  {rsi_lbl}", transform=axes[2].transAxes,
                     fontsize=10, fontfamily="monospace", va="top", color=rsi_clr, fontweight="bold")
        axes[2].set_ylabel("RSI", color=TXT, fontsize=10)

        buf = io.BytesIO()
        fig.savefig(buf, dpi=150, bbox_inches="tight", facecolor=BG, pad_inches=0.3)
        plt.close(fig)
        buf.seek(0)
        return buf

    def _draw_trade_chart(self, ax, result: SignalResult, indicators: IndicatorValues):
        n = 10
        opens = self.opens[-n:]
        highs = self.highs[-n:]
        lows = self.lows[-n:]
        closes = self.closes[-n:]
        idx = list(range(n))

        ax.set_facecolor(C["bg2"])
        for s in ax.spines.values():
            s.set_color(C["grid"])

        for i in range(n):
            color = C["green"] if closes[i] >= opens[i] else C["red"]
            body_bot = min(opens[i], closes[i])
            body_h = abs(closes[i] - opens[i])
            if body_h == 0:
                body_h = (highs[i] - lows[i]) * 0.01
            ax.bar(idx[i], body_h, 0.6, bottom=body_bot, color=color, edgecolor=color, linewidth=0.5, alpha=0.92, zorder=3)
            ax.plot([idx[i], idx[i]], [lows[i], body_bot], color=color, linewidth=0.8, zorder=3)
            ax.plot([idx[i], idx[i]], [body_bot + body_h, highs[i]], color=color, linewidth=0.8, zorder=3)

        for i in range(n):
            ci = len(self.candles) - n + i
            ax.text(idx[i], lows[i] * 0.998, self.candles[ci].timestamp.strftime('%m/%d %H:%M'),
                    fontsize=6, color=C["text_dim"], ha='center', va='top', rotation=45)

        current = closes[-1]

        if result.stop_loss > 0:
            ax.axhline(y=result.stop_loss, color=C["red"], linewidth=2, linestyle="--", alpha=0.9, zorder=5)
            ax.text(n - 0.3, result.stop_loss, f" SL {result.stop_loss:.2f} ", fontsize=9, color="white",
                    ha="right", va="center", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc=C["red"], ec="none", alpha=0.95))

        if result.entry_price > 0:
            ax.axhline(y=result.entry_price, color=C["blue"], linewidth=2.5, linestyle="-", alpha=0.95, zorder=5)
            ax.text(n - 0.3, result.entry_price, f" ENTRY {result.entry_price:.2f} ", fontsize=9, color="white",
                    ha="right", va="center", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc=C["blue"], ec="none", alpha=0.95))

        if result.take_profit_1 > 0:
            ax.axhline(y=result.take_profit_1, color=C["green"], linewidth=2, linestyle="-", alpha=0.9, zorder=5)
            ax.text(n - 0.3, result.take_profit_1, f" TP1 {result.take_profit_1:.2f} ", fontsize=9, color="white",
                    ha="right", va="center", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc="#1a4d1a", ec=C["green"], alpha=0.95))

        if result.take_profit_2 > 0:
            ax.axhline(y=result.take_profit_2, color=C["green"], linewidth=1.5, linestyle="--", alpha=0.7, zorder=5)
            ax.text(n - 0.3, result.take_profit_2, f" TP2 {result.take_profit_2:.2f} ", fontsize=8, color=C["green"],
                    ha="right", va="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc=C["bg2"], ec=C["green"], alpha=0.9))

        if result.take_profit_3 > 0:
            ax.axhline(y=result.take_profit_3, color=C["green"], linewidth=1, linestyle=":", alpha=0.6, zorder=5)
            ax.text(n - 0.3, result.take_profit_3, f" TP3 {result.take_profit_3:.2f} ", fontsize=7, color=C["green"],
                    ha="right", va="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc=C["bg2"], ec=C["green"], alpha=0.8))

        if result.support_levels:
            for i, s in enumerate(result.support_levels[:2]):
                if s > 0:
                    ax.axhline(y=s, color=C["green"], linewidth=0.8, linestyle="--", alpha=0.4, zorder=2)
                    ax.text(0, s, f" S{i+1}", fontsize=7, color=C["green"], va="center", alpha=0.6)

        if result.resistance_levels:
            for i, r in enumerate(result.resistance_levels[:2]):
                if r > 0:
                    ax.axhline(y=r, color=C["red"], linewidth=0.8, linestyle="--", alpha=0.4, zorder=2)
                    ax.text(0, r, f" R{i+1}", fontsize=7, color=C["red"], va="center", alpha=0.6)

        sig_color = C["green"] if "BUY" in result.signal_type.value else C["red"] if "SELL" in result.signal_type.value else C["orange"]
        ax.text(n / 2, current * 1.015, f" {result.signal_type.value} ", fontsize=14, fontweight="bold",
                color="white", ha="center", va="bottom",
                bbox=dict(boxstyle="round,pad=0.4", fc=sig_color, ec="none", alpha=0.95), zorder=10)

        sl_pct = abs(result.entry_price - result.stop_loss) / result.entry_price * 100 if result.entry_price > 0 else 0
        tp1_pct = abs(result.take_profit_1 - result.entry_price) / result.entry_price * 100 if result.entry_price > 0 else 0
        detail_lines = [
            f"{'━' * 34}",
            f"  TRADE PLAN  \u00b7  {result.signal_type.value}",
            f"{'━' * 34}",
            f"  Entry:      {result.entry_price:.2f}",
            f"  SL:         {result.stop_loss:.2f}  ({sl_pct:.2f}%)",
            f"  TP1:        {result.take_profit_1:.2f}  ({tp1_pct:.2f}%)",
            f"  TP2:        {result.take_profit_2:.2f}",
            f"  TP3:        {result.take_profit_3:.2f}",
            f"  R:R:        {result.risk_reward_ratio:.2f}",
            f"  Leverage:   {result.leverage_suggestion}",
            f"  Position:   {result.position_size_pct:.2f}%",
            f"{'━' * 34}",
            f"  Confidence: {result.confidence:.0f}%",
            f"  Trend:      {result.trend_direction.value}",
            f"  Phase:      {result.market_phase.value}",
            f"  Spot:       {result.spot_action}",
            f"  Futures:    {result.futures_action}",
        ]
        txt = "\n".join(detail_lines)
        ax.text(0.02, 0.98, txt, transform=ax.transAxes, fontsize=8, fontfamily="monospace",
                va="top", ha="left", color=C["text"], linespacing=1.4,
                bbox=dict(boxstyle="round,pad=0.6", fc=C["bg"], ec=C["grid"], alpha=0.95))

        ax.set_title("LAST 10 CANDLES  \u00b7  TRADE PLAN", fontsize=12, fontweight="bold",
                      color=C["text"], pad=10)
        ax.set_ylabel("Price", color=C["text"], fontsize=10)
        ax.tick_params(colors=C["text"], labelsize=8)
        ax.grid(True, color=C["grid"], alpha=0.2, linewidth=0.3)
        ax.set_xlim(-0.5, n - 0.3)

    def _draw_data_section(self, fig, result, indicators, enhanced_data, bt_result):
        """Draw ALL analysis data below the charts."""
        BG, BG2, GRD = C["bg"], C["bg2"], C["grid"]
        TXT, TD, GRN = C["text"], C["text_dim"], C["green"]
        RED, BLU, ORG = C["red"], C["blue"], C["orange"]
        PRP, TEA, CYN = C["purple"], C["teal"], C["cyan"]
        YEL, PNK, WHT = C["yellow"], C["pink"], C["white"]
        current = self.closes[-1]
        sig_color = GRN if "BUY" in result.signal_type.value else RED if "SELL" in result.signal_type.value else ORG

        def _box(ax, x, y, w, h, fc=BG2, ec=GRD, lw=1, alpha=0.95):
            ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=lw,
                                       alpha=alpha, transform=ax.transAxes, clip_on=False, zorder=1))

        def _txt(ax, x, y, t, fs=9, color=TXT, ha="left", va="top", fw="normal", ff="monospace"):
            ax.text(x, y, t, fontsize=fs, color=color, ha=ha, va=va, fontweight=fw, fontfamily=ff,
                    transform=ax.transAxes, clip_on=False)

        # --- Row 1: Indicators | S/R | Signal Reasons ---
        ax_r1 = fig.add_axes([0.02, 0.38, 0.96, 0.13])
        ax_r1.set_xlim(0, 1); ax_r1.set_ylim(0, 1); ax_r1.axis("off"); ax_r1.set_facecolor(BG)

        # Indicators (left 33%)
        _box(ax_r1, 0.0, 0.0, 0.32, 1.0)
        _txt(ax_r1, 0.02, 0.96, "TECHNICAL INDICATORS", fs=10, color=CYN, fw="bold")
        inds = [
            f"SMA50:   {indicators.sma50:.2f}",
            f"SMA50 Slope: {indicators.sma50 - indicators.sma50_prev:+.2f}",
            f"RSI(14): {indicators.rsi:.1f}",
            f"MACD:    {indicators.macd_line:.4f}",
            f"MACD Sig:{indicators.macd_signal:.4f}",
            f"BB Upper: {indicators.bb_upper:.2f}",
            f"BB Lower: {indicators.bb_lower:.2f}",
            f"BB Width: {indicators.bb_width:.2f}%",
            f"ATR(14): {indicators.atr:.2f} ({indicators.atr_percent:.2f}%)",
            f"ADX:     {indicators.adx:.1f}",
            f"CCI(20): {indicators.cci:.1f}",
            f"MFI(14): {indicators.mfi:.1f}",
            f"VWAP:    {indicators.vwap:.2f}",
            f"Stoch K: {indicators.stoch_k:.1f}",
            f"Stoch D: {indicators.stoch_d:.1f}",
            f"Momentum:{indicators.momentum:.2f}",
            f"ROC:     {indicators.roc:.2f}%",
        ]
        for j, line in enumerate(inds):
            _txt(ax_r1, 0.02, 0.88 - j * 0.055, line, fs=7, color=TXT)

        # S/R (middle 33%)
        _box(ax_r1, 0.34, 0.0, 0.32, 1.0)
        _txt(ax_r1, 0.36, 0.96, "SUPPORT / RESISTANCE", fs=10, color=TEA, fw="bold")
        _txt(ax_r1, 0.36, 0.90, f"Current: {current:.2f}", fs=8, color=BLU, fw="bold")
        y = 0.84
        if result.resistance_levels:
            for i, r in enumerate(result.resistance_levels[:5]):
                d = (r - current) / current * 100
                _txt(ax_r1, 0.36, y, f"R{i+1}: {r:.2f}  (+{d:.2f}%)", fs=7, color=RED)
                y -= 0.05
        y -= 0.02
        if result.support_levels:
            for i, s in enumerate(result.support_levels[:5]):
                d = (current - s) / current * 100
                _txt(ax_r1, 0.36, y, f"S{i+1}: {s:.2f}  (-{d:.2f}%)", fs=7, color=GRN)
                y -= 0.05

        # Signal Reasons (right 33%)
        _box(ax_r1, 0.68, 0.0, 0.32, 1.0)
        _txt(ax_r1, 0.70, 0.96, "SIGNAL REASONS", fs=10, color=PNK, fw="bold")
        for j, r in enumerate(result.reasons[:12]):
            is_bull = any(w in r.upper() for w in ["BULL", "BUY", "ABOVE", "POSITIVE", "UP", "MARKUP", "ACCUM"])
            is_bear = any(w in r.upper() for w in ["BEAR", "SELL", "BELOW", "NEGATIVE", "DOWN", "DISTRIBUTION"])
            clr = GRN if is_bull else RED if is_bear else ORG
            marker = "+" if is_bull else "-" if is_bear else "~"
            _txt(ax_r1, 0.70, 0.88 - j * 0.07, f"{marker} {r[:48]}", fs=6.5, color=clr)

        # --- Row 2: Confidence | Multi-TF | Fibonacci ---
        ax_r2 = fig.add_axes([0.02, 0.22, 0.96, 0.14])
        ax_r2.set_xlim(0, 1); ax_r2.set_ylim(0, 1); ax_r2.axis("off"); ax_r2.set_facecolor(BG)

        # Confidence Score
        _box(ax_r2, 0.0, 0.0, 0.32, 1.0)
        _txt(ax_r2, 0.02, 0.96, "CONFIDENCE SCORE", fs=10, color=CYN, fw="bold")
        if enhanced_data and 'confidence' in enhanced_data:
            conf = enhanced_data['confidence']
            _txt(ax_r2, 0.02, 0.88, f"Score: {conf.get('total_score', 0)}/{conf.get('max_possible', 100)}  "
                  f"({conf.get('confidence_pct', 0):.0f}%)  {conf.get('rating', 'N/A')}", fs=8, color=WHT)
            factors = conf.get('factors', {})
            bar_y = 0.80
            for fname, fval in list(factors.items())[:8]:
                bw = fval / 10 * 0.28
                fclr = CYN if fval >= 5 else ORG if fval >= 3 else RED
                ax_r2.add_patch(plt.Rectangle((0.02, bar_y - 0.008), bw, 0.014,
                                 facecolor=fclr, alpha=0.6, transform=ax_r2.transAxes, clip_on=False))
                _txt(ax_r2, 0.02 + bw + 0.01, bar_y - 0.005, f"{fval}", fs=6, color=fclr)
                _txt(ax_r2, 0.02, bar_y - 0.005, fname[:14], fs=6, color=TD)
                bar_y -= 0.08

        # Multi-Timeframe
        _box(ax_r2, 0.34, 0.0, 0.32, 1.0)
        _txt(ax_r2, 0.36, 0.96, "MULTI-TIMEFRAME", fs=10, color=CYN, fw="bold")
        if enhanced_data and 'multi_timeframe' in enhanced_data:
            tf_data = enhanced_data['multi_timeframe']
            y = 0.88
            for tf, d in tf_data.items():
                trend = d['trend']
                tclr = GRN if trend == 'BULLISH' else RED if trend == 'BEARISH' else ORG
                arrow = ">>>" if trend == 'BULLISH' else "<<<" if trend == 'BEARISH' else "==="
                _txt(ax_r2, 0.36, y, f"{tf:4s}: {trend:10s} {arrow}", fs=8, color=tclr)
                y -= 0.12

        # Fibonacci
        _box(ax_r2, 0.68, 0.0, 0.32, 1.0)
        _txt(ax_r2, 0.70, 0.96, "FIBONACCI LEVELS", fs=10, color=PRP, fw="bold")
        if enhanced_data and 'fibonacci' in enhanced_data:
            fib = enhanced_data['fibonacci']
            _txt(ax_r2, 0.70, 0.88, f"Position: {fib.get('position', {}).get('price_position', 'N/A')}", fs=8, color=WHT)
            y = 0.80
            for name, level in list(fib.get('levels', {}).items())[:6]:
                _txt(ax_r2, 0.70, y, f"{name}: {level:.2f}", fs=7, color=PRP)
                y -= 0.10

        # --- Row 3: Volatility | Regime | Backtest ---
        ax_r3 = fig.add_axes([0.02, 0.06, 0.96, 0.14])
        ax_r3.set_xlim(0, 1); ax_r3.set_ylim(0, 1); ax_r3.axis("off"); ax_r3.set_facecolor(BG)

        # Volatility
        _box(ax_r3, 0.0, 0.0, 0.32, 1.0)
        _txt(ax_r3, 0.02, 0.96, "VOLATILITY & RISK", fs=10, color=ORG, fw="bold")
        if enhanced_data and 'volatility' in enhanced_data:
            vol = enhanced_data['volatility']
            vlines = [
                f"HV:       {vol.get('historical_volatility', 0):.2f}%",
                f"Sharpe:   {vol.get('sharpe_ratio', 0):.2f}",
                f"Sortino:  {vol.get('sortino_ratio', 0):.2f}",
                f"MaxDD:    {vol.get('max_drawdown', {}).get('max_drawdown_pct', 0):.2f}%",
                f"VaR(95):  {vol.get('var_95', 0):.2f}%",
            ]
            for j, line in enumerate(vlines):
                _txt(ax_r3, 0.02, 0.88 - j * 0.14, line, fs=7, color=TXT)

        # Market Regime
        _box(ax_r3, 0.34, 0.0, 0.32, 1.0)
        _txt(ax_r3, 0.36, 0.96, "MARKET REGIME", fs=10, color=TEA, fw="bold")
        if enhanced_data and 'regime' in enhanced_data:
            r = enhanced_data['regime']
            rlines = [
                f"Regime:   {r.get('regime', 'N/A')}",
                f"Strategy: {r.get('strategy', 'N/A')}",
                f"Trend:    {r.get('trend_regime', 'N/A')}",
                f"Vol Reg:  {r.get('volatility_regime', 'N/A')}",
                f"BB Squeeze: {r.get('bb_squeeze', 'NO')}",
            ]
            for j, line in enumerate(rlines):
                _txt(ax_r3, 0.36, 0.88 - j * 0.14, line, fs=7, color=TXT)

        # Backtest
        _box(ax_r3, 0.68, 0.0, 0.32, 1.0)
        _txt(ax_r3, 0.70, 0.96, "BACKTEST RESULTS", fs=10, color=YEL, fw="bold")
        if bt_result and bt_result.get('total_trades', 0) > 0:
            blines = [
                f"Capital:  ${bt_result.get('initial_capital', 0):,.0f} -> ${bt_result.get('final_capital', 0):,.0f}",
                f"Return:   {bt_result.get('total_return_pct', 0):.2f}%",
                f"B&H:      {bt_result.get('buy_hold_return_pct', 0):.2f}%",
                f"Trades:   {bt_result.get('total_trades', 0)} (W:{bt_result.get('winning_trades', 0)}/L:{bt_result.get('losing_trades', 0)})",
                f"Win Rate: {bt_result.get('win_rate', 0):.1f}%",
                f"PF:       {bt_result.get('profit_factor', 0):.2f}",
                f"Sharpe:   {bt_result.get('sharpe_ratio', 0):.2f}",
                f"MaxDD:    {bt_result.get('max_drawdown', 0):.2f}%",
            ]
        else:
            blines = ["No trades generated in backtest", f"B&H Return: {bt_result.get('buy_hold_return_pct', 0):.2f}%" if bt_result else "N/A"]
        for j, line in enumerate(blines):
            _txt(ax_r3, 0.70, 0.88 - j * 0.10, line, fs=7, color=TXT)

        # --- Row 4: Risk Management + Disclaimer ---
        ax_r4 = fig.add_axes([0.02, 0.005, 0.96, 0.05])
        ax_r4.set_xlim(0, 1); ax_r4.set_ylim(0, 1); ax_r4.axis("off"); ax_r4.set_facecolor(BG)
        risk_text = ("RISK: Never risk >2% per trade | Always set SL | Take partial profits (30/40/30) | "
                     "Move SL to breakeven after TP1 | Check news before entry | "
                     "DISCLAIMER: Educational purposes only. Not financial advice. Trading involves risk of loss.")
        _txt(ax_r4, 0.5, 0.5, risk_text, fs=6, color=TD, ha="center", va="center")

    def generate(self, indicators: IndicatorValues, result: SignalResult,
                 enhanced_data: Dict[str, Any], output_path: str) -> str:
        if not HAS_MATPLOTLIB:
            return ""
        print(f"[CHART] Generating ALL-IN-ONE PNG (charts + all analysis)...")

        smc_buf = self._render_smc_to_buffer()
        smc_img = plt.imread(smc_buf)

        fig = plt.figure(figsize=(32, 40), facecolor=C["bg"])

        # Title banner
        ax_title = fig.add_axes([0.0, 0.965, 1.0, 0.035])
        ax_title.set_xlim(0, 1); ax_title.set_ylim(0, 1); ax_title.axis("off"); ax_title.set_facecolor(C["bg"])
        sig_color = C["green"] if "BUY" in result.signal_type.value else C["red"] if "SELL" in result.signal_type.value else C["orange"]
        ax_title.add_patch(plt.Rectangle((0.05, 0.05), 0.9, 0.9, fc=C["bg2"], ec=sig_color, lw=3,
                                         transform=ax_title.transAxes, clip_on=False))
        ax_title.text(0.5, 0.65, f"SMA 50 TRADING BOT  |  {result.signal_type.value}  |  "
                      f"Confidence: {result.confidence:.0f}%  |  "
                      f"{self.candles[-1].timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
                      fontsize=18, fontweight="bold", color=sig_color, ha="center", va="center",
                      transform=ax_title.transAxes)

        # Row 0: Charts (SMC left, Trade Plan right)
        ax_smc = fig.add_axes([0.01, 0.66, 0.54, 0.30])
        ax_smc.imshow(smc_img, aspect="auto"); ax_smc.axis("off")

        ax_trade = fig.add_axes([0.56, 0.66, 0.43, 0.30])
        self._draw_trade_chart(ax_trade, result, indicators)

        # Separator line
        ax_sep = fig.add_axes([0.01, 0.655, 0.98, 0.003])
        ax_sep.set_xlim(0, 1); ax_sep.set_ylim(0, 1); ax_sep.axis("off")
        ax_sep.axhline(y=0.5, color=C["grid"], linewidth=2)

        # Data sections
        self._draw_data_section(fig, result, indicators, enhanced_data,
                                getattr(self, '_bt_result', None))

        plt.savefig(output_path, dpi=120, bbox_inches="tight", facecolor=C["bg"], pad_inches=0.15,
                    pil_kwargs={"antialias": "best"})
        plt.close(fig)
        print(f"[CHART] Saved: {output_path}")
        return output_path


class BeautifulPDFGenerator:
    """One clean PDF with all analysis."""

    def __init__(self, candles: List[Candle]):
        self.candles = candles

    def generate(self, result: SignalResult, enhanced_data: Dict[str, Any],
                 bt_result: Dict[str, Any], chart_path: str, output_path: str) -> str:
        if not HAS_MATPLOTLIB:
            return ""
        print(f"[PDF] Generating PDF: {output_path}")
        pdf = PdfPages(output_path)
        self._page_cover(pdf, result)
        self._page_chart(pdf, chart_path)
        self._page_signal(pdf, result)
        self._page_indicators(pdf, result)
        self._page_sr(pdf, result)
        self._page_enhanced(pdf, enhanced_data)
        self._page_backtest(pdf, bt_result)
        self._page_risk(pdf)
        pdf.close()
        print(f"[PDF] Saved: {output_path}")
        return output_path

    def _new_fig(self):
        fig = plt.figure(figsize=(11.69, 8.27), facecolor=C["bg"])
        return fig

    def _page_cover(self, pdf, result):
        fig = self._new_fig()
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_facecolor(C["bg"]); ax.axis("off")
        for i in range(200):
            ax.plot(np.random.random(), np.random.random(), '.', color=C["grid"], alpha=0.15, markersize=1)
        ax.add_patch(plt.Rectangle((0.15, 0.62), 0.7, 0.25, fc=C["bg2"], ec=C["grid"], lw=2,
                     transform=ax.transAxes, clip_on=False, zorder=1))
        _box(ax, 0.15, 0.62, 0.7, 0.25, fc=C["bg2"], ec=C["grid"], lw=2)
        sig_color = C["green"] if "BUY" in result.signal_type.value else C["red"] if "SELL" in result.signal_type.value else C["orange"]
        _text(ax, 0.5, 0.84, "SMA 50", fs=42, color=C["white"], ha="center", fw="bold")
        _text(ax, 0.5, 0.78, "TRADING BOT", fs=20, color=C["text_dim"], ha="center")
        _box(ax, 0.3, 0.63, 0.4, 0.12, fc=sig_color, ec=sig_color, lw=3)
        _text(ax, 0.5, 0.72, result.signal_type.value, fs=28, color="white", ha="center", fw="bold")
        _text(ax, 0.5, 0.66, f"Confidence: {result.confidence:.0f}%", fs=14, color="white", ha="center")
        info = [
            f"Date:       {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
            f"Last Candle: {self.candles[-1].timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
            f"Candles:    {len(self.candles)} analyzed",
            f"Price:      {self.candles[-1].close:.2f}",
            f"Trend:      {result.trend_direction.value}",
            f"Phase:      {result.market_phase.value}",
            f"Spot:       {result.spot_action}  |  Futures: {result.futures_action}",
        ]
        for j, line in enumerate(info):
            _text(ax, 0.5, 0.52 - j * 0.035, line, fs=10, color=C["text"], ha="center", ff="monospace")
        _text(ax, 0.5, 0.04, "SMA 50 Trading Bot v2.0  ·  Generated by Toobit Engine",
              fs=8, color=C["text_dim"], ha="center")
        pdf.savefig(fig, facecolor=C["bg"])
        plt.close(fig)

    def _page_chart(self, pdf, chart_path):
        if not chart_path or not os.path.exists(chart_path):
            return
        fig = self._new_fig()
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_facecolor(C["bg"]); ax.axis("off")
        try:
            img = plt.imread(chart_path)
            ax.imshow(img, aspect="auto", extent=[0.01, 0.99, 0.01, 0.99])
        except Exception as e:
            _text(ax, 0.5, 0.5, f"Chart: {e}", fs=12, color=C["red"], ha="center")
        pdf.savefig(fig, facecolor=C["bg"])
        plt.close(fig)

    def _page_signal(self, pdf, result):
        fig = self._new_fig()
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_facecolor(C["bg"]); ax.axis("off")
        sig_color = C["green"] if "BUY" in result.signal_type.value else C["red"] if "SELL" in result.signal_type.value else C["orange"]
        _text(ax, 0.5, 0.95, "SIGNAL & TRADE PLAN", fs=20, color=C["white"], ha="center", fw="bold")

        sections = [
            ("ACTION", sig_color, [
                f"Signal:      {result.signal_type.value}",
                f"Confidence:  {result.confidence:.0f}%",
                f"Spot:        {result.spot_action}",
                f"Futures:     {result.futures_action}",
                f"Leverage:    {result.leverage_suggestion}",
                f"Size:        {result.position_size_pct:.2f}% portfolio",
            ]),
            ("TRADE PLAN", C["yellow"], [
                f"Entry:       {result.entry_price:.2f}",
                f"Stop Loss:   {result.stop_loss:.2f}  ({abs(result.entry_price - result.stop_loss) / result.entry_price * 100:.2f}%)",
                f"TP1:         {result.take_profit_1:.2f}  ({abs(result.take_profit_1 - result.entry_price) / result.entry_price * 100:.2f}%)",
                f"TP2:         {result.take_profit_2:.2f}",
                f"TP3:         {result.take_profit_3:.2f}",
                f"Risk/Reward: {result.risk_reward_ratio:.2f}",
            ]),
            ("REASONS", C["cyan"], [f"{'+' if any(w in r.upper() for w in ['BULL','BUY','ABOVE','POSITIVE']) else '-'} {r}" for r in result.reasons[:8]]),
            ("WARNINGS", C["orange"], result.warnings if result.warnings else ["No warnings"]),
        ]
        y = 0.88
        for title, color, items in sections:
            h = len(items) * 0.03 + 0.05
            _box(ax, 0.05, y - h + 0.02, 0.9, h, fc=C["bg2"], ec=C["grid"])
            _text(ax, 0.08, y, title, fs=12, color=color, fw="bold")
            y -= 0.04
            for item in items:
                is_bull = any(w in item.upper() for w in ["BULL", "BUY", "ABOVE", "POSITIVE", "+"])
                is_bear = any(w in item.upper() for w in ["BEAR", "SELL", "BELOW", "NEGATIVE", "-"])
                ic = C["green"] if is_bull and "+" in item else C["red"] if is_bear and "-" in item else C["text"]
                _text(ax, 0.1, y, item[:80], fs=9, color=ic, ff="monospace")
                y -= 0.03
            y -= 0.02
        pdf.savefig(fig, facecolor=C["bg"])
        plt.close(fig)

    def _page_indicators(self, pdf, result):
        fig = self._new_fig()
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_facecolor(C["bg"]); ax.axis("off")
        _text(ax, 0.5, 0.95, "TECHNICAL INDICATORS", fs=20, color=C["white"], ha="center", fw="bold")
        inds = result.indicators_summary
        keys = list(inds.keys())
        cols = 3
        per_col = len(keys) // cols + 1
        for col in range(cols):
            x = 0.08 + col * 0.32
            y = 0.90
            for row in range(per_col):
                idx = col * per_col + row
                if idx < len(keys):
                    k = keys[idx]
                    v = inds[k]
                    try:
                        nv = float(str(v).replace('%', '').replace('$', ''))
                        clr = C["green"] if nv > 0 else C["red"] if nv < 0 else C["text"]
                    except:
                        clr = C["text"]
                    _text(ax, x, y, f"{k}: {v}", fs=9, color=clr, ff="monospace")
                    y -= 0.04
        pdf.savefig(fig, facecolor=C["bg"])
        plt.close(fig)

    def _page_sr(self, pdf, result):
        fig = self._new_fig()
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_facecolor(C["bg"]); ax.axis("off")
        _text(ax, 0.5, 0.95, "SUPPORT & RESISTANCE", fs=20, color=C["white"], ha="center", fw="bold")
        cp = self.candles[-1].close
        y = 0.88
        _text(ax, 0.1, y, "RESISTANCE", fs=14, color=C["red"], fw="bold")
        y -= 0.05
        for i, r in enumerate(result.resistance_levels):
            d = (r - cp) / cp * 100
            bw = min(d / 5, 0.6)
            ax.add_patch(plt.Rectangle((0.15, y - 0.01), bw, 0.025, fc=C["red"], alpha=0.3,
                         transform=ax.transAxes, clip_on=False))
            _text(ax, 0.12, y, f"R{i+1}: {r:.2f}  (+{d:.2f}%)", fs=10, color=C["red"], ff="monospace")
            y -= 0.04
        y -= 0.02
        _box(ax, 0.08, y - 0.01, 0.84, 0.03, fc=C["blue"], ec=C["blue"], alpha=0.5)
        _text(ax, 0.5, y, f"CURRENT: {cp:.2f}", fs=12, color="white", ha="center", fw="bold")
        y -= 0.05
        _text(ax, 0.1, y, "SUPPORT", fs=14, color=C["green"], fw="bold")
        y -= 0.05
        for i, s in enumerate(result.support_levels):
            d = (cp - s) / cp * 100
            bw = min(d / 5, 0.6)
            ax.add_patch(plt.Rectangle((0.15, y - 0.01), bw, 0.025, fc=C["green"], alpha=0.3,
                         transform=ax.transAxes, clip_on=False))
            _text(ax, 0.12, y, f"S{i+1}: {s:.2f}  (-{d:.2f}%)", fs=10, color=C["green"], ff="monospace")
            y -= 0.04
        pdf.savefig(fig, facecolor=C["bg"])
        plt.close(fig)

    def _page_enhanced(self, pdf, enhanced_data):
        if not enhanced_data:
            return
        fig = self._new_fig()
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_facecolor(C["bg"]); ax.axis("off")
        _text(ax, 0.5, 0.95, "ENHANCED ANALYSIS", fs=20, color=C["white"], ha="center", fw="bold")
        y = 0.90
        secs = []
        if 'multi_timeframe' in enhanced_data:
            items = [f"{tf}: {d['trend']}" for tf, d in enhanced_data['multi_timeframe'].items()]
            secs.append(("MULTI-TIMEFRAME", C["cyan"], items))
        if 'fibonacci' in enhanced_data:
            fib = enhanced_data['fibonacci']
            items = [f"Position: {fib.get('position', {}).get('price_position', 'N/A')}"]
            for n, l in list(fib.get('levels', {}).items())[:4]:
                items.append(f"{n}: {l:.2f}")
            secs.append(("FIBONACCI", C["purple"], items))
        if 'volatility' in enhanced_data:
            v = enhanced_data['volatility']
            items = [f"HV: {v.get('historical_volatility', 0):.2f}%",
                     f"Sharpe: {v.get('sharpe_ratio', 0):.2f}",
                     f"Sortino: {v.get('sortino_ratio', 0):.2f}",
                     f"MaxDD: {v.get('max_drawdown', {}).get('max_drawdown_pct', 0):.2f}%"]
            secs.append(("VOLATILITY", C["orange"], items))
        if 'regime' in enhanced_data:
            r = enhanced_data['regime']
            items = [f"Regime: {r.get('regime', 'N/A')}",
                     f"Strategy: {r.get('strategy', 'N/A')}",
                     f"ADX: {r.get('adx', 0):.1f}"]
            secs.append(("MARKET REGIME", C["teal"], items))
        if 'confidence' in enhanced_data:
            c = enhanced_data['confidence']
            items = [f"Score: {c.get('total_score', 0)}/{c.get('max_possible', 100)} ({c.get('confidence_pct', 0):.0f}%)",
                     f"Rating: {c.get('rating', 'N/A')}"]
            secs.append(("CONFIDENCE", C["yellow"], items))
        for title, color, items in secs:
            h = len(items) * 0.03 + 0.05
            _box(ax, 0.05, y - h + 0.02, 0.9, h, fc=C["bg2"], ec=C["grid"])
            _text(ax, 0.08, y, title, fs=12, color=color, fw="bold")
            y -= 0.04
            for item in items:
                _text(ax, 0.1, y, item, fs=9, color=C["text"], ff="monospace")
                y -= 0.03
            y -= 0.02
        pdf.savefig(fig, facecolor=C["bg"])
        plt.close(fig)

    def _page_backtest(self, pdf, bt):
        if not bt or bt.get('total_trades', 0) == 0:
            return
        fig = self._new_fig()
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_facecolor(C["bg"]); ax.axis("off")
        _text(ax, 0.5, 0.95, "BACKTEST RESULTS", fs=20, color=C["white"], ha="center", fw="bold")
        items = [
            f"Capital:      ${bt.get('initial_capital', 0):,.2f} -> ${bt.get('final_capital', 0):,.2f}",
            f"Return:       {bt.get('total_return_pct', 0):.2f}%  (B&H: {bt.get('buy_hold_return_pct', 0):.2f}%)",
            f"Alpha:        {bt.get('alpha', 0):.2f}%",
            f"Trades:       {bt.get('total_trades', 0)}  (W:{bt.get('winning_trades', 0)} / L:{bt.get('losing_trades', 0)})",
            f"Win Rate:     {bt.get('win_rate', 0):.1f}%",
            f"Profit Factor: {bt.get('profit_factor', 0):.2f}",
            f"Max Drawdown: {bt.get('max_drawdown', 0):.2f}%",
            f"Sharpe:       {bt.get('sharpe_ratio', 0):.2f}",
        ]
        y = 0.88
        for item in items:
            _text(ax, 0.1, y, item, fs=11, color=C["text"], ff="monospace")
            y -= 0.05
        pdf.savefig(fig, facecolor=C["bg"])
        plt.close(fig)

    def _page_risk(self, pdf, _=None):
        fig = self._new_fig()
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_facecolor(C["bg"]); ax.axis("off")
        _text(ax, 0.5, 0.95, "RISK MANAGEMENT & DISCLAIMER", fs=18, color=C["white"], ha="center", fw="bold")
        lines = [
            ("RISK GUIDELINES", C["yellow"], [
                "1. Never risk more than 2% per trade",
                "2. Always set stop loss before entry",
                "3. Take partial profits: 30% TP1, 40% TP2, 30% TP3",
                "4. Move SL to breakeven after TP1",
                "5. Monitor volume for confirmation",
                "6. Reduce leverage in high volatility",
                "7. Do not chase >1 ATR from entry",
                "8. Check news before entering",
            ]),
            ("DISCLAIMER", C["orange"], [
                "This report is for educational purposes only.",
                "Trading involves substantial risk of loss.",
                "Past performance does not guarantee future results.",
                "Always do your own research.",
                "Not financial advice.",
            ]),
        ]
        y = 0.88
        for title, color, items in lines:
            _text(ax, 0.1, y, title, fs=13, color=color, fw="bold")
            y -= 0.04
            for item in items:
                _text(ax, 0.12, y, item, fs=9, color=C["text"])
                y -= 0.035
            y -= 0.03
        _text(ax, 0.5, 0.04, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}  |  SMA 50 Bot v2.0",
              fs=8, color=C["text_dim"], ha="center")
        pdf.savefig(fig, facecolor=C["bg"])
        plt.close(fig)

class ChartGenerator:
    """Generate professional trading charts with indicators."""

    def __init__(self, candles: List[Candle]):
        self.candles = candles
        self.closes = [c.close for c in candles]
        self.opens = [c.open for c in candles]
        self.highs = [c.high for c in candles]
        self.lows = [c.low for c in candles]
        self.volumes = [c.volume for c in candles]
        self.dates = [c.timestamp for c in candles]
        self.ti = TechnicalIndicators()

    def _create_candlestick_panel(self, ax, indices, opens, highs, lows, closes,
                                   sma50_vals, sma200_vals=None,
                                   bb_upper=None, bb_lower=None,
                                   support_levels=None, resistance_levels=None,
                                   vwap_vals=None):
        """Draw candlestick chart on the given axis."""
        width = 0.6
        for i in range(len(indices)):
            color = COLORS["green"] if closes[i] >= opens[i] else COLORS["red"]
            body_bottom = min(opens[i], closes[i])
            body_height = abs(closes[i] - opens[i])
            if body_height == 0:
                body_height = (highs[i] - lows[i]) * 0.01
            ax.bar(indices[i], body_height, width, bottom=body_bottom,
                   color=color, edgecolor=color, linewidth=0.5, alpha=0.9)
            ax.plot([indices[i], indices[i]], [lows[i], body_bottom],
                    color=color, linewidth=0.8)
            ax.plot([indices[i], indices[i]], [body_bottom + body_height, highs[i]],
                    color=color, linewidth=0.8)

        if sma50_vals is not None:
            valid_sma = [(i, v) for i, v in zip(indices, sma50_vals) if v > 0]
            if valid_sma:
                si, sv = zip(*valid_sma)
                ax.plot(si, sv, color=COLORS["cyan"], linewidth=1.8, label="SMA 50", alpha=0.9)

        if sma50_vals is not None:
            valid_sma = [(i, v) for i, v in zip(indices, sma50_vals) if v > 0]
            if valid_sma:
                si, sv = zip(*valid_sma)
                ax.plot(si, sv, color=COLORS["orange"], linewidth=1.2, label="SMA 50",
                        linestyle="--", alpha=0.7)

        if bb_upper is not None and bb_lower is not None:
            valid_upper = [(i, v) for i, v in zip(indices, bb_upper) if v > 0]
            valid_lower = [(i, v) for i, v in zip(indices, bb_lower) if v > 0]
            if valid_upper and valid_lower:
                ui, uv = zip(*valid_upper)
                li, lv = zip(*valid_lower)
                ax.plot(ui, uv, color=COLORS["purple"], linewidth=0.8, alpha=0.5, label="BB Upper")
                ax.plot(li, lv, color=COLORS["purple"], linewidth=0.8, alpha=0.5, label="BB Lower")
                ax.fill_between(ui, uv, lv, color=COLORS["purple"], alpha=0.05)

        if vwap_vals is not None:
            valid_vwap = [(i, v) for i, v in zip(indices, vwap_vals) if v > 0]
            if valid_vwap:
                vi, vv = zip(*valid_vwap)
                ax.plot(vi, vv, color=COLORS["yellow"], linewidth=1.0, linestyle="-.",
                        label="VWAP", alpha=0.6)

        if support_levels:
            for i, s in enumerate(support_levels):
                ax.axhline(y=s, color=COLORS["green"], linewidth=0.8, linestyle="--",
                           alpha=0.5, label=f"S{i+1}: {s:.2f}")

        if resistance_levels:
            for i, r in enumerate(resistance_levels):
                ax.axhline(y=r, color=COLORS["red"], linewidth=0.8, linestyle="--",
                           alpha=0.5, label=f"R{i+1}: {r:.2f}")

        ax.legend(loc="upper left", fontsize=7, facecolor=COLORS["bg2"],
                  edgecolor=COLORS["grid"], labelcolor=COLORS["text"], ncol=3)
        ax.set_ylabel("Price", color=COLORS["text"], fontsize=9)
        ax.tick_params(colors=COLORS["text"], labelsize=8)
        ax.grid(True, color=COLORS["grid"], alpha=0.3, linewidth=0.5)
        ax.set_facecolor(COLORS["bg"])
        for spine in ax.spines.values():
            spine.set_color(COLORS["grid"])

    def _create_volume_panel(self, ax, indices, volumes, opens, closes):
        """Draw volume bars."""
        colors = []
        for i in range(len(indices)):
            if closes[i] >= opens[i]:
                colors.append(COLORS["green"])
            else:
                colors.append(COLORS["red"])
        ax.bar(indices, volumes, color=colors, alpha=0.7, width=0.6)
        if len(volumes) > 20:
            vol_sma = pd.Series(volumes).rolling(20).mean().values
            valid_vol = [(i, v) for i, v in zip(indices, vol_sma) if not np.isnan(v)]
            if valid_vol:
                vi, vv = zip(*valid_vol)
                ax.plot(vi, vv, color=COLORS["blue"], linewidth=1.0, label="Vol SMA50")
        ax.legend(loc="upper left", fontsize=7, facecolor=COLORS["bg2"],
                  edgecolor=COLORS["grid"], labelcolor=COLORS["text"])
        ax.set_ylabel("Volume", color=COLORS["text"], fontsize=9)
        ax.tick_params(colors=COLORS["text"], labelsize=8)
        ax.grid(True, color=COLORS["grid"], alpha=0.3, linewidth=0.5)
        ax.set_facecolor(COLORS["bg"])
        for spine in ax.spines.values():
            spine.set_color(COLORS["grid"])

    def _create_rsi_panel(self, ax, indices, rsi_vals):
        """Draw RSI indicator."""
        ax.plot(indices, rsi_vals, color=COLORS["purple"], linewidth=1.5, label="RSI(14)")
        ax.axhline(y=70, color=COLORS["red"], linewidth=0.8, linestyle="--", alpha=0.7)
        ax.axhline(y=30, color=COLORS["green"], linewidth=0.8, linestyle="--", alpha=0.7)
        ax.axhline(y=50, color=COLORS["text_dim"], linewidth=0.5, linestyle=":", alpha=0.5)
        ax.fill_between(indices, 70, [max(min(r, 100), 70) for r in rsi_vals],
                        color=COLORS["red"], alpha=0.1)
        ax.fill_between(indices, 30, [min(max(r, 0), 30) for r in rsi_vals],
                        color=COLORS["green"], alpha=0.1)
        rsi_current = rsi_vals[-1] if rsi_vals else 50
        rsi_color = COLORS["red"] if rsi_current > 70 else COLORS["green"] if rsi_current < 30 else COLORS["text"]
        rsi_label = "OVERBOUGHT" if rsi_current > 70 else "OVERSOLD" if rsi_current < 30 else "NEUTRAL"
        ax.text(0.99, 0.95, f"RSI: {rsi_current:.1f} ({rsi_label})",
                transform=ax.transAxes, fontsize=9, fontweight="bold",
                color=rsi_color, ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.3", facecolor=COLORS["bg2"],
                         edgecolor=rsi_color, alpha=0.9))
        ax.set_ylim(0, 100)
        ax.set_ylabel("RSI", color=COLORS["text"], fontsize=9)
        ax.tick_params(colors=COLORS["text"], labelsize=8)
        ax.grid(True, color=COLORS["grid"], alpha=0.3, linewidth=0.5)
        ax.set_facecolor(COLORS["bg"])
        for spine in ax.spines.values():
            spine.set_color(COLORS["grid"])

    def _create_macd_panel(self, ax, indices, macd_line, macd_signal, macd_hist):
        """Draw MACD indicator."""
        ax.plot(indices, macd_line, color=COLORS["blue"], linewidth=1.2, label="MACD")
        ax.plot(indices, macd_signal, color=COLORS["orange"], linewidth=1.0, label="Signal")
        hist_colors = [COLORS["green"] if h >= 0 else COLORS["red"] for h in macd_hist]
        ax.bar(indices, macd_hist, color=hist_colors, alpha=0.6, width=0.6)
        ax.axhline(y=0, color=COLORS["text_dim"], linewidth=0.5, linestyle=":")
        macd_val = macd_line[-1] if macd_line else 0
        signal_val = macd_signal[-1] if macd_signal else 0
        macd_color = COLORS["green"] if macd_val > signal_val else COLORS["red"]
        ax.text(0.99, 0.95, f"MACD: {macd_val:.2f}",
                transform=ax.transAxes, fontsize=9, fontweight="bold",
                color=macd_color, ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.3", facecolor=COLORS["bg2"],
                         edgecolor=macd_color, alpha=0.9))
        ax.legend(loc="upper left", fontsize=7, facecolor=COLORS["bg2"],
                  edgecolor=COLORS["grid"], labelcolor=COLORS["text"])
        ax.set_ylabel("MACD", color=COLORS["text"], fontsize=9)
        ax.tick_params(colors=COLORS["text"], labelsize=8)
        ax.grid(True, color=COLORS["grid"], alpha=0.3, linewidth=0.5)
        ax.set_facecolor(COLORS["bg"])
        for spine in ax.spines.values():
            spine.set_color(COLORS["grid"])

    def _create_stoch_panel(self, ax, indices, stoch_k, stoch_d):
        """Draw Stochastic Oscillator."""
        ax.plot(indices, stoch_k, color=COLORS["cyan"], linewidth=1.2, label="%K")
        ax.plot(indices, stoch_d, color=COLORS["pink"], linewidth=1.0, label="%D")
        ax.axhline(y=80, color=COLORS["red"], linewidth=0.8, linestyle="--", alpha=0.5)
        ax.axhline(y=20, color=COLORS["green"], linewidth=0.8, linestyle="--", alpha=0.5)
        ax.fill_between(indices, 80, [max(min(s, 100), 80) for s in stoch_k],
                        color=COLORS["red"], alpha=0.1)
        ax.fill_between(indices, 20, [min(max(s, 0), 20) for s in stoch_k],
                        color=COLORS["green"], alpha=0.1)
        ax.set_ylim(0, 100)
        ax.legend(loc="upper left", fontsize=7, facecolor=COLORS["bg2"],
                  edgecolor=COLORS["grid"], labelcolor=COLORS["text"])
        ax.set_ylabel("Stoch", color=COLORS["text"], fontsize=9)
        ax.tick_params(colors=COLORS["text"], labelsize=8)
        ax.grid(True, color=COLORS["grid"], alpha=0.3, linewidth=0.5)
        ax.set_facecolor(COLORS["bg"])
        for spine in ax.spines.values():
            spine.set_color(COLORS["grid"])

    def generate_full_chart(self, indicators: IndicatorValues,
                             result: SignalResult,
                             output_path: str,
                             enhanced_data: Dict[str, Any] = None) -> str:
        """Generate complete multi-panel trading chart."""
        if not HAS_MATPLOTLIB:
            print("[SKIP] matplotlib not available, skipping chart generation")
            return ""
        print(f"[CHART] Generating chart: {output_path}")
        ti = self.ti
        closes = np.array(self.closes)
        indices = list(range(len(self.candles)))
        sma50 = ti.sma(self.closes, 50)
        sma50 = ti.sma(self.closes, 50)
        bb_upper, bb_mid, bb_lower = ti.bollinger_bands(self.closes)
        rsi_vals = ti.rsi(self.closes)
        macd_line, macd_signal, macd_hist = ti.macd(self.closes)
        stoch_k, stoch_d = ti.stochastic(self.candles)
        vwap_vals = ti.vwap(self.candles)

        fig = plt.figure(figsize=(26, 22))
        gs = gridspec.GridSpec(6, 1, height_ratios=[4, 1, 1.2, 1, 1, 0.8],
                               hspace=0.08, figure=fig)
        fig.patch.set_facecolor(COLORS["bg"])

        ax_candle = fig.add_subplot(gs[0])
        ax_vol = fig.add_subplot(gs[1], sharex=ax_candle)
        ax_rsi = fig.add_subplot(gs[2], sharex=ax_candle)
        ax_macd = fig.add_subplot(gs[3], sharex=ax_candle)
        ax_stoch = fig.add_subplot(gs[4], sharex=ax_candle)
        ax_info = fig.add_subplot(gs[5])
        ax_info.axis("off")

        self._create_candlestick_panel(
            ax_candle, indices, self.opens, self.highs, self.lows, self.closes,
            sma50, sma50, bb_upper, bb_lower,
            result.support_levels, result.resistance_levels,
            vwap_vals
        )
        self._create_volume_panel(ax_vol, indices, self.volumes, self.opens, self.closes)
        self._create_rsi_panel(ax_rsi, indices, rsi_vals)
        self._create_macd_panel(ax_macd, indices, macd_line, macd_signal, macd_hist)
        self._create_stoch_panel(ax_stoch, indices, stoch_k, stoch_d)

        signal_color = COLORS["green"] if "BUY" in result.signal_type.value else \
                      COLORS["red"] if "SELL" in result.signal_type.value else COLORS["orange"]
        fig.text(0.5, 0.98, f"SMA 50 TRADING BOT  |  {result.signal_type.value}  |  "
                 f"Confidence: {result.confidence:.0f}%",
                 fontsize=16, fontweight="bold", color=signal_color,
                 ha="center", va="top",
                 bbox=dict(boxstyle="round,pad=0.5", facecolor=COLORS["bg2"],
                          edgecolor=signal_color, alpha=0.95))

        current_price = self.candles[-1].close
        c = self.candles[-1]
        date_str = c.timestamp.strftime('%Y-%m-%d %H:%M UTC')
        info_text = (f"Close: {current_price:.2f}  |  "
                    f"SMA50: {indicators.sma50:.2f}  |  "
                    f"RSI: {indicators.rsi:.1f}  |  "
                    f"MACD: {indicators.macd_line:.4f}  |  "
                    f"ATR: {indicators.atr:.2f} ({indicators.atr_percent:.2f}%)  |  "
                    f"ADX: {indicators.adx:.1f}  |  "
                    f"Vol Ratio: {result.indicators_summary.get('Volume Ratio', 'N/A')}")
        fig.text(0.5, 0.96, info_text, fontsize=9, color=COLORS["text_dim"],
                 ha="center", va="top", fontfamily="monospace")

        date_labels = []
        tick_positions = []
        step = max(1, len(self.candles) // 20)
        for i in range(0, len(self.candles), step):
            tick_positions.append(i)
            date_labels.append(self.candles[i].timestamp.strftime('%m/%d'))
        ax_stoch.set_xticks(tick_positions)
        ax_stoch.set_xticklabels(date_labels, rotation=45, fontsize=7)
        for ax in [ax_candle, ax_vol, ax_rsi, ax_macd, ax_stoch]:
            plt.setp(ax.get_xticklabels(), visible=False)
        plt.setp(ax_stoch.get_xticklabels(), visible=True)

        if result.signal_type != SignalType.HOLD:
            if result.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                marker_color = COLORS["green"]
                marker = "^"
                y_offset = current_price * 0.995
            else:
                marker_color = COLORS["red"]
                marker = "v"
                y_offset = current_price * 1.005
            ax_candle.scatter([len(self.candles)-1], [y_offset],
                            marker=marker, s=200, color=marker_color, zorder=10,
                            edgecolors="white", linewidth=1.5)
            ax_candle.annotate(f"{result.signal_type.value}\n{current_price:.2f}",
                             xy=(len(self.candles)-1, y_offset),
                             xytext=(len(self.candles)-5, y_offset * (1.03 if "BUY" in result.signal_type.value else 0.97)),
                             fontsize=9, fontweight="bold", color=marker_color,
                             arrowprops=dict(arrowstyle="->", color=marker_color, lw=1.5),
                             bbox=dict(boxstyle="round,pad=0.3", facecolor=COLORS["bg2"],
                                      edgecolor=marker_color, alpha=0.9))

        if result.stop_loss > 0 and result.take_profit_1 > 0:
            ax_candle.axhline(y=result.stop_loss, color=COLORS["red"], linewidth=1.2,
                             linestyle="-.", alpha=0.7)
            ax_candle.text(len(self.candles)-1, result.stop_loss,
                          f" SL: {result.stop_loss:.2f}", fontsize=8,
                          color=COLORS["red"], va="center", fontweight="bold")
            ax_candle.axhline(y=result.take_profit_1, color=COLORS["green"], linewidth=1.2,
                             linestyle="-.", alpha=0.7)
            ax_candle.text(len(self.candles)-1, result.take_profit_1,
                          f" TP1: {result.take_profit_1:.2f}", fontsize=8,
                          color=COLORS["green"], va="center", fontweight="bold")

        plt.savefig(output_path, dpi=200, bbox_inches="tight",
                   facecolor=COLORS["bg"], pad_inches=0.3,
                   pil_kwargs={"antialias": "best"})
        plt.close(fig)
        print(f"[CHART] Saved: {output_path}")
        return output_path

    def generate_reasoning_chart(self, result: SignalResult,
                                  enhanced_data: Dict[str, Any],
                                  output_path: str) -> str:
        """Generate a reasoning/analysis summary chart."""
        if not HAS_MATPLOTLIB:
            return ""
        print(f"[CHART] Generating reasoning chart: {output_path}")
        fig, axes = plt.subplots(2, 3, figsize=(26, 14))
        fig.patch.set_facecolor(COLORS["bg"])
        fig.suptitle("ANALYSIS REASONS & INDICATOR SCORES",
                     fontsize=16, fontweight="bold", color=COLORS["white"], y=0.98)

        ax1 = axes[0, 0]
        indicators = list(result.indicators_summary.keys())[:12]
        values = []
        for k in indicators:
            v = result.indicators_summary[k]
            try:
                values.append(float(str(v).replace('%', '').replace('$', '')))
            except:
                values.append(0)
        colors_bar = [COLORS["green"] if v > 0 else COLORS["red"] for v in values]
        y_pos = range(len(indicators))
        ax1.barh(y_pos, values, color=colors_bar, alpha=0.7, height=0.6)
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(indicators, fontsize=7, color=COLORS["text"])
        ax1.set_title("Indicator Values", color=COLORS["text"], fontsize=11, fontweight="bold")
        ax1.set_facecolor(COLORS["bg"])
        ax1.tick_params(colors=COLORS["text"], labelsize=8)
        ax1.grid(True, axis="x", color=COLORS["grid"], alpha=0.3)
        for spine in ax1.spines.values():
            spine.set_color(COLORS["grid"])

        ax2 = axes[0, 1]
        if enhanced_data and 'confidence' in enhanced_data:
            factors = enhanced_data['confidence'].get('factors', {})
            factor_names = list(factors.keys())
            factor_vals = list(factors.values())
            factor_colors = [COLORS["cyan"] if v >= 5 else COLORS["orange"] if v >= 3 else COLORS["red"]
                           for v in factor_vals]
            y_pos = range(len(factor_names))
            ax2.barh(y_pos, factor_vals, color=factor_colors, alpha=0.8, height=0.6)
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels([n.replace('_', ' ').title() for n in factor_names],
                               fontsize=7, color=COLORS["text"])
        ax2.set_title("Confidence Factors", color=COLORS["text"], fontsize=11, fontweight="bold")
        ax2.set_facecolor(COLORS["bg"])
        ax2.tick_params(colors=COLORS["text"], labelsize=8)
        ax2.grid(True, axis="x", color=COLORS["grid"], alpha=0.3)
        for spine in ax2.spines.values():
            spine.set_color(COLORS["grid"])

        ax3 = axes[0, 2]
        reasons = result.reasons[:10]
        reason_colors = []
        for r in reasons:
            if "BULL" in r.upper() or "BUY" in r.upper() or "ABOVE" in r.upper() or "POSITIVE" in r.upper():
                reason_colors.append(COLORS["green"])
            elif "BEAR" in r.upper() or "SELL" in r.upper() or "BELOW" in r.upper() or "NEGATIVE" in r.upper():
                reason_colors.append(COLORS["red"])
            else:
                reason_colors.append(COLORS["text"])
        for i, (reason, color) in enumerate(zip(reasons, reason_colors)):
            y = 0.95 - i * 0.1
            marker = "+" if color == COLORS["green"] else "-" if color == COLORS["red"] else "~"
            ax3.text(0.05, y, f" {marker} {reason[:65]}", transform=ax3.transAxes,
                    fontsize=8, color=color, fontfamily="monospace",
                    verticalalignment="top")
        ax3.set_title("Signal Reasons", color=COLORS["text"], fontsize=11, fontweight="bold")
        ax3.axis("off")
        ax3.set_facecolor(COLORS["bg"])

        ax4 = axes[1, 0]
        signal_labels = ["BUY", "HOLD", "SELL"]
        signal_sizes = [0, 0, 0]
        if "BUY" in result.signal_type.value:
            signal_sizes = [result.confidence, 100 - result.confidence, 0]
            signal_colors = [COLORS["green"], COLORS["grid"], COLORS["grid"]]
        elif "SELL" in result.signal_type.value:
            signal_sizes = [0, 100 - result.confidence, result.confidence]
            signal_colors = [COLORS["grid"], COLORS["grid"], COLORS["red"]]
        else:
            signal_sizes = [0, result.confidence, 100 - result.confidence]
            signal_colors = [COLORS["grid"], COLORS["orange"], COLORS["grid"]]
        wedges, texts = ax4.pie(signal_sizes, labels=signal_labels, colors=signal_colors,
                                startangle=90, textprops={"color": COLORS["text"], "fontsize": 9})
        ax4.set_title(f"Signal: {result.signal_type.value}", color=signal_colors[0],
                     fontsize=12, fontweight="bold")

        ax5 = axes[1, 1]
        if enhanced_data and 'multi_timeframe' in enhanced_data:
            tf_data = enhanced_data['multi_timeframe']
            tf_names = list(tf_data.keys())
            tf_scores = []
            tf_colors = []
            for tf_name in tf_names:
                tf = tf_data[tf_name]
                if tf['trend'] == 'BULLISH':
                    tf_scores.append(tf.get('strength', 5))
                    tf_colors.append(COLORS["green"])
                elif tf['trend'] == 'BEARISH':
                    tf_scores.append(-tf.get('strength', 5))
                    tf_colors.append(COLORS["red"])
                else:
                    tf_scores.append(0)
                    tf_colors.append(COLORS["orange"])
            bars = ax5.bar(tf_names, tf_scores, color=tf_colors, alpha=0.8, width=0.5)
            ax5.axhline(y=0, color=COLORS["text_dim"], linewidth=0.8)
            ax5.set_title("Multi-Timeframe Alignment", color=COLORS["text"],
                         fontsize=11, fontweight="bold")
        ax5.set_facecolor(COLORS["bg"])
        ax5.tick_params(colors=COLORS["text"], labelsize=8)
        ax5.grid(True, axis="y", color=COLORS["grid"], alpha=0.3)
        for spine in ax5.spines.values():
            spine.set_color(COLORS["grid"])

        ax6 = axes[1, 2]
        risk_data = {
            "Entry": result.entry_price,
            "Stop Loss": result.stop_loss,
            "TP1": result.take_profit_1,
            "TP2": result.take_profit_2,
            "TP3": result.take_profit_3
        }
        risk_colors = [COLORS["blue"], COLORS["red"], COLORS["green"],
                      COLORS["green"], COLORS["green"]]
        if result.risk_reward_ratio > 0:
            bars = ax6.barh(list(risk_data.keys()), list(risk_data.values()),
                           color=risk_colors, alpha=0.8, height=0.5)
            ax6.set_title(f"Trade Plan (R:R = {result.risk_reward_ratio:.2f})",
                         color=COLORS["text"], fontsize=11, fontweight="bold")
        else:
            ax6.text(0.5, 0.5, "HOLD\nNo active trade",
                    transform=ax6.transAxes, fontsize=14, color=COLORS["orange"],
                    ha="center", va="center", fontweight="bold")
            ax6.set_title("Trade Plan", color=COLORS["text"], fontsize=11, fontweight="bold")
        ax6.set_facecolor(COLORS["bg"])
        ax6.tick_params(colors=COLORS["text"], labelsize=8)
        ax6.grid(True, axis="x", color=COLORS["grid"], alpha=0.3)
        for spine in ax6.spines.values():
            spine.set_color(COLORS["grid"])

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(output_path, dpi=200, bbox_inches="tight",
                   facecolor=COLORS["bg"], pad_inches=0.3,
                   pil_kwargs={"antialias": "best"})
        plt.close(fig)
        print(f"[CHART] Saved: {output_path}")
        return output_path


# ============================================================================
# SECTION 26: PDF REPORT GENERATOR
# ============================================================================

class PDFReportGenerator:
    """Generate comprehensive PDF reports with charts and analysis."""

    def __init__(self, candles: List[Candle]):
        self.candles = candles
        self.chart_gen = ChartGenerator(candles)

    def generate_pdf(self, result: SignalResult,
                     enhanced_data: Dict[str, Any],
                     bt_result: Dict[str, Any],
                     output_path: str) -> str:
        """Generate complete PDF report."""
        if not HAS_MATPLOTLIB:
            print("[SKIP] matplotlib not available, skipping PDF generation")
            return ""
        print(f"\n[PDF] Generating PDF report: {output_path}")
        pdf = PdfPages(output_path)
        self._add_cover_page(pdf, result)
        self._add_signal_page(pdf, result, enhanced_data)
        chart_dir = os.path.join(os.path.dirname(output_path), "temp_charts")
        os.makedirs(chart_dir, exist_ok=True)
        main_chart_path = os.path.join(chart_dir, "main_chart.png")
        self.chart_gen.generate_full_chart(
            enhanced_data.get('indicators', IndicatorValues()) if enhanced_data else IndicatorValues(),
            result, main_chart_path, enhanced_data
        )
        if os.path.exists(main_chart_path):
            self._add_chart_page(pdf, main_chart_path, "Main Analysis Chart")
        reasoning_chart_path = os.path.join(chart_dir, "reasoning_chart.png")
        self.chart_gen.generate_reasoning_chart(result, enhanced_data, reasoning_chart_path)
        if os.path.exists(reasoning_chart_path):
            self._add_chart_page(pdf, reasoning_chart_path, "Analysis Reasons & Scores")
        self._add_indicators_page(pdf, result)
        self._add_support_resistance_page(pdf, result)
        if enhanced_data:
            self._add_enhanced_page(pdf, enhanced_data)
        if bt_result and bt_result.get('total_trades', 0) > 0:
            self._add_backtest_page(pdf, bt_result)
        self._add_risk_management_page(pdf, result)
        self._add_disclaimer_page(pdf)
        pdf.close()
        self._cleanup_temp_charts(chart_dir)
        print(f"[PDF] Saved: {output_path}")
        return output_path

    def _add_cover_page(self, pdf, result: SignalResult):
        """Add cover page to PDF."""
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.patch.set_facecolor(COLORS["bg"])
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_facecolor(COLORS["bg"])
        ax.axis("off")
        ax.text(0.5, 0.88, "SMA 50 TRADING BOT", fontsize=28, fontweight="bold",
                color=COLORS["white"], ha="center", va="center", fontfamily="Vazirmatn")
        ax.text(0.5, 0.80, "Trend Direction & Dynamic Support/Resistance Analysis",
                fontsize=14, color=COLORS["text_dim"], ha="center", va="center")
        ax.text(0.5, 0.72, "Complete Technical Analysis Report",
                fontsize=12, color=COLORS["text_dim"], ha="center", va="center")

        signal_color = COLORS["green"] if "BUY" in result.signal_type.value else \
                      COLORS["red"] if "SELL" in result.signal_type.value else COLORS["orange"]
        ax.add_patch(plt.Rectangle((0.25, 0.42), 0.5, 0.18,
                     facecolor=COLORS["bg2"], edgecolor=signal_color,
                     linewidth=3, transform=ax.transAxes, clip_on=False,
                     zorder=1))
        ax.text(0.5, 0.54, result.signal_type.value, fontsize=32, fontweight="bold",
                color=signal_color, ha="center", va="center", zorder=2)
        ax.text(0.5, 0.46, f"Confidence: {result.confidence:.0f}%",
                fontsize=16, color=COLORS["text"], ha="center", va="center", zorder=2)

        info_lines = [
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
            f"Last Candle: {self.candles[-1].timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
            f"Candles Analyzed: {len(self.candles)}",
            f"Price Range: {min(c.low for c in self.candles):.2f} - {max(c.high for c in self.candles):.2f}",
            f"Current Price: {self.candles[-1].close:.2f}",
            f"Trend: {result.trend_direction.value}",
            f"Market Phase: {result.market_phase.value}",
        ]
        for i, line in enumerate(info_lines):
            ax.text(0.5, 0.32 - i * 0.035, line, fontsize=10, color=COLORS["text"],
                   ha="center", va="center", fontfamily="monospace")

        ax.text(0.5, 0.03, "Generated by SMA 50 Trading Bot v2.0",
                fontsize=8, color=COLORS["text_dim"], ha="center", va="center")
        pdf.savefig(fig, facecolor=COLORS["bg"])
        plt.close(fig)

    def _add_signal_page(self, pdf, result: SignalResult, enhanced_data):
        """Add signal summary page."""
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.patch.set_facecolor(COLORS["bg"])
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_facecolor(COLORS["bg"])
        ax.axis("off")
        ax.text(0.5, 0.96, "SIGNAL SUMMARY & TRADING PLAN",
                fontsize=18, fontweight="bold", color=COLORS["white"],
                ha="center", va="top")

        signal_color = COLORS["green"] if "BUY" in result.signal_type.value else \
                      COLORS["red"] if "SELL" in result.signal_type.value else COLORS["orange"]
        sections = [
            ("TRADING ACTIONS", [
                f"Overall Signal: {result.signal_type.value}",
                f"Confidence: {result.confidence:.1f}%",
                f"Spot Action: {result.spot_action}",
                f"Futures Action: {result.futures_action}",
                f"Leverage: {result.leverage_suggestion}",
                f"Position Size: {result.position_size_pct:.2f}% of portfolio",
            ]),
            ("TRADE PLAN", [
                f"Entry Price: {result.entry_price:.2f}",
                f"Stop Loss: {result.stop_loss:.2f}",
                f"Take Profit 1: {result.take_profit_1:.2f}",
                f"Take Profit 2: {result.take_profit_2:.2f}",
                f"Take Profit 3: {result.take_profit_3:.2f}",
                f"Risk/Reward: {result.risk_reward_ratio:.2f}",
            ]),
            ("TREND & MARKET", [
                f"Trend Direction: {result.trend_direction.value}",
                f"Market Phase: {result.market_phase.value}",
                f"Patterns: {', '.join(result.patterns_detected) if result.patterns_detected else 'None'}",
            ]),
        ]

        y = 0.88
        for section_title, items in sections:
            ax.add_patch(plt.Rectangle((0.05, y - len(items)*0.035 - 0.02), 0.9, len(items)*0.035 + 0.06,
                         facecolor=COLORS["bg2"], edgecolor=COLORS["grid"],
                         linewidth=1, transform=ax.transAxes, clip_on=False))
            ax.text(0.08, y, section_title, fontsize=12, fontweight="bold",
                   color=signal_color, transform=ax.transAxes)
            y -= 0.04
            for item in items:
                ax.text(0.1, y, item, fontsize=9, color=COLORS["text"],
                       fontfamily="monospace", transform=ax.transAxes)
                y -= 0.035
            y -= 0.02

        pdf.savefig(fig, facecolor=COLORS["bg"])
        plt.close(fig)

    def _add_chart_page(self, pdf, chart_path: str, title: str):
        """Add a chart image page."""
        if not os.path.exists(chart_path):
            return
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.patch.set_facecolor(COLORS["bg"])
        ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_facecolor(COLORS["bg"])
        ax.axis("off")
        try:
            img = plt.imread(chart_path)
            ax.imshow(img, aspect="auto", extent=[0.02, 0.98, 0.02, 0.98])
        except Exception as e:
            ax.text(0.5, 0.5, f"Chart could not be loaded: {e}",
                   transform=ax.transAxes, fontsize=10, color=COLORS["red"],
                   ha="center", va="center")
        pdf.savefig(fig, facecolor=COLORS["bg"])
        plt.close(fig)

    def _add_indicators_page(self, pdf, result: SignalResult):
        """Add technical indicators page."""
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.patch.set_facecolor(COLORS["bg"])
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_facecolor(COLORS["bg"])
        ax.axis("off")
        ax.text(0.5, 0.96, "TECHNICAL INDICATORS",
                fontsize=18, fontweight="bold", color=COLORS["white"],
                ha="center", va="top")

        indicators = result.indicators_summary
        keys = list(indicators.keys())
        col_size = len(keys) // 3 + 1
        for col in range(3):
            start_idx = col * col_size
            end_idx = min(start_idx + col_size, len(keys))
            x = 0.08 + col * 0.32
            y = 0.90
            for idx in range(start_idx, end_idx):
                if idx < len(keys):
                    key = keys[idx]
                    val = indicators[key]
                    try:
                        num_val = float(str(val).replace('%', '').replace('$', ''))
                        if num_val > 0:
                            color = COLORS["green"]
                        elif num_val < 0:
                            color = COLORS["red"]
                        else:
                            color = COLORS["text"]
                    except:
                        color = COLORS["text"]
                    ax.text(x, y, f"{key}: {val}", fontsize=8, color=color,
                           fontfamily="monospace", transform=ax.transAxes)
                    y -= 0.04

        pdf.savefig(fig, facecolor=COLORS["bg"])
        plt.close(fig)

    def _add_support_resistance_page(self, pdf, result: SignalResult):
        """Add support/resistance levels page."""
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.patch.set_facecolor(COLORS["bg"])
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_facecolor(COLORS["bg"])
        ax.axis("off")
        ax.text(0.5, 0.96, "SUPPORT & RESISTANCE LEVELS",
                fontsize=18, fontweight="bold", color=COLORS["white"],
                ha="center", va="top")

        current_price = self.candles[-1].close
        y = 0.88
        if result.resistance_levels:
            ax.text(0.1, y, "RESISTANCE LEVELS", fontsize=12, fontweight="bold",
                   color=COLORS["red"], transform=ax.transAxes)
            y -= 0.05
            for i, r in enumerate(result.resistance_levels):
                dist = (r - current_price) / current_price * 100
                ax.text(0.12, y, f"R{i+1}: {r:.2f} (+{dist:.2f}%)",
                       fontsize=9, color=COLORS["red"], fontfamily="monospace",
                       transform=ax.transAxes)
                bar_width = min(dist / 10, 0.6)
                ax.add_patch(plt.Rectangle((0.45, y - 0.01), bar_width, 0.025,
                             facecolor=COLORS["red"], alpha=0.3,
                             transform=ax.transAxes, clip_on=False))
                y -= 0.04

        y -= 0.02
        ax.add_patch(plt.Rectangle((0.08, y - 0.01), 0.84, 0.03,
                     facecolor=COLORS["blue"], alpha=0.5,
                     transform=ax.transAxes, clip_on=False))
        ax.text(0.5, y, f"CURRENT: {current_price:.2f}", fontsize=11, fontweight="bold",
               color=COLORS["white"], ha="center", transform=ax.transAxes)
        y -= 0.05

        if result.support_levels:
            ax.text(0.1, y, "SUPPORT LEVELS", fontsize=12, fontweight="bold",
                   color=COLORS["green"], transform=ax.transAxes)
            y -= 0.05
            for i, s in enumerate(result.support_levels):
                dist = (current_price - s) / current_price * 100
                ax.text(0.12, y, f"S{i+1}: {s:.2f} (-{dist:.2f}%)",
                       fontsize=9, color=COLORS["green"], fontfamily="monospace",
                       transform=ax.transAxes)
                bar_width = min(dist / 10, 0.6)
                ax.add_patch(plt.Rectangle((0.45, y - 0.01), bar_width, 0.025,
                             facecolor=COLORS["green"], alpha=0.3,
                             transform=ax.transAxes, clip_on=False))
                y -= 0.04

        pdf.savefig(fig, facecolor=COLORS["bg"])
        plt.close(fig)

    def _add_enhanced_page(self, pdf, enhanced_data: Dict[str, Any]):
        """Add enhanced analysis page."""
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.patch.set_facecolor(COLORS["bg"])
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_facecolor(COLORS["bg"])
        ax.axis("off")
        ax.text(0.5, 0.96, "ENHANCED ANALYSIS",
                fontsize=18, fontweight="bold", color=COLORS["white"],
                ha="center", va="top")

        y = 0.90
        sections = []
        if 'multi_timeframe' in enhanced_data:
            mtf = enhanced_data['multi_timeframe']
            mtf_items = []
            for tf, data in mtf.items():
                trend_icon = ">>>" if data['trend'] == 'BULLISH' else "<<<" if data['trend'] == 'BEARISH' else "==="
                mtf_items.append(f"{tf}: {data['trend']} {trend_icon}")
            sections.append(("MULTI-TIMEFRAME", mtf_items))

        if 'fibonacci' in enhanced_data:
            fib = enhanced_data['fibonacci']
            fib_items = [f"Position: {fib.get('position', {}).get('price_position', 'N/A')}"]
            levels = fib.get('levels', {})
            for name, level in list(levels.items())[:4]:
                fib_items.append(f"{name}: {level:.2f}")
            sections.append(("FIBONACCI", fib_items))

        if 'volatility' in enhanced_data:
            vol = enhanced_data['volatility']
            vol_items = [
                f"Historical Vol: {vol.get('historical_volatility', 0):.2f}%",
                f"Sharpe Ratio: {vol.get('sharpe_ratio', 0):.2f}",
                f"Sortino Ratio: {vol.get('sortino_ratio', 0):.2f}",
                f"Max Drawdown: {vol.get('max_drawdown', {}).get('max_drawdown_pct', 0):.2f}%",
            ]
            sections.append(("VOLATILITY & RISK", vol_items))

        if 'regime' in enhanced_data:
            regime = enhanced_data['regime']
            regime_items = [
                f"Regime: {regime.get('regime', 'N/A')}",
                f"Strategy: {regime.get('strategy', 'N/A')}",
                f"ADX: {regime.get('adx', 0):.1f}",
                f"BB Width: {regime.get('bb_width', 0):.2f}%",
            ]
            sections.append(("MARKET REGIME", regime_items))

        if 'confidence' in enhanced_data:
            conf = enhanced_data['confidence']
            conf_items = [
                f"Score: {conf.get('total_score', 0)}/{conf.get('max_possible', 100)}",
                f"Confidence: {conf.get('confidence_pct', 0):.1f}%",
                f"Rating: {conf.get('rating', 'LOW')}",
            ]
            sections.append(("CONFIDENCE", conf_items))

        for section_title, items in sections:
            ax.add_patch(plt.Rectangle((0.05, y - len(items)*0.035 - 0.02), 0.9, len(items)*0.035 + 0.06,
                         facecolor=COLORS["bg2"], edgecolor=COLORS["grid"],
                         linewidth=1, transform=ax.transAxes, clip_on=False))
            ax.text(0.08, y, section_title, fontsize=11, fontweight="bold",
                   color=COLORS["cyan"], transform=ax.transAxes)
            y -= 0.04
            for item in items:
                ax.text(0.1, y, item, fontsize=8, color=COLORS["text"],
                       fontfamily="monospace", transform=ax.transAxes)
                y -= 0.035
            y -= 0.02

        pdf.savefig(fig, facecolor=COLORS["bg"])
        plt.close(fig)

    def _add_backtest_page(self, pdf, bt_result: Dict[str, Any]):
        """Add backtest results page."""
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.patch.set_facecolor(COLORS["bg"])
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_facecolor(COLORS["bg"])
        ax.axis("off")
        ax.text(0.5, 0.96, "BACKTEST RESULTS",
                fontsize=18, fontweight="bold", color=COLORS["white"],
                ha="center", va="top")

        y = 0.88
        items = [
            f"Initial Capital: ${bt_result.get('initial_capital', 0):,.2f}",
            f"Final Capital: ${bt_result.get('final_capital', 0):,.2f}",
            f"Total Return: {bt_result.get('total_return_pct', 0):.2f}%",
            f"Buy & Hold Return: {bt_result.get('buy_hold_return_pct', 0):.2f}%",
            f"Alpha: {bt_result.get('alpha', 0):.2f}%",
            f"",
            f"Total Trades: {bt_result.get('total_trades', 0)}",
            f"Winning Trades: {bt_result.get('winning_trades', 0)}",
            f"Losing Trades: {bt_result.get('losing_trades', 0)}",
            f"Win Rate: {bt_result.get('win_rate', 0):.1f}%",
            f"Profit Factor: {bt_result.get('profit_factor', 0):.2f}",
            f"",
            f"Total Profit: ${bt_result.get('total_profit', 0):,.2f}",
            f"Total Loss: ${bt_result.get('total_loss', 0):,.2f}",
            f"Max Drawdown: {bt_result.get('max_drawdown', 0):.2f}%",
            f"Sharpe Ratio: {bt_result.get('sharpe_ratio', 0):.2f}",
        ]
        for item in items:
            if item:
                ax.text(0.1, y, item, fontsize=10, color=COLORS["text"],
                       fontfamily="monospace", transform=ax.transAxes)
            y -= 0.04

        pdf.savefig(fig, facecolor=COLORS["bg"])
        plt.close(fig)

    def _add_risk_management_page(self, pdf, result: SignalResult):
        """Add risk management guidelines page."""
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.patch.set_facecolor(COLORS["bg"])
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_facecolor(COLORS["bg"])
        ax.axis("off")
        ax.text(0.5, 0.96, "RISK MANAGEMENT GUIDELINES",
                fontsize=18, fontweight="bold", color=COLORS["white"],
                ha="center", va="top")

        guidelines = [
            "1. Never risk more than 2% of your portfolio on a single trade",
            "2. Always set stop loss before entering any position",
            "3. Take partial profits: 30% at TP1, 40% at TP2, 30% at TP3",
            "4. Move stop loss to breakeven after TP1 is hit",
            "5. Monitor volume for confirmation of trend continuation",
            "6. If ATR increases significantly, tighten stop loss",
            "7. Do not chase if price moves more than 1 ATR from entry",
            "8. Check for major news/events before entering",
            "9. Use proper position sizing based on account risk",
            "10. Keep a trading journal to track performance",
            "",
            "FUTURES-SPECIFIC:",
            "- Always use stop loss (liquidation risk)",
            "- Monitor funding rates before entry",
            "- Use cross margin for flexibility",
            "- Set liquidation buffer of 2x stop loss distance",
            "- Reduce leverage in high volatility",
            "",
            "DISCLAIMER:",
            "This is technical analysis for educational purposes only.",
            "Trading involves significant risk of financial loss.",
            "Always do your own research before making trading decisions.",
            "Past performance does not guarantee future results.",
        ]

        y = 0.88
        for line in guidelines:
            if line.startswith("FUTURES") or line.startswith("DISCLAIMER"):
                color = COLORS["orange"]
                fontsize = 11
            elif line.startswith("-"):
                color = COLORS["text_dim"]
                fontsize = 9
            else:
                color = COLORS["text"]
                fontsize = 9
            if line:
                ax.text(0.08, y, line, fontsize=fontsize, color=color,
                       fontfamily="monospace", transform=ax.transAxes)
            y -= 0.035

        pdf.savefig(fig, facecolor=COLORS["bg"])
        plt.close(fig)

    def _add_disclaimer_page(self, pdf):
        """Add disclaimer page."""
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.patch.set_facecolor(COLORS["bg"])
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_facecolor(COLORS["bg"])
        ax.axis("off")

        disclaimer_text = [
            "DISCLAIMER & TERMS OF USE",
            "",
            "This report is generated by an automated trading analysis system",
            "and is provided for informational and educational purposes only.",
            "",
            "NOT FINANCIAL ADVICE",
            "This report does not constitute financial advice, investment advice,",
            "trading advice, or any other form of professional advice. The analysis",
            "and signals provided are based on historical data and technical",
            "indicators which may not accurately predict future price movements.",
            "",
            "RISK WARNING",
            "Trading cryptocurrencies and financial instruments involves substantial",
            "risk of loss and is not suitable for every investor. The high degree",
            "of leverage can work against you as well as for you. Before deciding",
            "to trade, you should carefully consider your investment objectives,",
            "level of experience, and risk appetite.",
            "",
            "NO GUARANTEE OF ACCURACY",
            "While every effort is made to ensure the accuracy of the information",
            "contained in this report, no guarantee is made as to the accuracy,",
            "completeness, or timeliness of the information, text, graphics, or",
            "other items contained herein.",
            "",
            "PAST PERFORMANCE",
            "Past performance is not indicative of future results. The backtesting",
            "results shown are hypothetical and may not reflect actual trading",
            "results. Actual trading results may differ materially from backtesting",
            "results.",
            "",
            f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "SMA 50 Trading Bot v2.0",
        ]

        y = 0.92
        for i, line in enumerate(disclaimer_text):
            if i == 0:
                color = COLORS["white"]
                fontsize = 16
            elif line in ["NOT FINANCIAL ADVICE", "RISK WARNING", "NO GUARANTEE OF ACCURACY",
                         "PAST PERFORMANCE"]:
                color = COLORS["orange"]
                fontsize = 12
            else:
                color = COLORS["text"]
                fontsize = 10
            if line:
                ax.text(0.5, y, line, fontsize=fontsize, color=color,
                       ha="center", va="top", transform=ax.transAxes)
            y -= 0.04

        pdf.savefig(fig, facecolor=COLORS["bg"])
        plt.close(fig)

    def _cleanup_temp_charts(self, chart_dir: str):
        """Clean up temporary chart files."""
        try:
            if os.path.exists(chart_dir):
                for f in os.listdir(chart_dir):
                    if f.endswith('.png'):
                        os.remove(os.path.join(chart_dir, f))
                os.rmdir(chart_dir)
        except:
            pass


# ============================================================================
# SECTION 27: MAIN EXECUTION (COMPLETE WITH ALL MODULES)
# ============================================================================

def main():
    """Main entry point for the SMA 50 Trading Bot - Complete Edition."""
    print("\n" + "=" * 70)
    print("  SMA 50 TRADING BOT v2.0 - COMPLETE EDITION")
    print("  Trend Direction & Dynamic Support/Resistance Analyzer")
    print("  + Multi-Timeframe | Fibonacci | Elliott Wave | Volatility")
    print("  + Backtesting | Alerts | Pivot Points | Data Export")
    print("=" * 70)
    print()

    if len(sys.argv) < 2:
        print("[USAGE] python main.py <path_to_candles.json>")
        print("[EXAMPLE] python main.py ../../candles/candles.json")
        print()
        default_path = os.path.join(os.path.dirname(__file__), '..', '..', 'candles', 'candles.json')
        default_path = os.path.normpath(default_path)
        if os.path.exists(default_path):
            print(f"[INFO] Using default path: {default_path}")
            file_path = default_path
        else:
            print("[ERROR] No candle file specified and default not found")
            sys.exit(1)
    else:
        file_path = sys.argv[1]

    print(f"[INFO] Loading candles from: {file_path}")
    candles = load_candles(file_path)
    validate_candle_sequence(candles)

    print(f"\n[INFO] Analyzing {len(candles)} candles...")
    print(f"[INFO] Date range: {candles[0].timestamp.strftime('%Y-%m-%d')} to "
          f"{candles[-1].timestamp.strftime('%Y-%m-%d')}")
    print(f"[INFO] Price range: {min(c.low for c in candles):.2f} - "
          f"{max(c.high for c in candles):.2f}")
    print()

    print("[PHASE 1/5] Running core signal analysis...")
    generator = SignalGenerator(candles)
    result = generator.generate_signal()

    print("\n[PHASE 2/5] Running enhanced analysis modules...")
    enhanced = EnhancedSignalGenerator(candles)
    enhanced_data = enhanced.run_full_analysis()

    print("\n[PHASE 3/5] Running backtest...")
    backtest = BacktestEngine(candles)
    bt_result = backtest.run_sma50_backtest()

    print("\n[PHASE 4/5] Checking alerts...")
    alerts = AlertSystem.check_alerts(candles, generator.indicators, result)
    alerts_text = AlertSystem.format_alerts(alerts)

    print("\n[PHASE 5/8] Generating text reports...")

    core_report = ReportGenerator.generate_report(result, candles, generator.indicators)
    enhanced_report = EnhancedReportGenerator.generate_enhanced_section(enhanced_data, candles)
    bt_report = backtest.format_backtest_report(bt_result)
    pivot_report = format_pivot_report(candles)

    full_report = core_report + enhanced_report + pivot_report + bt_report + alerts_text

    quick_summary = DataExporter.generate_quick_summary(result)
    print("\n" + "=" * 70)
    print(f"  QUICK SUMMARY: {quick_summary}")
    print("=" * 70)

    print(full_report)

    report_filename = f"sma50_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path = os.path.join(os.path.dirname(__file__), report_filename)
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(full_report)
        print(f"\n[EXPORT] Full report saved to: {report_path}")
    except Exception as e:
        print(f"[WARNING] Could not save report: {e}")

    try:
        json_data = DataExporter.to_json(result, enhanced_data, bt_result)
        json_filename = f"sma50_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        json_path = os.path.join(os.path.dirname(__file__), json_filename)
        DataExporter.save_json(json_data, json_path)
    except Exception as e:
        print(f"[WARNING] Could not save JSON export: {e}")

    print("\n[PHASE 6/8] Generating PNG chart...")
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    chart_gen = BeautifulChartGenerator(candles)
    chart_gen._bt_result = bt_result
    png_path = os.path.join(os.path.dirname(__file__), f"sma50_analysis_{timestamp_str}.png")
    try:
        chart_gen.generate(generator.indicators, result, enhanced_data, png_path)
        print(f"[EXPORT] PNG saved to: {png_path}")
    except Exception as e:
        print(f"[WARNING] Could not generate PNG: {e}")
        import traceback
        traceback.print_exc()
        png_path = ""

    print("\n[PHASE 7/8] Skipping separate reasoning chart (included in main PNG)")

    print("\n[PHASE 8/8] Generating PDF report...")
    pdf_path = os.path.join(os.path.dirname(__file__), f"sma50_report_{timestamp_str}.pdf")
    try:
        pdf_gen = BeautifulPDFGenerator(candles)
        pdf_gen.generate(result, enhanced_data, bt_result, png_path, pdf_path)
        print(f"[EXPORT] PDF saved to: {pdf_path}")
    except Exception as e:
        print(f"[WARNING] Could not generate PDF: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("  EXPORT SUMMARY")
    print("=" * 70)
    print(f"  PNG (all-in-one):  {png_path}")
    print(f"  PDF (all-in-one):  {pdf_path}")
    print(f"  TXT Report:        {report_path}")
    print(f"  JSON Data:         sma50_data_{timestamp_str}.json")
    print("=" * 70)

    print("\n[COMPLETE] All analysis modules executed successfully!")
    print(f"[COMPLETE] Total analysis time: {datetime.now().strftime('%H:%M:%S')}")
    print()

    return result, enhanced_data, bt_result


if __name__ == "__main__":
    main()
