from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub

import joblib
import pandas as pd
import numpy as np
import random
import time
from collections import deque


# ---------------------------------------------------------------
# Windowed feature extraction (same logic as windowed_features.py /
# build_windowed_dataset.py -- MUST match exactly, or live features
# won't line up with what the model was trained on)
# ---------------------------------------------------------------
WINDOW_SIZE = 5
METRICS = ["bandwidth_mbps", "packet_loss_percent", "delay_ms", "jitter_ms"]


class MetricWindow:
    def __init__(self, window_size=WINDOW_SIZE):
        self.window_size = window_size
        self.buffers = {m: deque(maxlen=window_size) for m in METRICS}

    def add(self, bandwidth, packet_loss, delay, jitter):
        self.buffers["bandwidth_mbps"].append(bandwidth)
        self.buffers["packet_loss_percent"].append(packet_loss)
        self.buffers["delay_ms"].append(delay)
        self.buffers["jitter_ms"].append(jitter)

    def is_ready(self):
        return len(self.buffers["bandwidth_mbps"]) == self.window_size

    def extract_features(self):
        t = np.arange(self.window_size, dtype=float)
        feats = {}
        for m in METRICS:
            values = np.array(self.buffers[m], dtype=float)
            feats[f"{m}_current"] = float(values[-1])
            feats[f"{m}_mean"] = float(values.mean())
            feats[f"{m}_std"] = float(values.std())
            feats[f"{m}_min"] = float(values.min())
            feats[f"{m}_max"] = float(values.max())
            feats[f"{m}_slope"] = float(np.polyfit(t, values, 1)[0]) if self.window_size >= 2 else 0.0
        return feats


