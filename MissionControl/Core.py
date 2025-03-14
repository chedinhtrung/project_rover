import sys
import os

from VideoConnector import VideoConnector
from Network.UdpDataChannel import UdpDataChannel
from Network.config import *
from queue import Queue
from Command import Command
from Telemetry import Telemetry
from Logger.MissionControl_Logger import MCLogger
from Network.TcpDataChannel import TcpDataChannel

class MissionControlCore:
    def __init__(self, ui):
        MCLogger.set_logging_element(ui.serverlog)
        self.video_cmd_datachannel = UdpDataChannel(source=Queue(), sink=Queue(), remote_host=video_cmd_datachannel["remote_host"])
        self.video_connector = VideoConnector(self.video_cmd_datachannel, config=video, name="Main Video Feed")
        #self.video_datachannel = TcpDataChannel(source=Queue(), sink=Queue(), remote_host=tcp_gateB, send=False)
        #self.video_connector = VideoConnector(self.video_datachannel, config=video, name="Main Video Feed")
        self.videodisplay = ui.videodisplay
        self.throttle_dipslay = ui.throttledisplay
        self.videodisplay.set_videosource(self.video_connector)
        self.command = Command(self.video_cmd_datachannel)
        self.throttle_dipslay.set_controlsource(self.command)
        self.telemetry_datachannel = UdpDataChannel(source=Queue(), sink=Queue(), remote_host=telemetry_datachannel["remote_host"])
        self.telemetry = Telemetry(datachannel=self.telemetry_datachannel)
        #self.telemetry = Telemetry(datachannel=self.video_cmd_datachannel)
        self.mapdisplay = ui.mapdisplay
        self.mapdisplay.set_mapupdater(self.telemetry)
        self.roverstatusdisplay = ui.roverstatusdisplay
        self.roverstatusdisplay.set_updater(self.telemetry)
        
    def start(self):
        self.telemetry_datachannel.start()
        #self.video_datachannel.start()
        self.telemetry.start()
        self.video_cmd_datachannel.start()
        self.video_connector.start()
        self.command.start()

    def stop(self):
        self.video_connector.destroy()
        self.video_cmd_datachannel.destroy()
        self.command.stop()
        self.telemetry.stop()
        #self.video_datachannel.destroy()
        self.telemetry_datachannel.destroy()
