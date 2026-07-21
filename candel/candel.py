import json
import pandas as pd
import mplfinance as mpf


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

    mpf.plot(
        df,
        type="candle",
        style=style,

        volume=True,

        figsize=(16, 9),

        tight_layout=True,

        xrotation=0,

        savefig=dict(
            fname=output_file,
            dpi=300,
            bbox_inches="tight",
        ),
    )

    print(f"Saved: {output_file}")


if __name__ == "__main__":
    export_candles("candles.json")