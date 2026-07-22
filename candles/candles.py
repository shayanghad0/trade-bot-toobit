import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplfinance as mpf

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 600,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "figure.facecolor": "#131722",
    "axes.facecolor": "#131722",
    "savefig.facecolor": "#131722",
})


def supertrend(df, length=10, multiplier=1.0):
    high = df["High"].values
    low = df["Low"].values
    close = df["Close"].values
    hl2 = (high + low) / 2.0

    # ATR
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.roll(close, 1)),
            np.abs(low - np.roll(close, 1)),
        ),
    )
    tr[0] = high[0] - low[0]
    atr = pd.Series(tr).ewm(span=length, adjust=False).mean().values

    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    n = len(close)
    final_upper = np.copy(upper)
    final_lower = np.copy(lower)
    direction = np.ones(n, dtype=int)  # 1=up, -1=down

    for i in range(1, n):
        # upper band ratchet
        if upper[i] < final_upper[i - 1] or close[i - 1] > final_upper[i - 1]:
            final_upper[i] = upper[i]
        else:
            final_upper[i] = final_upper[i - 1]

        # lower band ratchet
        if lower[i] > final_lower[i - 1] or close[i - 1] < final_lower[i - 1]:
            final_lower[i] = lower[i]
        else:
            final_lower[i] = final_lower[i - 1]

        # direction flip
        if direction[i - 1] == 1 and close[i] < final_lower[i]:
            direction[i] = -1
        elif direction[i - 1] == -1 and close[i] > final_upper[i]:
            direction[i] = 1
        else:
            direction[i] = direction[i - 1]

    trend = np.where(direction == 1, final_lower, final_upper)
    return pd.Series(trend, index=df.index), pd.Series(direction, index=df.index)


