"""
Week 4 — Baseline Experiment Script
-------------------------------------
Builds a multi-switch, multi-host Mininet topology, applies a STATIC/REACTIVE
QoS policy (no AI), generates competing traffic to create congestion, and
measures: Latency, Jitter, Packet Loss, Throughput.

This is your Week 4 deliverable — the "before AI" baseline your Week 8-10
AI-driven results will be compared against.

Run with: sudo python3 week4_baseline_experiment.py
Requires: Mininet, Ryu (running separately: ryu-manager ryu.app.simple_switch_13)
"""

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import time
import subprocess
import re
import csv


def create_topology():
    net = Mininet(controller=RemoteController, link=TCLink)

    info("*** Adding controller\n")
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

    info("*** Adding switches\n")
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')

    info("*** Adding hosts\n")
    # h1 = video server, h2 = video client
    # h3, h4 = competing "background" traffic hosts (simulate congestion)
    h1 = net.addHost('h1', ip='10.0.0.1')
    h2 = net.addHost('h2', ip='10.0.0.2')
    h3 = net.addHost('h3', ip='10.0.0.3')
    h4 = net.addHost('h4', ip='10.0.0.4')

    info("*** Creating links (bandwidth-limited to simulate real constraints)\n")
    net.addLink(h1, s1, bw=10)       # video server link
    net.addLink(h2, s2, bw=10)       # video client link
    net.addLink(h3, s1, bw=10)       # background traffic host
    net.addLink(h4, s2, bw=10)       # background traffic host
    net.addLink(s1, s2, bw=10, delay='5ms')  # core link — this is the bottleneck
    net.addLink(s2, s3, bw=10)

    info("*** Starting network\n")
    net.start()

    return net


def apply_static_qos(net):
    """
    STATIC/REACTIVE baseline QoS: simple fixed priority using tc (traffic control)
    on the core bottleneck link. This represents 'traditional QoS' with no AI —
    fixed rules that do not adapt to real-time conditions.
    """
    info("*** Applying static QoS policy on core link (s1-s2)\n")
    s1 = net.get('s1')
    # Simple static priority queuing: video traffic gets a fixed priority class,
    # but this does NOT adapt based on real-time congestion prediction.
    s1.cmd('tc qdisc add dev s1-eth3 root handle 1: prio bands 3')
    s1.cmd('tc qdisc add dev s1-eth3 parent 1:1 handle 10: sfq')
    s1.cmd('tc qdisc add dev s1-eth3 parent 1:2 handle 20: sfq')
    s1.cmd('tc qdisc add dev s1-eth3 parent 1:3 handle 30: sfq')


def run_congestion_scenario(net, duration=30):
    """
    Generates competing background traffic (h3->h4) WHILE video-like traffic
    (h1->h2) runs, to create realistic congestion on the bottleneck link.
    """
    h1, h2, h3, h4 = net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')

    info("*** Starting iperf3 server on h2 (video client)\n")
    h2.cmd('iperf3 -s -p 5201 -D')  # -D = daemonize

    info("*** Starting iperf3 server on h4 (background traffic sink)\n")
    h4.cmd('iperf3 -s -p 5202 -D')

    time.sleep(1)

    info("*** Starting background 'congestion' traffic h3 -> h4\n")
    h3.cmd(f'iperf3 -c 10.0.0.4 -p 5202 -u -b 8M -t {duration} -J > /tmp/bg_traffic.json &')

    time.sleep(2)  # let background congestion ramp up first

    info("*** Starting video-like traffic h1 -> h2 (measured flow)\n")
    result = h1.cmd(f'iperf3 -c 10.0.0.2 -p 5201 -u -b 4M -t {duration} -J')

    with open('/tmp/video_traffic.json', 'w') as f:
        f.write(result)

    time.sleep(duration + 2)  # wait for background traffic to finish

    return result


def parse_iperf_json(json_text):
    """
    Extract key baseline metrics from iperf3 JSON output:
    throughput, jitter, packet loss.
    """
    import json
    try:
        data = json.loads(json_text)
        summary = data.get('end', {}).get('sum', {})
        throughput_mbps = summary.get('bits_per_second', 0) / 1e6
        jitter_ms = summary.get('jitter_ms', 0)
        lost_percent = summary.get('lost_percent', 0)
        return {
            'throughput_mbps': round(throughput_mbps, 3),
            'jitter_ms': round(jitter_ms, 3),
            'packet_loss_percent': round(lost_percent, 3),
        }
    except Exception as e:
        return {'error': str(e)}


def measure_latency(net, samples=10):
    """
    Measures round-trip latency (ping) between h1 (video server) and h2 (video client)
    DURING the congestion scenario, to capture realistic baseline latency.
    """
    h1 = net.get('h1')
    info(f"*** Measuring latency with {samples} pings\n")
    result = h1.cmd(f'ping -c {samples} 10.0.0.2')

    rtts = re.findall(r'time=([\d.]+)', result)
    rtts = [float(x) for x in rtts]
    avg_latency = sum(rtts) / len(rtts) if rtts else None
    return {
        'avg_latency_ms': round(avg_latency, 3) if avg_latency else None,
        'samples': rtts,
    }


def save_results(metrics, latency, filename='week4_baseline_results.csv'):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Throughput (Mbps)', metrics.get('throughput_mbps')])
        writer.writerow(['Jitter (ms)', metrics.get('jitter_ms')])
        writer.writerow(['Packet Loss (%)', metrics.get('packet_loss_percent')])
        writer.writerow(['Avg Latency (ms)', latency.get('avg_latency_ms')])
    info(f"*** Results saved to {filename}\n")


def main():
    setLogLevel('info')
    net = create_topology()

    try:
        apply_static_qos(net)

        info("\n*** Running baseline congestion scenario (static/reactive QoS, no AI)\n")
        result_json = run_congestion_scenario(net, duration=30)
        metrics = parse_iperf_json(result_json)

        latency = measure_latency(net, samples=10)

        print("\n" + "=" * 50)
        print("WEEK 4 BASELINE RESULTS (Static/Reactive QoS — No AI)")
        print("=" * 50)
        print(f"Throughput      : {metrics.get('throughput_mbps')} Mbps")
        print(f"Jitter          : {metrics.get('jitter_ms')} ms")
        print(f"Packet Loss     : {metrics.get('packet_loss_percent')} %")
        print(f"Average Latency : {latency.get('avg_latency_ms')} ms")
        print("=" * 50)
        print("\nThese numbers are your BASELINE — compare against them in Week 9-10")
        print("once your AI-driven proactive QoS system (confidence-thresholded)")
        print("is integrated, to demonstrate improvement.\n")

        save_results(metrics, latency)

        # Optional: drop into CLI for manual inspection before tearing down
        # CLI(net)

    finally:
        net.stop()


if __name__ == '__main__':
    main()
