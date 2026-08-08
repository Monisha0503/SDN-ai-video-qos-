"""
Week 3 - Basic Mininet + Ryu Test Topology
--------------------------------------------
A simple 4-host, 2-switch topology used to verify that Mininet and the
Ryu SDN controller are correctly communicating, before building the
full baseline/AI experiments in later weeks.

Prerequisites:
  1. Install Mininet:  sudo apt-get install mininet
  2. Install Ryu:      pip3 install ryu
  3. Start Ryu controller in a separate terminal:
       ryu-manager ryu.app.simple_switch_13

Run this script with:
  sudo python3 basic_topology.py
"""

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink


def create_topology():
    net = Mininet(controller=RemoteController, link=TCLink)

    print("Adding controller")
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

    print("Adding switches")
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    print("Adding hosts")
    h1 = net.addHost('h1', ip='10.0.0.1')
    h2 = net.addHost('h2', ip='10.0.0.2')
    h3 = net.addHost('h3', ip='10.0.0.3')
    h4 = net.addHost('h4', ip='10.0.0.4')

    print("Creating links")
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s2)
    net.addLink(h4, s2)
    net.addLink(s1, s2)

    print("Starting network")
    net.start()

    print("Running CLI - try 'pingall' to verify connectivity")
    CLI(net)

    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    create_topology()
