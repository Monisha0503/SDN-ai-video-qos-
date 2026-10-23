import csv
import time
import random
import os

DATA_FILE = os.path.expanduser("~/sdn_ai_project/data/network_data.csv")

os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

header = [
    "timestamp",
    "bandwidth_mbps",
    "packet_loss_percent",
    "delay_ms",
    "jitter_ms",
    "congestion"
]

file_exists = os.path.exists(DATA_FILE)

# ---------------------------------------------------------------
# WHY THIS CHANGED:
# The old version drew a brand-new random.uniform() value every cycle,
# completely independent of the previous reading. Real network metrics
# don't jump around like that -- they drift. A forecasting model needs
# drift/trend to learn from, otherwise "predict what's coming" is
# meaningless (there's nothing coming, every sample is unrelated noise).
#
# This version uses a random WALK: each new value is the previous value
# plus a small random step, clamped to a realistic range. Occasionally
# (random chance each cycle) it nudges deliberately toward a "congestion
# episode" for a few cycles, then recovers -- so your dataset contains
# genuine rising-trend-before-congestion patterns to learn from, which
# is exactly what a predictive/pre-congestion system needs to see during
# training.
# ---------------------------------------------------------------

state = {
    "bandwidth": 70.0,
    "packet_loss": 1.0,
    "delay": 15.0,
    "jitter": 3.0,
}

# quiet baseline each metric relaxes back toward when there's no episode --
# without this pull-back, a plain random walk just drifts to the clamp
# boundaries over time and gets permanently "stuck" in congestion
BASELINE = {
    "bandwidth": 70.0,
    "packet_loss": 1.0,
    "delay": 15.0,
    "jitter": 3.0,
}
REVERSION_RATE = 0.08  # how strongly it pulls back toward baseline each idle cycle

# how many cycles left in the current "drifting toward congestion" episode
congestion_episode_remaining = 0


def step_metric(current, min_val, max_val, max_step):
    """Random-walk one metric by a small step, clamped to valid range."""
    new_val = current + random.uniform(-max_step, max_step)
    return max(min_val, min(max_val, new_val))


def step_metric_with_reversion(current, baseline, min_val, max_val, max_step):
    """Random step plus a gentle pull back toward baseline (mean reversion),
    so metrics recover to normal between congestion episodes instead of
    drifting permanently toward the clamp boundary."""
    pull = (baseline - current) * REVERSION_RATE
    new_val = current + pull + random.uniform(-max_step, max_step)
    return max(min_val, min(max_val, new_val))


def update_state():
    global congestion_episode_remaining

    # occasionally start a congestion-building episode (trend upward for a few cycles)
    if congestion_episode_remaining == 0 and random.random() < 0.08:
        congestion_episode_remaining = random.randint(4, 8)

    if congestion_episode_remaining > 0:
        # push delay/jitter/loss UP and bandwidth DOWN -- a real pre-congestion signature
        state["bandwidth"] = step_metric(state["bandwidth"] - random.uniform(1, 4), 5, 100, 2)
        state["packet_loss"] = step_metric(state["packet_loss"] + random.uniform(0.2, 1.0), 0, 15, 0.5)
        state["delay"] = step_metric(state["delay"] + random.uniform(2, 6), 1, 150, 3)
        state["jitter"] = step_metric(state["jitter"] + random.uniform(0.5, 2.0), 0, 40, 1)
        congestion_episode_remaining -= 1
    else:
        # normal quiet drift, pulled gently back toward baseline so the
        # system actually recovers after each congestion episode
        state["bandwidth"] = step_metric_with_reversion(state["bandwidth"], BASELINE["bandwidth"], 5, 100, 3)
        state["packet_loss"] = step_metric_with_reversion(state["packet_loss"], BASELINE["packet_loss"], 0, 15, 0.3)
        state["delay"] = step_metric_with_reversion(state["delay"], BASELINE["delay"], 1, 150, 2)
        state["jitter"] = step_metric_with_reversion(state["jitter"], BASELINE["jitter"], 0, 40, 0.8)

    return (
        round(state["bandwidth"], 2),
        round(state["packet_loss"], 2),
        round(state["delay"], 2),
        round(state["jitter"], 2),
    )


with open(DATA_FILE, "a", newline="") as file:
    writer = csv.writer(file)

    if not file_exists:
        writer.writerow(header)

    print("Starting network data collection (trending/windowed simulation)...")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:

            bandwidth, packet_loss, delay, jitter = update_state()

            congestion = 1 if (
                packet_loss > 5 or
                delay > 60 or
                jitter > 15
            ) else 0

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            writer.writerow([
                timestamp,
                bandwidth,
                packet_loss,
                delay,
                jitter,
                congestion
            ])

            file.flush()

            print(
                f"Bandwidth={bandwidth} Mbps | "
                f"Loss={packet_loss}% | "
                f"Delay={delay} ms | "
                f"Jitter={jitter} ms | "
                f"Congestion={congestion}"
            )

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nData collection stopped.")
