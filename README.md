# Predictive Pre-Congestion Aware QoS Optimization for Video Streaming using SDN and Lightweight AI

**Course:** CS23502 – Networks and Data Communication
**Type:** Mini Project (Semester-long, 12 weeks)

## Team

| Name | Register No. |
|---|---|
| Sana Tasneem Azimudin | 2024503007 |
| Priyadharshini M | 2024503501 |
| Sharmu R | 2024503055 |
| Monisha G | 2024503043 |

## Problem Statement

Video streaming applications suffer from buffering, quality degradation, and increased latency when network congestion occurs. Traditional QoS mechanisms in Software Defined Networks (SDN) — such as static priority queuing and fixed routing rules — are **reactive**, responding only after congestion is detected. Existing SDN-based QoS solutions for video (e.g., ARVS, MaxStream) largely optimize routing *after* congestion is observed, relying mainly on bandwidth/throughput as the sole metric. There is limited work combining lightweight, real-time predictive models with SDN controllers to anticipate congestion **before** it occurs, specifically for video traffic prioritization.

## Proposed Solution

This project designs a **proactive, prediction-based QoS optimization system** for video streaming over SDN. A lightweight machine learning model continuously monitors network conditions and forecasts congestion **2–5 seconds before it occurs**. The SDN controller (Ryu) then proactively reprioritizes and reroutes video traffic ahead of the congestion event, rather than reacting to it after quality has already degraded.

## Key Features

1. **Proactive, not reactive** — forecasts congestion ahead of time instead of responding after the fact.
2. **Confidence-aware triggering** — rerouting/prioritization is triggered only when prediction confidence exceeds a tuned threshold (e.g., 0.75), avoiding overreaction to noisy predictions.
3. **Multi-model benchmarking** — Random Forest, Gradient Boosting, and LSTM models are trained and compared; the best-performing model is selected based on measured results.
4. **Real-time visualization dashboard** — live network metrics and AI-driven decisions are displayed during demonstration.

## Architecture

See [`docs/architecture-diagram.drawio`](docs/architecture-diagram.drawio) for the full system architecture (Application Plane → SDN Controller/Ryu → Data Plane), including the Confidence Threshold Checker and AI Prediction Module.

## Tools & Technologies

| Category | Tool(s) |
|---|---|
| Network Emulation | Mininet |
| SDN Controller | Ryu (Python-based) |
| Traffic Generation | iPerf3 |
| Packet Inspection | Wireshark |
| AI/ML Development | Python (scikit-learn, TensorFlow/Keras) |
| Visualization | Matplotlib / Plotly |
| Report Writing | Overleaf (IEEE conference format) |

## Project Timeline (12 Weeks)

| Month | Focus |
|---|---|
| Month 1 (Week 1–4) | Literature review, Mininet + Ryu setup, baseline (static QoS) experiments |
| Month 2 (Week 5–8) | Feature engineering, model training/benchmarking, AI–controller integration |
| Month 3 (Week 9–12) | Comparative analysis, dashboard, IEEE report, final presentation |

Full plan: [`docs/12-week-plan.pdf`](docs/12-week-plan.pdf)

## Repository Structure

```
├── README.md
├── docs/
│   ├── 12-week-plan.pdf
│   ├── literature-review.docx
│   └── architecture-diagram.drawio
└── src/
    ├── basic_topology.py          # Week 3 — Mininet + Ryu test topology
    └── week4_baseline_experiment.py  # Week 4 — baseline QoS measurement script
```

## Literature Review

16 papers reviewed covering three research tracks: reactive SDN-QoS routing, RL/GNN-based routing optimization, and congestion/elephant-flow prediction. Full review with problem/method/result/relevance analysis: [`docs/literature-review.docx`](docs/literature-review.docx)

## Status

**Current stage:** First Review (Aug 5, 2026) — Problem statement, research gap, objectives, methodology, architecture diagram, and literature review complete. Testbed setup (Mininet/Ryu) and baseline experiments in progress.

## Links

- **Report (Overleaf):** https://www.overleaf.com/read/pxvpbmhbmbnk#553d2e
- **Project Board / Presentation:** https://docs.google.com/presentation/d/1btQkrH0NQOfDMpvwdyCGi0GJ9AnBnHH1/edit?usp=sharing

## References

See full reference list in [`docs/literature-review.docx`](docs/literature-review.docx).
