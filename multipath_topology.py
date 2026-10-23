from mininet.topo import Topo
from mininet.link import TCLink


class MultiPathTopo(Topo):

    def build(self):

        # Hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')

        # Switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')

        # Host connections
        self.addLink(h1, s1, cls=TCLink, bw=100)
        self.addLink(h2, s4, cls=TCLink, bw=100)

        # Normal Path: s1 -> s2 -> s4
        self.addLink(s1, s2, cls=TCLink, bw=10)
        self.addLink(s2, s4, cls=TCLink, bw=10)

        # Alternate Path: s1 -> s3 -> s4
        self.addLink(s1, s3, cls=TCLink, bw=20)
        self.addLink(s3, s4, cls=TCLink, bw=20)


topos = {
    'multipath': lambda: MultiPathTopo()
}
