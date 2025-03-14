import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))

import picamera
from Network.UdpDataChannel import UdpDataChannel
from threading import Thread
from config import *
from queue import Queue
from Command import Command
import time
import subprocess
from Logger.Telemetry import Telemetry
import RPi.GPIO as GPIO

class CameraConnection:
    def __init__(self, datachannel:UdpDataChannel) -> None:
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
        except Exception as e:
            print(e)
            # TODO: Log the error and send to the remote connection
    
    def camera_loop(self):
        self.camera.start_recording(self, format='h264')
        self.camera.wait_recording()
    
    def write(self, data):
        #print(len(data))
        while len(data) > 3000:
            self.datachannel.source.put(data[0:3000])
            data=data[3000:]
        #data += b'\x00\x00'
        self.datachannel.source.put(data)
    
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
        self.cmd_video_datachannel = UdpDataChannel(source=Queue(), sink=Queue(), remote_host=video_cmd_datachannel["remote_host"])
        self.cmd_video_datachannel.start()
        self.camera_connection = CameraConnection(datachannel=self.cmd_video_datachannel)
        self.command = Command(datachannel=self.cmd_video_datachannel)
        self.telemetry_datachannel = UdpDataChannel(source=Queue(), sink=Queue(), 
                                               remote_host=telemetry_datachannel["remote_host"], recv=False)
        self.telemetry = Telemetry(datachannel=self.telemetry_datachannel)
        self.telemetry_datachannel.start()
        self.telemetry.start()
        self.camera_connection.start()
        self.command.start()
    
    def shutdown(self, event):
        try:
            self.camera_connection.stop()
            self.telemetry.stop()
            self.command.stop()
            self.cmd_video_datachannel.destroy()
            self.telemetry_datachannel.destroy()
            subprocess.call(["sudo", "shutdown", "-h", "now"])
        except Exception as e:
            pass

        finally:
            subprocess.call(["sudo", "shutdown", "-h", "now"])

Main()

