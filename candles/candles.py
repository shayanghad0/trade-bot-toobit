import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import mplfinance as mpf

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 600,
    "font.size": 10,
    "font.family": "sans-serif",
    "figure.facecolor": "#0d1117",
    "axes.facecolor": "#0d1117",
    "savefig.facecolor": "#0d1117",
})

BG = "#0d1117"
BG2 = "#161b22"
GRID = "#21262d"
TEXT = "#c9d1d9"
GREEN = "#3fb950"
RED = "#f85149"
BLUE = "#58a6ff"
ORANGE = "#d29922"
PURPLE = "#bc8cff"
TEAL = "#39d353"
CYAN = "#00d4aa"


def supertrend(df, length=10, multiplier=1.0):
    high, low, close = df["High"].values, df["Low"].values, df["Close"].values
    hl2 = (high + low) / 2.0
    tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]
    atr = pd.Series(tr).ewm(span=length, adjust=False).mean().values

    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr
    n = len(close)
    fu, fl = np.copy(upper), np.copy(lower)
    d = np.ones(n, dtype=int)

    for i in range(1, n):
        fu[i] = upper[i] if upper[i] < fu[i-1] or close[i-1] > fu[i-1] else fu[i-1]
        fl[i] = lower[i] if lower[i] > fl[i-1] or close[i-1] < fl[i-1] else fl[i-1]
        if d[i-1] == 1 and close[i] < fl[i]: d[i] = -1
        elif d[i-1] == -1 and close[i] > fu[i]: d[i] = 1
        else: d[i] = d[i-1]

    trend = np.where(d == 1, fl, fu)
    return pd.Series(trend, index=df.index), pd.Series(d, index=df.index)


def rsi(close, length=14):
    delta = close.diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_g = gain.ewm(span=length, adjust=False).mean()
    avg_l = loss.ewm(span=length, adjust=False).mean()
    return 100 - (100 / (1 + avg_g / avg_l))


def macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def pivots(df, left=5, right=5):
    h, l = df["High"].values, df["Low"].values
    n = len(h)
    ph, pl = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(left, n - right):
        if h[i] == max(h[i-left:i+right+1]): ph[i] = h[i]
        if l[i] == min(l[i-left:i+right+1]): pl[i] = l[i]
    return pd.Series(ph, index=df.index), pd.Series(pl, index=df.index)


def smart_money(df, swing_length=5):
    o, h, l, c = df["Open"].values, df["High"].values, df["Low"].values, df["Close"].values
    n = len(df)
    ph, pl = pivots(df, swing_length, swing_length)
    phv, plv = ph.values, pl.values

    bos_bull = np.zeros(n, dtype=bool)
    bos_bear = np.zeros(n, dtype=bool)
    choch_bull = np.zeros(n, dtype=bool)
    choch_bear = np.zeros(n, dtype=bool)
    lsh = np.full(n, np.nan)
    lsl = np.full(n, np.nan)
    shi = np.full(n, -1, dtype=int)
    sli = np.full(n, -1, dtype=int)
    trend = np.zeros(n, dtype=int)

    csh, csl = np.nan, np.nan
    cshi, csli = -1, -1
    ct = 0

    for i in range(1, n):
        if not np.isnan(phv[i]): csh, cshi = phv[i], i
        if not np.isnan(plv[i]): csl, csli = plv[i], i
        lsh[i], lsl[i] = csh, csl
        shi[i], sli[i] = cshi, csli

        if not np.isnan(csh) and c[i] > csh and c[i-1] <= csh:
            (choch_bull if ct == -1 else bos_bull)[i] = True
            ct = 1
        if not np.isnan(csl) and c[i] < csl and c[i-1] >= csl:
            (choch_bear if ct == 1 else bos_bear)[i] = True
            ct = -1
        trend[i] = ct

    bob, bol = np.full(n, np.nan), np.full(n, np.nan)
    beb, bel = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(1, n):
        if bos_bull[i] or choch_bull[i]:
            for j in range(i-1, max(i-6, -1), -1):
                if c[j] < o[j]: bob[i], bol[i] = h[j], l[j]; break
        if bos_bear[i] or choch_bear[i]:
            for j in range(i-1, max(i-6, -1), -1):
                if c[j] > o[j]: beb[i], bel[i] = h[j], l[j]; break

    fbt, fbb = np.full(n, np.nan), np.full(n, np.nan)
    fvet, fveb = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(2, n):
        if l[i] > h[i-2]: fbt[i], fbb[i] = l[i], h[i-2]
        if h[i] < l[i-2]: fvet[i], fveb[i] = l[i-2], h[i]

    return {"bos_bull": bos_bull, "bos_bear": bos_bear, "choch_bull": choch_bull, "choch_bear": choch_bear,
            "bob": bob, "bol": bol, "beb": beb, "bel": bel,
            "fbt": fbt, "fbb": fbb, "fvet": fvet, "fveb": fveb,
            "lsh": lsh, "lsl": lsl, "shi": shi, "sli": sli}


