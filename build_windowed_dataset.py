"""
build_windowed_dataset.py

Run this AFTER collecting fresh data with the updated data_collector.py
(let it run for at least 15-20 minutes so you get enough congestion
episodes to learn from).

It reads your raw network_data.csv (one row per 2-second poll) and builds
a new windowed_network_data.csv where each row = trend features from the
last 5 readings (10 seconds of history) + a label for whether congestion
happens 3 polls (~6 seconds) in the FUTURE.

This is what turns your model from "classify the current instant" into
"forecast what's about to happen" -- the actual point of your project title.

Usage:
    python3 build_windowed_dataset.py
"""

import pandas as pd
import numpy as np
import os

RAW_FILE = os.path.expanduser("~/sdn_ai_project/data/network_data.csv")
OUT_FILE = os.path.expanduser("~/sdn_ai_project/data/windowed_network_data.csv")

WINDOW_SIZE = 5     # how many past readings to summarize (5 readings * 2s = 10s lookback)
HORIZON = 3         # how many readings ahead to predict (3 readings * 2s = 6s ahead)

METRICS = ["bandwidth_mbps", "packet_loss_percent", "delay_ms", "jitter_ms"]


def extract_window_features(window_df):
    """window_df: WINDOW_SIZE rows, oldest first. Returns a flat feature dict."""
    feats = {}
    t = np.arange(len(window_df), dtype=float)  # 0,1,2,3,4 (evenly spaced by polling interval)

    for m in METRICS:
        values = window_df[m].values.astype(float)
        feats[f"{m}_current"] = values[-1]
        feats[f"{m}_mean"] = values.mean()
        feats[f"{m}_std"] = values.std()
        feats[f"{m}_min"] = values.min()
        feats[f"{m}_max"] = values.max()
        feats[f"{m}_slope"] = np.polyfit(t, values, 1)[0] if len(values) >= 2 else 0.0

    return feats


def main():
    df = pd.read_csv(RAW_FILE)
    n = len(df)
    print(f"Loaded {n} raw samples from {RAW_FILE}")

    if n < WINDOW_SIZE + HORIZON + 10:
        print(
            f"Not enough data yet. You need at least {WINDOW_SIZE + HORIZON + 10} rows; "
            f"you have {n}. Let data_collector.py run longer, then re-run this script."
        )
        return

    rows = []
    # i is the index of the LAST sample in the window (the "current" moment)
    # we need i-WINDOW_SIZE+1 .. i for the window, and i+HORIZON for the future label
    for i in range(WINDOW_SIZE - 1, n - HORIZON):
        window = df.iloc[i - WINDOW_SIZE + 1: i + 1]
        future_row = df.iloc[i + HORIZON]

        feats = extract_window_features(window)
        feats["label_future_congestion"] = int(future_row["congestion"])
        rows.append(feats)

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT_FILE, index=False)

    print(f"\nBuilt windowed dataset: {len(out_df)} samples")
    print(f"Saved to: {OUT_FILE}")
    print(f"\nLabel balance:")
    print(out_df["label_future_congestion"].value_counts())
    print(
        f"\nEach row = trend features from a {WINDOW_SIZE * 2}s window, "
        f"labeled with whether congestion occurs {HORIZON * 2}s later."
    )


if __name__ == "__main__":
    main()
