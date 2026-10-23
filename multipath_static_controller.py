"""
multipath_static_controller.py

The "no AI" baseline controller for your controlled comparison test.
It installs the normal path (s1 -> s2 -> s4) once at startup and NEVER
switches, no matter what happens to the traffic. This is your control
group: same topology, same traffic, zero intelligence.

Run this INSTEAD of multipath_ai_controller_windowed.py when you want
to measure baseline (static routing) performance.
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3


class MultiPathStaticController(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MultiPathStaticController, self).__init__(*args, **kwargs)
        self.datapaths = {}

        self.logger.info("================================")
        self.logger.info("STATIC (NO-AI) BASELINE CONTROLLER STARTED")
        self.logger.info("Always uses Normal Path: s1 -> s2 -> s4")
        self.logger.info("No rerouting, no prediction -- this is the control group")
        self.logger.info("================================")

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
            self.logger.info("All 4 switches connected - installing STATIC normal path")
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

        self.logger.info("STATIC NORMAL PATH INSTALLED (permanent, no switching)")