def export_candles(json_file, output_file="chart.png"):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data: raise ValueError("JSON file is empty.")

    df = pd.DataFrame(data)
    df.rename(columns={"open_time": "Date", "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}, inplace=True)
    df["Date"] = pd.to_datetime(df["Date"], unit="ms")
    for col in ["Open", "High", "Low", "Close", "Volume"]: df[col] = pd.to_numeric(df[col])
    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]
    df.set_index("Date", inplace=True)

    mc = mpf.make_marketcolors(up=GREEN, down=RED, edge={"up": GREEN, "down": RED}, wick={"up": GREEN, "down": RED}, volume={"up": GREEN, "down": RED})
    style = mpf.make_mpf_style(base_mpf_style="nightclouds", marketcolors=mc, facecolor=BG, figcolor=BG, gridstyle="-", gridcolor=GRID, y_on_right=True,
        rc={"axes.labelcolor": TEXT, "axes.edgecolor": GRID, "xtick.color": TEXT, "ytick.color": TEXT, "figure.facecolor": BG, "savefig.facecolor": BG})

    st1, d1 = supertrend(df, 10, 1.0)
    st2, d2 = supertrend(df, 10, 2.0)
    st3, d3 = supertrend(df, 10, 3.0)
    rv = rsi(df["Close"], 14)
    macd_line, macd_signal, macd_hist = macd(df["Close"])
    ph, pl = pivots(df, 5, 5)
    sm = smart_money(df, 5)

    pmn, pmx = df["Low"].min(), df["High"].max()
    rs = ((rv - 30) / (70 - 30)) * (pmx - pmn) + pmn
    rs = rs.clip(pmn, pmx)
    pln, pll = ph.ffill(), pl.ffill()

    def split(v, d):
        n = len(v)
        um, dm = d == 1, d == -1
        for i in range(1, n):
            if d[i] != d[i-1]: (um if d[i] == 1 else dm)[i-1] = True
        u, dd = v.copy().astype(float), v.copy().astype(float)
        u[~um] = np.nan; dd[~dm] = np.nan
        return u, dd

    s1u, s1d = [pd.Series(x, index=df.index) for x in split(st1.values, d1.values)]
    s2u, s2d = [pd.Series(x, index=df.index) for x in split(st2.values, d2.values)]
    s3u, s3d = [pd.Series(x, index=df.index) for x in split(st3.values, d3.values)]

    rsi_70 = pd.Series([70] * len(df), index=df.index)
    rsi_30 = pd.Series([30] * len(df), index=df.index)

    raw_ap = [
        (s1u, dict(color=GREEN, width=2.5)),
        (s1d, dict(color=RED, width=2.5)),
        (s2u, dict(color=GREEN, width=1.5, linestyle="--")),
        (s2d, dict(color=RED, width=1.5, linestyle="--")),
        (s3u, dict(color=GREEN, width=1, linestyle=":")),
        (s3d, dict(color=RED, width=1, linestyle=":")),
        (pln, dict(color=BLUE, width=1.8, linestyle="--")),
        (pll, dict(color=ORANGE, width=1.8, linestyle="--")),
        (ph, dict(type="scatter", marker="v", markersize=50, color=RED)),
        (pl, dict(type="scatter", marker="^", markersize=50, color=GREEN)),
        (rv, dict(color=PURPLE, width=1.8, panel=2, ylabel="RSI")),
        (rsi_70, dict(color="#555555", width=0.8, linestyle="--", panel=2)),
        (rsi_30, dict(color="#555555", width=0.8, linestyle="--", panel=2)),
        (macd_hist, dict(type="bar", color=[GREEN if v >= 0 else RED for v in macd_hist], panel=3, ylabel="MACD", width=0.7)),
        (macd_line, dict(color=BLUE, width=1.2, panel=3)),
        (macd_signal, dict(color=ORANGE, width=1.2, panel=3)),
    ]
    ap = [mpf.make_addplot(d, **kw) for d, kw in raw_ap if not (isinstance(d, pd.Series) and d.isna().all()) and not (isinstance(d, np.ndarray) and np.all(np.isnan(d)))]

    dd1, dd2, dd3 = d1.iloc[-1], d2.iloc[-1], d3.iloc[-1]

    fig, axes = mpf.plot(df, type="candle", style=style, volume=True, addplot=ap, figsize=(26, 22), panel_ratios=(5, 1.2, 1.5, 1.5), tight_layout=True, xrotation=0, returnfig=True)
    for a in axes: a.set_facecolor(BG)
    ax = axes[0]

    # Structure lines
    for i in range(len(df)):
        if sm["bos_bull"][i] or sm["choch_bull"][i]:
            si, lv = sm["sli"][i], sm["lsl"][i]
            if si >= 0: ax.plot([si, i], [lv, lv], color=GREEN, linewidth=1.5, alpha=0.7)
        if sm["bos_bear"][i] or sm["choch_bear"][i]:
            si, lv = sm["shi"][i], sm["lsh"][i]
            if si >= 0: ax.plot([si, i], [lv, lv], color=RED, linewidth=1.5, alpha=0.7)

    # BOS/CHoCH labels
    for i in range(len(df)):
        if sm["bos_bull"][i]:
            ax.text(i, df["Low"].iloc[i] * 0.996, "BOS", fontsize=7, color="white", ha="center", va="top", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.15", facecolor=BLUE, edgecolor="none", alpha=0.95))
        if sm["bos_bear"][i]:
            ax.text(i, df["High"].iloc[i] * 1.004, "BOS", fontsize=7, color="white", ha="center", va="bottom", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.15", facecolor=RED, edgecolor="none", alpha=0.95))
        if sm["choch_bull"][i]:
            ax.text(i, df["Low"].iloc[i] * 0.996, "CHoCH", fontsize=7, color="white", ha="center", va="top", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.15", facecolor=TEAL, edgecolor="none", alpha=0.95))
        if sm["choch_bear"][i]:
            ax.text(i, df["High"].iloc[i] * 1.004, "CHoCH", fontsize=7, color="white", ha="center", va="bottom", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.15", facecolor=ORANGE, edgecolor="none", alpha=0.95))

    hv, lv = df["High"].values, df["Low"].values

    # Order Blocks
    for i in range(len(df)):
        if not np.isnan(sm["bob"][i]):
            t, b = sm["bob"][i], sm["bol"][i]
            e = next((j for j in range(i+1, len(df)) if lv[j] < b), len(df))
            ax.add_patch(plt.Rectangle((i-0.5, b), e-i, t-b, facecolor=BLUE, alpha=0.1, edgecolor=BLUE, linewidth=0.5))
        if not np.isnan(sm["beb"][i]):
            t, b = sm["beb"][i], sm["bel"][i]
            e = next((j for j in range(i+1, len(df)) if hv[j] > t), len(df))
            ax.add_patch(plt.Rectangle((i-0.5, b), e-i, t-b, facecolor=RED, alpha=0.1, edgecolor=RED, linewidth=0.5))

    # FVG
    for i in range(len(df)):
        if not np.isnan(sm["fbt"][i]):
            t, b = sm["fbt"][i], sm["fbb"][i]
            e = next((j for j in range(i+1, len(df)) if lv[j] <= b), len(df))
            ax.add_patch(plt.Rectangle((i-0.5, b), e-i, t-b, facecolor=CYAN, alpha=0.1, edgecolor=CYAN, linewidth=0.5))
        if not np.isnan(sm["fvet"][i]):
            t, b = sm["fvet"][i], sm["fveb"][i]
            e = next((j for j in range(i+1, len(df)) if hv[j] >= t), len(df))
            ax.add_patch(plt.Rectangle((i-0.5, b), e-i, t-b, facecolor="#f8514980", alpha=0.1, edgecolor=RED, linewidth=0.5))

    # Title
    fig.text(0.5, 0.97, "SMART MONEY CONCEPTS  ·  TRIPLE SUPERTREND  ·  RSI  ·  MACD", fontsize=14, fontweight="bold", color=TEXT, ha="center")

    # Info panels
    def panel_box(ax, x, y, lines, title=None):
        txt = "\n".join(lines)
        if title:
            txt = f"{'━' * 28}\n  {title}\n{'━' * 28}\n" + txt
        ax.text(x, y, txt, transform=ax.transAxes, fontsize=9, fontfamily="monospace", va="top", ha="left" if x < 0.5 else "right",
                color=TEXT, linespacing=1.3, bbox=dict(boxstyle="round,pad=0.6", fc=BG2, ec="#30363d", alpha=0.95))

    # ST table
    st_lines = []
    for lbl, dd in [("ST 1", dd1), ("ST 2", dd2), ("ST 3", dd3)]:
        arr = "▲" if dd == 1 else "▼"
        clr = GREEN if dd == 1 else RED
        st_lines.append(f"  {lbl}  {arr}  {'BULL' if dd == 1 else 'BEAR'}")
    panel_box(ax, 0.01, 0.98, st_lines, "SUPERTREND")



    # RSI panel info
    rsi_now = rv.iloc[-1]
    rsi_clr = RED if rsi_now > 70 else GREEN if rsi_now < 30 else ORANGE
    rsi_lbl = "OVERBOUGHT" if rsi_now > 70 else "OVERSOLD" if rsi_now < 30 else "NEUTRAL"
    axes[2].text(0.01, 0.92, f"  RSI(14): {rsi_now:.1f}  {rsi_lbl}", transform=axes[2].transAxes, fontsize=10, fontfamily="monospace",
                 va="top", color=rsi_clr, fontweight="bold")
    axes[2].set_ylabel("RSI", color=TEXT, fontsize=10)

    # MACD panel info
    macd_now = macd_line.iloc[-1]
    signal_now = macd_signal.iloc[-1]
    hist_now = macd_hist.iloc[-1]
    macd_clr = GREEN if macd_now > signal_now else RED
    macd_lbl = "BULLISH" if macd_now > signal_now else "BEARISH"
    cross_lbl = ""
    if len(macd_hist) > 1:
        prev_hist = macd_hist.iloc[-2]
        if hist_now > 0 and prev_hist <= 0:
            cross_lbl = "  [CROSSUP]"
        elif hist_now < 0 and prev_hist >= 0:
            cross_lbl = "  [CROSSDN]"
    axes[3].text(0.01, 0.92, f"  MACD(12,26,9): {macd_now:.4f}  {macd_lbl}{cross_lbl}", transform=axes[3].transAxes, fontsize=10, fontfamily="monospace",
                 va="top", color=macd_clr, fontweight="bold")
    axes[3].axhline(y=0, color="#555555", linewidth=0.8, linestyle="--")
    axes[3].set_ylabel("MACD", color=TEXT, fontsize=10)

    fig.savefig(output_file, dpi=600, bbox_inches="tight", facecolor=BG, pad_inches=0.3, pil_kwargs={"antialias": "best"})
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    export_candles("candles.json")
