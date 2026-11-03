# Predictive Pre-Congestion Aware QoS Optimization for Video Streaming using SDN and Lightweight AI

CS23502 Mini Project, MIT-Chennai (Dept. of Computer Technology)

| Name | Register No. |
|---|---|
| Sana Tasneem Azimudin | 2024503007 |
| Priyadharshini M | 2024503501 |
| Sharmu R | 2024503055 |
| Monisha G | 2024503043 |

## What this project does

A Ryu (OpenFlow 1.3) controller keeps a sliding window of the last 5 QoS samples (10 s) of bandwidth, packet loss, delay and jitter, turns them into 24 trend features, and a Gradient Boosting classifier forecasts whether congestion will occur 3 samples (6 s) later.

## Scope and honesty note (please read)

- The QoS telemetry that drives the model is **simulated** (a random walk with congestion episodes, see `data_collector.py`). It is **not measured** from the Mininet switches.
- Real and verified: the forecasting pipeline, the live controller integration, the confidence gate, and the OpenFlow flow-table change (`s1-eth2` -> `s1-eth3`, checked with `ovs-ofctl`).
- The static-vs-AI comparison is a **single preliminary run**, not evidence of a proven improvement. See the paper and `docs/Final_Implementation_Evidence.docx`.
- Main future work: poll OpenFlow port statistics so the model reacts to real traffic.

## Repository layout

| File | Role |
|---|---|
| `data_collector.py` | Generates simulated trending telemetry every 2 s into `data/network_data.csv` |
| `build_windowed_dataset.py` | Reads `network_data.csv`, writes `data/windowed_network_data.csv` (24 features + label) |
| `train_gradient_boosting_windowed.py` | Trains the model; writes `gradient_boosting_windowed_model.pkl` and `windowed_feature_columns.pkl` |
| `multipath_ai_controller_windowed.py` | Live Ryu controller: window, forecast, 0.90 gate, path install |
| `multipath_static_controller.py` | Baseline: installs the normal path once, never switches |
| `multipath_topology.py` | Mininet topology (h1, h2, s1-s4) |
| `gradient_boosting_windowed_model.pkl`, `windowed_feature_columns.pkl` | Trained model and feature order used by the controller |
| `data/` | Datasets (see `data/README.md`) |
| `docs/` | Evidence document and screenshots |

Earlier-phase files (`multipath_ai_controller.py`, `train_gradient_boosting.py`, `train_random_forest.py`, `train_lstm.py`, `compare_models.py`, `plot_results.py`, `results_summary.csv`, `*.png`, `threshold_*.log`) belong to the first version, which used independent random readings and no sliding window. They are kept for reference.

## How the files connect

```
data_collector.py --> data/network_data.csv
        --> build_windowed_dataset.py --> data/windowed_network_data.csv
        --> train_gradient_boosting_windowed.py --> *.pkl (model + feature order)
        --> multipath_ai_controller_windowed.py (loads both .pkl files)
multipath_topology.py  <-- Mininet connects to whichever controller is running
multipath_static_controller.py  (baseline, no model)
```

## Prerequisites

Ubuntu on WSL2 (or Linux), Python 3.10, Ryu 4.34 in a virtualenv, Mininet, Open vSwitch, iperf3, and the Python packages pandas, numpy, scikit-learn, joblib. See the implementation manual for exact versions.

Note: `multipath_ai_controller_windowed.py` loads the model from `/home/monisha/sdn_ai_project/`. If your path differs, edit the two `joblib.load(...)` lines.

## Run it

All commands are from `~/sdn_ai_project`.

**1. Build the data and model (once)**
```bash
source ~/ryu310_env/bin/activate
python3 data_collector.py          # let it run a few minutes (about 570 samples used), Ctrl+C to stop
python3 build_windowed_dataset.py
python3 train_gradient_boosting_windowed.py   # prints accuracy, saves the .pkl files
```
Expected: about 567 windowed rows and accuracy near 89% (varies with the generated data).

**2. AI-enabled run** (two terminals)
```bash
# Terminal 1
source ~/ryu310_env/bin/activate
ryu-manager multipath_ai_controller_windowed.py
# Terminal 2 (wait for "All 4 switches connected" in terminal 1 after starting Mininet)
sudo mn --custom multipath_topology.py --topo multipath --mac --switch ovsk --controller remote,ip=127.0.0.1,port=6653
```
At the `mininet>` prompt:
```
pingall
h2 iperf3 -s -D
h1 iperf3 -c 10.0.0.2 -t 60 -J > /tmp/ai_result.json
h1 ping -c 30 10.0.0.2
sh ovs-ofctl -O OpenFlow13 dump-flows s1
```
Watch terminal 1: forecasts with confidence, and "PRE-EMPTIVELY SWITCH TO ALTERNATE PATH" when confidence >= 0.90.

**3. Static baseline run:** repeat step 2 with `ryu-manager multipath_static_controller.py` (stop the AI controller and `sudo mn -c` first).

**4. Verify the reroute:** run `sh ovs-ofctl -O OpenFlow13 dump-flows s1` before and after a switch. The output port changes between `s1-eth2` (normal) and `s1-eth3` (alternate).

## Results (summary)

| Item | Value |
|---|---|
| Windowed rows / features | 567 / 24 |
| Test accuracy (random 80/20 split, simulated data) | 89.47% |
| Inference time per forecast | about 3-6 ms |
| Static: iperf3 sender / receiver | 9.89 / 9.57 Mbps, 0 retransmits |
| AI: iperf3 sender / receiver | 12.70 / 12.42 Mbps, 405 retransmits |
| Static / AI ping avg RTT | 0.259 / 0.322 ms (idle path, treat as equal) |

Single run per controller. Throughput differences may come from path capacity or flow rewrites, not only forecasting quality.

## Known limitations

Simulated telemetry; single-run comparison; random (not time-ordered) train/test split on overlapping windows; flows are deleted and reinstalled every 2 s cycle (likely cause of the retransmit bursts).

## Links

- Paper (Overleaf): https://www.overleaf.com/project/6ad7874711984de722d343ea/share#5bae75fcdae6386ec782ca4d44a9268c03b08adc22e59ad4
- Evidence document: `docs/Final_Implementation_Evidence.docx`