class MultiPathAIController(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MultiPathAIController, self).__init__(*args, **kwargs)

        self.model = joblib.load(
            "/home/monisha/sdn_ai_project/gradient_boosting_windowed_model.pkl"
        )
        self.feature_cols = joblib.load(
            "/home/monisha/sdn_ai_project/windowed_feature_columns.pkl"
        )

        self.threshold = 0.90
        self.datapaths = {}

        # rolling window buffer + simulated-trending state (see data_collector.py
        # for why this replaced independent random.uniform() calls)
        self.window = MetricWindow()
        self.sim_state = {
            "bandwidth": 70.0,
            "packet_loss": 1.0,
            "delay": 15.0,
            "jitter": 3.0,
        }
        self.sim_baseline = dict(self.sim_state)
        self.reversion_rate = 0.08
        self.congestion_episode_remaining = 0

        self.logger.info("================================")
        self.logger.info("MULTIPATH AI SDN CONTROLLER STARTED (WINDOWED FORECASTING)")
        self.logger.info("Normal Path: s1 -> s2 -> s4")
        self.logger.info("Alternate Path: s1 -> s3 -> s4")
        self.logger.info(f"Window size: {WINDOW_SIZE} samples | Forecast horizon: ~6s ahead")
        self.logger.info("================================")

        self.monitor_thread = hub.spawn(self.monitor_ai)

    # -----------------------------------------------------------
    def _step_metric(self, current, min_val, max_val, max_step):
        new_val = current + random.uniform(-max_step, max_step)
        return max(min_val, min(max_val, new_val))

    def _step_metric_with_reversion(self, current, baseline, min_val, max_val, max_step):
        pull = (baseline - current) * self.reversion_rate
        new_val = current + pull + random.uniform(-max_step, max_step)
        return max(min_val, min(max_val, new_val))

    def _next_reading(self):
        """Same trending-simulation logic as data_collector.py (including
        mean-reversion to baseline during idle periods), so live behavior
        matches what the model was trained on."""
        if self.congestion_episode_remaining == 0 and random.random() < 0.08:
            self.congestion_episode_remaining = random.randint(4, 8)

        s = self.sim_state
        b = self.sim_baseline
        if self.congestion_episode_remaining > 0:
            s["bandwidth"] = self._step_metric(s["bandwidth"] - random.uniform(1, 4), 5, 100, 2)
            s["packet_loss"] = self._step_metric(s["packet_loss"] + random.uniform(0.2, 1.0), 0, 15, 0.5)
            s["delay"] = self._step_metric(s["delay"] + random.uniform(2, 6), 1, 150, 3)
            s["jitter"] = self._step_metric(s["jitter"] + random.uniform(0.5, 2.0), 0, 40, 1)
            self.congestion_episode_remaining -= 1
        else:
            s["bandwidth"] = self._step_metric_with_reversion(s["bandwidth"], b["bandwidth"], 5, 100, 3)
            s["packet_loss"] = self._step_metric_with_reversion(s["packet_loss"], b["packet_loss"], 0, 15, 0.3)
            s["delay"] = self._step_metric_with_reversion(s["delay"], b["delay"], 1, 150, 2)
            s["jitter"] = self._step_metric_with_reversion(s["jitter"], b["jitter"], 0, 40, 0.8)

        return s["bandwidth"], s["packet_loss"], s["delay"], s["jitter"]

    # -----------------------------------------------------------
    def monitor_ai(self):

        while True:

            bandwidth, packet_loss, delay, jitter = self._next_reading()
            self.window.add(bandwidth, packet_loss, delay, jitter)

            self.logger.info(
                "Reading: Bandwidth=%.2f Mbps | Loss=%.2f%% | Delay=%.2f ms | Jitter=%.2f ms",
                bandwidth, packet_loss, delay, jitter
            )

            if not self.window.is_ready():
                self.logger.info(
                    "Warming up window (%d/%d samples) -- no prediction yet",
                    len(self.window.buffers["bandwidth_mbps"]), WINDOW_SIZE
                )
                hub.sleep(2)
                continue

            features = self.window.extract_features()
            data = pd.DataFrame([features])[self.feature_cols]  # enforce training column order

            start_time = time.perf_counter()
            prediction = self.model.predict(data)[0]
            probabilities = self.model.predict_proba(data)[0]
            confidence = probabilities[prediction]
            prediction_time_ms = (time.perf_counter() - start_time) * 1000

            self.logger.info("Threshold: %.2f", self.threshold)
            self.logger.info("Prediction Latency: %.4f ms", prediction_time_ms)
            self.logger.info("--------------------------------")
            self.logger.info(
                "AI FORECAST (~6s ahead): %s | Confidence: %.2f%%",
                "CONGESTION" if prediction == 1 else "NO CONGESTION",
                confidence * 100
            )
            self.logger.info(
                "Trend signals -> delay_slope=%.3f jitter_slope=%.3f bandwidth_slope=%.3f",
                features["delay_ms_slope"], features["jitter_ms_slope"], features["bandwidth_mbps_slope"]
            )

            if prediction == 1 and confidence >= self.threshold:
                self.logger.info("ACTION: PRE-EMPTIVELY SWITCH TO ALTERNATE PATH (s1 -> s3 -> s4)")
                self.install_alternate_path()
            else:
                self.logger.info("ACTION: USE NORMAL PATH (s1 -> s2 -> s4)")
                self.install_normal_path()

            hub.sleep(2)

    # -----------------------------------------------------------
    @set_ev_cls(
        ofp_event.EventOFPSwitchFeatures,
        CONFIG_DISPATCHER
    )
    def switch_features_handler(self, ev):

        datapath = ev.msg.datapath
        dpid = datapath.id

        self.datapaths[dpid] = datapath

        self.logger.info("Switch connected: DPID %s", dpid)

        if len(self.datapaths) == 4:
            self.logger.info("All 4 switches connected - installing initial normal path")
            self.install_normal_path()

    def delete_flows(self, datapath):

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()

        mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            match=match
        )

        datapath.send_msg(mod)

    def add_flow(self, datapath, in_port, out_port):

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(in_port=in_port)
        actions = [parser.OFPActionOutput(out_port)]
        instructions = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]

        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=100,
            match=match,
            instructions=instructions
        )

        datapath.send_msg(mod)

    def install_normal_path(self):

        if len(self.datapaths) < 4:
            return

        s1 = self.datapaths[1]
        s2 = self.datapaths[2]
        s3 = self.datapaths[3]
        s4 = self.datapaths[4]

        for dp in self.datapaths.values():
            self.delete_flows(dp)

        self.add_flow(s1, 1, 2)
        self.add_flow(s2, 1, 2)
        self.add_flow(s4, 2, 1)

        self.add_flow(s4, 1, 2)
        self.add_flow(s2, 2, 1)
        self.add_flow(s1, 2, 1)

        self.logger.info("NORMAL PATH INSTALLED")

    def install_alternate_path(self):

        if len(self.datapaths) < 4:
            return

        s1 = self.datapaths[1]
        s2 = self.datapaths[2]
        s3 = self.datapaths[3]
        s4 = self.datapaths[4]

        for dp in self.datapaths.values():
            self.delete_flows(dp)

        self.add_flow(s1, 1, 3)
        self.add_flow(s3, 1, 2)
        self.add_flow(s4, 3, 1)

        self.add_flow(s4, 1, 3)
        self.add_flow(s3, 2, 1)
        self.add_flow(s1, 3, 1)

        self.logger.info("ALTERNATE PATH INSTALLED")