def rsi(close, length=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(span=length, adjust=False).mean()
    avg_loss = loss.ewm(span=length, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def pivots(df, left=5, right=5):
    high = df["High"].values
    low = df["Low"].values
    n = len(high)

    pivot_high = np.full(n, np.nan)
    pivot_low = np.full(n, np.nan)

    for i in range(left, n - right):
        if high[i] == max(high[i - left : i + right + 1]):
            pivot_high[i] = high[i]
        if low[i] == min(low[i - left : i + right + 1]):
            pivot_low[i] = low[i]

    return (
        pd.Series(pivot_high, index=df.index),
        pd.Series(pivot_low, index=df.index),
    )


def smart_money(df, swing_length=5):
    """Detect BOS/CHoCH, Order Blocks, and Fair Value Gaps."""
    o = df["Open"].values
    h = df["High"].values
    l = df["Low"].values
    c = df["Close"].values
    n = len(df)

    # --- Swing structure ---
    ph, pl = pivots(df, left=swing_length, right=swing_length)
    ph_vals = ph.values
    pl_vals = pl.values

    # BOS/CHoCH detection
    bos_bull = np.zeros(n, dtype=bool)
    bos_bear = np.zeros(n, dtype=bool)
    choch_bull = np.zeros(n, dtype=bool)
    choch_bear = np.zeros(n, dtype=bool)
    last_swing_high = np.full(n, np.nan)
    last_swing_low = np.full(n, np.nan)
    swing_high_idx = np.full(n, -1, dtype=int)
    swing_low_idx = np.full(n, -1, dtype=int)
    trend = np.zeros(n, dtype=int)

    current_sh = np.nan
    current_sl = np.nan
    current_sh_idx = -1
    current_sl_idx = -1
    current_trend = 0

    for i in range(1, n):
        if not np.isnan(ph_vals[i]):
            current_sh = ph_vals[i]
            current_sh_idx = i
        if not np.isnan(pl_vals[i]):
            current_sl = pl_vals[i]
            current_sl_idx = i

        last_swing_high[i] = current_sh
        last_swing_low[i] = current_sl
        swing_high_idx[i] = current_sh_idx
        swing_low_idx[i] = current_sl_idx

        if not np.isnan(current_sh) and c[i] > current_sh and c[i - 1] <= current_sh:
            if current_trend == -1:
                choch_bull[i] = True
            else:
                bos_bull[i] = True
            current_trend = 1

        if not np.isnan(current_sl) and c[i] < current_sl and c[i - 1] >= current_sl:
            if current_trend == 1:
                choch_bear[i] = True
            else:
                bos_bear[i] = True
            current_trend = -1

        trend[i] = current_trend

    # --- Order Blocks ---
    bull_ob = np.full(n, np.nan)
    bull_ob_low = np.full(n, np.nan)
    bear_ob = np.full(n, np.nan)
    bear_ob_low = np.full(n, np.nan)

    for i in range(1, n):
        if bos_bull[i] or choch_bull[i]:
            for j in range(i - 1, max(i - 6, -1), -1):
                if c[j] < o[j]:
                    bull_ob[i] = h[j]
                    bull_ob_low[i] = l[j]
                    break
        if bos_bear[i] or choch_bear[i]:
            for j in range(i - 1, max(i - 6, -1), -1):
                if c[j] > o[j]:
                    bear_ob[i] = h[j]
                    bear_ob_low[i] = l[j]
                    break

    # --- Fair Value Gaps ---
    fvg_bull_top = np.full(n, np.nan)
    fvg_bull_bot = np.full(n, np.nan)
    fvg_bear_top = np.full(n, np.nan)
    fvg_bear_bot = np.full(n, np.nan)

    for i in range(2, n):
        if l[i] > h[i - 2]:
            fvg_bull_top[i] = l[i]
            fvg_bull_bot[i] = h[i - 2]
        if h[i] < l[i - 2]:
            fvg_bear_top[i] = l[i - 2]
            fvg_bear_bot[i] = h[i]

    return {
        "bos_bull": bos_bull, "bos_bear": bos_bear,
        "choch_bull": choch_bull, "choch_bear": choch_bear,
        "bull_ob": bull_ob, "bull_ob_low": bull_ob_low,
        "bear_ob": bear_ob, "bear_ob_low": bear_ob_low,
        "fvg_bull_top": fvg_bull_top, "fvg_bull_bot": fvg_bull_bot,
        "fvg_bear_top": fvg_bear_top, "fvg_bear_bot": fvg_bear_bot,
        "last_swing_high": last_swing_high, "last_swing_low": last_swing_low,
        "swing_high_idx": swing_high_idx, "swing_low_idx": swing_low_idx,
    }


def export_candles(json_file, output_file="chart.png"):
    # Read JSON
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        raise ValueError("JSON file is empty.")

    # Create DataFrame
    df = pd.DataFrame(data)

    # Rename columns
    df.rename(columns={
        "open_time": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }, inplace=True)

    # Convert timestamp
    df["Date"] = pd.to_datetime(df["Date"], unit="ms")

    # Convert numeric columns
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col])

    # Keep only required columns
    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]

    # Set datetime index
    df.set_index("Date", inplace=True)

    # ---------------- Market Colors ---------------- #

    mc = mpf.make_marketcolors(
        up="white",
        down="#808080",

        edge={
            "up": "white",
            "down": "#808080",
        },

        wick={
            "up": "white",
            "down": "#808080",
        },

        volume={
            "up": "white",
            "down": "#808080",
        },
    )

    style = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mc,

        facecolor="#131722",
        figcolor="#131722",

        gridstyle="-",
        gridcolor="#2A2E39",

        y_on_right=True,

        rc={
            "axes.labelcolor": "white",
            "axes.edgecolor": "#555555",
            "xtick.color": "white",
            "ytick.color": "white",
            "figure.facecolor": "#131722",
            "savefig.facecolor": "#131722",
        },
    )

    # ---------------- SuperTrend 1 ---------------- #
    st1, dir1 = supertrend(df, length=10, multiplier=1.0)

    # SuperTrend 2
    st2, dir2 = supertrend(df, length=10, multiplier=2.0)

    # SuperTrend 3
    st3, dir3 = supertrend(df, length=10, multiplier=3.0)

    def split_segments(values, directions):
        """Split into up/down series, keeping one extra bar at each flip to avoid gaps."""
        n = len(values)
        up = values.copy().astype(float)
        dn = values.copy().astype(float)

        # At each direction flip, keep the previous bar's value in the new direction
        # so the two segments connect visually
        for i in range(1, n):
            if directions[i] != directions[i - 1]:
                # Keep this bar in BOTH old and new direction segments
                pass  # already in both since we only mask non-matching

        # Now mask: up series keeps bars where dir==1, dn keeps dir==-1
        # But at flip points, keep one extra bar from the opposite direction
        up_mask = directions == 1
        dn_mask = directions == -1

        # Extend each segment by one bar at flip boundaries
        for i in range(1, n):
            if directions[i] != directions[i - 1]:
                if directions[i] == 1:
                    # Flip to up: keep previous bar (which was down) in up series too
                    up_mask[i - 1] = True
                else:
                    # Flip to down: keep previous bar (which was up) in dn series too
                    dn_mask[i - 1] = True

        up[~up_mask] = np.nan
        dn[~dn_mask] = np.nan
        return up, dn

    st1_up, st1_dn = split_segments(st1.values, dir1.values)
    st1_up = pd.Series(st1_up, index=df.index)
    st1_dn = pd.Series(st1_dn, index=df.index)

    st2_up, st2_dn = split_segments(st2.values, dir2.values)
    st2_up = pd.Series(st2_up, index=df.index)
    st2_dn = pd.Series(st2_dn, index=df.index)

    st3_up, st3_dn = split_segments(st3.values, dir3.values)
    st3_up = pd.Series(st3_up, index=df.index)
    st3_dn = pd.Series(st3_dn, index=df.index)

    # ---------------- RSI ---------------- #
    rsi_val = rsi(df["Close"], length=14)
    price_min = df["Low"].min()
    price_max = df["High"].max()
    rsi_scaled = (rsi_val / 100) * (price_max - price_min) + price_min

    # ---------------- Pivots ---------------- #
    ph, pl = pivots(df, left=5, right=5)

    ph_line = ph.copy().ffill()
    pl_line = pl.copy().ffill()

    # ---------------- Smart Money ---------------- #
    sm = smart_money(df, swing_length=5)

    ap = [
        mpf.make_addplot(st1_up, color="green", width=2),
        mpf.make_addplot(st1_dn, color="red",   width=2),
        mpf.make_addplot(st2_up, color="green", width=2),
        mpf.make_addplot(st2_dn, color="red",   width=2),
        mpf.make_addplot(st3_up, color="green", width=2),
        mpf.make_addplot(st3_dn, color="red",   width=2),
        mpf.make_addplot(rsi_scaled, color="blue", width=1.5),
        mpf.make_addplot(ph_line, color="aqua", width=2.5),
        mpf.make_addplot(pl_line, color="aqua", width=2.5),
        mpf.make_addplot(ph, type="scatter", marker="v", markersize=80, color="red"),
        mpf.make_addplot(pl, type="scatter", marker="^", markersize=80, color="green"),
    ]

    d1 = dir1.iloc[-1]
    d2 = dir2.iloc[-1]
    d3 = dir3.iloc[-1]

    fig, axes = mpf.plot(
        df,
        type="candle",
        style=style,
        volume=True,
        addplot=ap,
        figsize=(22, 16),
        panel_ratios=(5, 1),
        tight_layout=True,
        xrotation=0,
        returnfig=True,
    )

    fig.patch.set_facecolor("#131722")
    axes[0].set_facecolor("#131722")

    ax = axes[0]

    # ---- Draw Structure Lines (BOS/CHoCH) ---- #
    for i in range(len(df)):
        # Bullish BOS line from swing low to breakout
        if sm["bos_bull"][i] or sm["choch_bull"][i]:
            start_idx = sm["swing_low_idx"][i]
            level = sm["last_swing_low"][i]
            if start_idx >= 0:
                color = "#2157f3" if sm["bos_bull"][i] else "#00ff68"
                style = "-" if sm["bos_bull"][i] else "--"
                ax.plot([start_idx, i], [level, level], color=color, linewidth=1.5, linestyle=style, alpha=0.9)

        # Bearish BOS line from swing high to breakout
        if sm["bos_bear"][i] or sm["choch_bear"][i]:
            start_idx = sm["swing_high_idx"][i]
            level = sm["last_swing_high"][i]
            if start_idx >= 0:
                color = "#F23645" if sm["bos_bear"][i] else "#ff6600"
                style = "-" if sm["bos_bear"][i] else "--"
                ax.plot([start_idx, i], [level, level], color=color, linewidth=1.5, linestyle=style, alpha=0.9)

    # ---- Draw BOS/CHoCH Labels ---- #
    for i in range(len(df)):
        if sm["bos_bull"][i]:
            ax.text(i, df["Low"].iloc[i] * 0.998, " BOS ", fontsize=8, color="white", fontweight="bold",
                    ha="center", va="top",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#2157f3", edgecolor="none", alpha=0.9))
        if sm["bos_bear"][i]:
            ax.text(i, df["High"].iloc[i] * 1.002, " BOS ", fontsize=8, color="white", fontweight="bold",
                    ha="center", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#F23645", edgecolor="none", alpha=0.9))
        if sm["choch_bull"][i]:
            ax.text(i, df["Low"].iloc[i] * 0.998, " CHoCH ", fontsize=8, color="white", fontweight="bold",
                    ha="center", va="top",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#00ff68", edgecolor="none", alpha=0.9))
        if sm["choch_bear"][i]:
            ax.text(i, df["High"].iloc[i] * 1.002, " CHoCH ", fontsize=8, color="white", fontweight="bold",
                    ha="center", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#ff6600", edgecolor="none", alpha=0.9))

    # ---- Draw Order Blocks (extend until mitigated) ---- #
    ob_drawn_bull = []
    ob_drawn_bear = []

    for i in range(len(df)):
        if not np.isnan(sm["bull_ob"][i]):
            ob_drawn_bull.append((i, sm["bull_ob"][i], sm["bull_ob_low"][i]))
        if not np.isnan(sm["bear_ob"][i]):
            ob_drawn_bear.append((i, sm["bear_ob"][i], sm["bear_ob_low"][i]))

    h = df["High"].values
    l = df["Low"].values

    # Bullish OBs — extend until price dips below OB low (mitigated)
    for start_i, top, bot in ob_drawn_bull:
        end_i = len(df)
        for j in range(start_i + 1, len(df)):
            if l[j] < bot:
                end_i = j
                break
        width = end_i - start_i
        if width > 0:
            rect = plt.Rectangle((start_i - 0.5, bot), width, top - bot,
                                 facecolor="#2157f3", alpha=0.12, edgecolor="#2157f3",
                                 linewidth=0.8, linestyle="--")
            ax.add_patch(rect)

    # Bearish OBs — extend until price rises above OB top (mitigated)
    for start_i, top, bot in ob_drawn_bear:
        end_i = len(df)
        for j in range(start_i + 1, len(df)):
            if h[j] > top:
                end_i = j
                break
        width = end_i - start_i
        if width > 0:
            rect = plt.Rectangle((start_i - 0.5, bot), width, top - bot,
                                 facecolor="#F23645", alpha=0.12, edgecolor="#F23645",
                                 linewidth=0.8, linestyle="--")
            ax.add_patch(rect)

    # ---- Draw Fair Value Gaps (extend until filled) ---- #
    for i in range(len(df)):
        if not np.isnan(sm["fvg_bull_top"][i]):
            top = sm["fvg_bull_top"][i]
            bot = sm["fvg_bull_bot"][i]
            end_i = len(df)
            for j in range(i + 1, len(df)):
                if l[j] <= bot:
                    end_i = j
                    break
            width = end_i - i
            if width > 0:
                rect = plt.Rectangle((i - 0.5, bot), width, top - bot,
                                     facecolor="#00ff68", alpha=0.12, edgecolor="#00ff68",
                                     linewidth=0.8, linestyle="--")
                ax.add_patch(rect)
        if not np.isnan(sm["fvg_bear_top"][i]):
            top = sm["fvg_bear_top"][i]
            bot = sm["fvg_bear_bot"][i]
            end_i = len(df)
            for j in range(i + 1, len(df)):
                if h[j] >= top:
                    end_i = j
                    break
            width = end_i - i
            if width > 0:
                rect = plt.Rectangle((i - 0.5, bot), width, top - bot,
                                     facecolor="#ff0008", alpha=0.12, edgecolor="#ff0008",
                                     linewidth=0.8, linestyle="--")
                ax.add_patch(rect)
    box_props = dict(boxstyle="round,pad=0.5", facecolor="#1a1a2e", edgecolor="#444444", alpha=0.92)

    # ---- SuperTrend Table ---- #
    lines = [
        ("ST 1", d1),
        ("ST 2", d2),
        ("ST 3", d3),
    ]

    table_text = ""
    for label, direction in lines:
        arrow = "▲" if direction == 1 else "▼"
        status = "Up" if direction == 1 else "Down"
        table_text += f"{label} : {arrow} {status}\n"

    ax.text(
        0.01, 0.98, table_text.strip(),
        transform=ax.transAxes,
        fontsize=10,
        fontfamily="monospace",
        fontweight="bold",
        verticalalignment="top",
        horizontalalignment="left",
        bbox=box_props,
        color="white",
    )

    # ---- Legend (bottom-right) ---- #
    legend_text = (
        "━━━ Legend ━━━━━━━━━━━━━━━━━\n"
        "─── SuperTrend (Green/Red)\n"
        "─── RSI (Blue)\n"
        "━━━ Pivot (Aqua)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "[BOS]     Break of Structure\n"
        "[CHoCH]   Change of Character\n"
        "▓▓▓ Bullish OB (Blue)\n"
        "▓▓▓ Bearish OB (Red)\n"
        "▓▓▓ Bullish FVG (Green)\n"
        "▓▓▓ Bearish FVG (Red)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    ax.text(
        0.99, 0.02, legend_text,
        transform=ax.transAxes,
        fontsize=8,
        fontfamily="monospace",
        verticalalignment="bottom",
        horizontalalignment="right",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1a2e", edgecolor="#444444", alpha=0.92),
        color="white",
        linespacing=1.4,
    )

    # ---- Title ---- #
    fig.suptitle("Smart Money Concepts  •  Triple SuperTrend  •  RSI",
                 fontsize=14, fontweight="bold", color="white", y=0.98)

    fig.savefig(
        output_file,
        dpi=600,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        pad_inches=0.25,
        pil_kwargs={"antialias": "best"},
    )
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    export_candles("candles.json")