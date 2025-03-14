import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))

import picamera
from Network.UdpDataChannel import UdpDataChannel
from Network.TcpDataChannel import TcpDataChannel
from threading import Thread
from config import *
from queue import Queue
from Command import Command
import time
import subprocess
from Logger.Telemetry import Telemetry
import RPi.GPIO as GPIO
from time import sleep

class CameraConnection:
    def __init__(self, datachannel):
        self.camera = None
        self.thread = Thread(target=self.camera_loop)
        try:
            self.camera = picamera.PiCamera()
            self.camera.resolution = camera["resolution"]
            self.camera.framerate = camera["framerate"]
            # Start a preview and let the camera warm up for 2 seconds
            self.camera.start_preview()
            time.sleep(2)
            self.datachannel = datachannel
            Telemetry.state["Cam"] = True
        except Exception as e:
            print(e)
            Telemetry.error(f"Camera error: {e}")
    
    def camera_loop(self):
        try:
            self.camera.start_recording(self, format='h264', quality=27)
            self.camera.wait_recording()
        except Exception as e:
            Telemetry.error(f"Camera error: {e}")
    
    def write(self, data):
        #print(len(data))
        if self.datachannel.connected:
            self.datachannel.source.put(data)
        else:
            while self.datachannel.source.qsize() != 0 and not(self.datachannel.connected):
                self.datachannel.source.get()
    
    def start(self):
        self.thread.start()
    
    def stop(self):
        self.camera.stop_recording()

class Main: 
    def __init__(self) -> None:
        button_pin = 17
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(button_pin, GPIO.FALLING, callback=self.shutdown, bouncetime=300)
        self.video_datachannel = TcpDataChannel(source=Queue(), sink=Queue(), remote_host=tcp_gateA, recv=False)
        self.video_datachannel.parent = "Video"
        self.video_datachannel.start()
        self.cmd_telemetry_datachannel = UdpDataChannel(source=Queue(), sink=Queue(), remote_host=video_cmd_datachannel["remote_host"])
        self.camera_connection = CameraConnection(datachannel=self.video_datachannel)
        self.camera_connection.start()
        self.command = Command(datachannel=self.cmd_telemetry_datachannel)
        self.telemetry = Telemetry(datachannel=self.cmd_telemetry_datachannel)
        self.cmd_telemetry_datachannel.start()
        self.telemetry.start()
        self.command.start()
    
    def shutdown(self, event):
        try:
            Telemetry.error("Rover shutting down...")
            sleep(2)
            self.camera_connection.stop()
            self.telemetry.stop()
            self.command.stop()
            self.video_datachannel.destroy()
            self.cmd_telemetry_datachannel.destroy()
            subprocess.call(["sudo", "shutdown", "-h", "now"])
        except Exception as e:
            pass

        finally:
            subprocess.call(["sudo", "shutdown", "-h", "now"])

Main()

