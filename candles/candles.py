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

    # Carry forward last pivot high/low to draw horizontal lines
    ph_line = ph.copy()
    pl_line = pl.copy()
    ph_line = ph_line.ffill()
    pl_line = pl_line.ffill()

    ap = [
        mpf.make_addplot(st1_up, color="green", width=2),
        mpf.make_addplot(st1_dn, color="red",   width=2),
        mpf.make_addplot(st2_up, color="green", width=2),
        mpf.make_addplot(st2_dn, color="red",   width=2),
        mpf.make_addplot(st3_up, color="green", width=2),
        mpf.make_addplot(st3_dn, color="red",   width=2),
        mpf.make_addplot(rsi_scaled, color="blue", width=1.5),
        mpf.make_addplot(ph_line, color="aqua",   width=2.5),
        mpf.make_addplot(pl_line, color="aqua", width=2.5),
        mpf.make_addplot(ph, type="scatter", marker="v", markersize=80, color="red"),
        mpf.make_addplot(pl, type="scatter", marker="^", markersize=80, color="green"),
    ]

    # Get last direction for each SuperTrend
    d1 = dir1.iloc[-1]
    d2 = dir2.iloc[-1]
    d3 = dir3.iloc[-1]

    fig, axes = mpf.plot(
        df,
        type="candle",
        style=style,

        volume=True,

        addplot=ap,

        figsize=(20, 16),

        panel_ratios=(4, 1),

        tight_layout=True,

        xrotation=0,

        returnfig=True,
    )

    # ---- Info Table (top-right) ---- #
    ax = axes[0]
    box_props = dict(boxstyle="round,pad=0.4", facecolor="#1a1a2e", edgecolor="#555555", alpha=0.9)

    lines = [
        ("ST 1", d1),
        ("ST 2", d2),
        ("ST 3", d3),
    ]

    table_text = ""
    for label, direction in lines:
        arrow = "▲" if direction == 1 else "▼"
        status = "Up" if direction == 1 else "Down"
        color = "green" if direction == 1 else "red"
        table_text += f"{label} : {arrow} {status}\n"

    ax.text(
        0.02, 0.98, table_text.strip(),
        transform=ax.transAxes,
        fontsize=11,
        fontfamily="monospace",
        fontweight="bold",
        verticalalignment="top",
        horizontalalignment="left",
        bbox=box_props,
        color="white",
    )

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