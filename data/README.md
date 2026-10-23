# Data associated with the project

All datasets are CSV files with a header row.

## network_data.csv (raw simulated telemetry)
574 samples, one every 2 s, produced by `data_collector.py`.

| Column | Meaning |
|---|---|
| timestamp | Sample time (YYYY-MM-DD HH:MM:SS) |
| bandwidth_mbps | Simulated available bandwidth (clamped 5-100) |
| packet_loss_percent | Simulated packet loss (clamped 0-15) |
| delay_ms | Simulated delay (clamped 1-150) |
| jitter_ms | Simulated jitter (clamped 0-40) |
| congestion | 1 if loss > 5% or delay > 60 ms or jitter > 15 ms, else 0 |

The values are a random walk with congestion episodes and mean reversion. They are simulated, not measured from the network.

## windowed_network_data.csv (training data)
567 rows x 25 columns, produced by `build_windowed_dataset.py` (window 5 samples, horizon 3 samples).

- 24 feature columns: for each of bandwidth_mbps, packet_loss_percent, delay_ms, jitter_ms the suffixes `_current`, `_mean`, `_std`, `_min`, `_max`, `_slope`.
- `label_future_congestion`: 1 if congestion occurs 3 samples (6 s) after the window's last sample. Class balance: 292 congested, 275 normal.

## network_data_OLD_backup.csv (legacy)
Dataset from the first version, which used independent random readings (no trend). Not used by the final model. Kept for reference.

## results_summary.csv, latency_summary.csv
Summary tables from the first-version model comparison and latency experiments.
