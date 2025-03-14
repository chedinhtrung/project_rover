
import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))

from libcamera import Transform
import picamera2
from picamera2.outputs import FileOutput
from picamera2.encoders import H264Encoder
from io import BufferedIOBase
from Network.UdpDataChannel import UdpDataChannel
from Network.TcpDataChannel import TcpDataChannel
from threading import Thread
from config import *
from queue import Queue
from Command import Command
import time
import serial
import subprocess
from Logger.Telemetry import Telemetry
import RPi.GPIO as GPIO
from time import sleep
#import cv2
from base64 import b64encode
import struct
from DataLogger.datalogger import DataLogger

class CameraConnection(BufferedIOBase):
    def __init__(self, datachannel):
        self.camera = None
        self.thread = Thread(target=self.camera_loop)
        self.init_camera(config=camera)
        self.datachannel = datachannel
        self.seqnr = 0
    def init_camera(self, config):
        try:
            self.camera = picamera2.Picamera2()
            #self.camera.resolution = config["resolution"]
            camera_config = self.camera.create_video_configuration(
            main={"size": (1280, 720)},
            controls={"FrameRate":20.0}) 
            #,transform=Transform(hflip=True, vflip=True))
            #camera_config['transform']['rotation'] = 180
            #self.camera.framerate = config["framerate"]
            #self.quality = config["quality"]
            # Start a preview and let the camera warm up for 2 seconds
            # self.camera.start_preview()
            time.sleep(2)
            self.mode = config["mode"]
            Telemetry.state["Cam"] = config["mode"]
            self.camera.configure(camera_config)
        except Exception as e:
            print(e)
            Telemetry.error(f"Camera error: {e}")
    
    def camera_loop(self):
        try:
            encoder = H264Encoder()
            self.camera.start_recording(encoder, FileOutput(self))
            #self.camera.wait_recording()
        except Exception as e:
            Telemetry.error(f"Camera error: {e}")
    
    def write(self, data):
        if self.datachannel.connected:
            self.datachannel.source.put(data)
            #print(len(data))
        else:
            while self.datachannel.source.qsize() != 0 and not(self.datachannel.connected):
                self.datachannel.source.get()
        #while len(data) > 1500:
        #    package = data[:1500]
        #    package += struct.pack('>I', self.seqnr)
        #    self.datachannel.source.put(package)
        #    data = data[1500:]
        #    self.seqnr += 1
        #if len(data) > 0:
        #    data += struct.pack('>I', self.seqnr)
        #    self.datachannel.source.put(data)
        #    self.seqnr += 1

    def start(self):
        self.thread.start()
    
    def stop(self):
        if self.camera is not None:
            self.camera.stop_recording()
            self.camera.close()
    
    def set_mode_datasaving(self):
        if self.mode == "Data saving":
            Telemetry.state["Cam"] = "Data saving"
            return
        print("Entered data saving mode")
        Telemetry.state["Cam"] = "Data saving"
        self.mode = "Data saving"
        self.stop()
        self.init_camera(config=camera_datasaving)
        self.camera.color_effects = (128, 128)
        #self.camera.shutter_speed = self.camera.exposure_speed
        #self.camera.iso = 800
        self.thread = Thread(target=self.camera_loop)
        self.start()
    
    def set_mode_normal(self):
        if self.mode == "Normal":
            Telemetry.state["Cam"] = "Normal"
            return
        print("Entering normal mode")
        Telemetry.state["Cam"] = "Normal"
        self.mode = "Normal"
        self.stop()
        self.init_camera(config=camera)
        self.thread = Thread(target=self.camera_loop)
        self.start()

class MirrorConnection: 
    def __init__(self):
        self.thread = None
        self.datachannel = UdpDataChannel(source=Queue(), sink=Queue(), remote_host=telemetry_datachannel["remote_host"])
        self.active = False
    
    def camera_loop(self):
        while self.active:
            vid = cv2.VideoCapture(1)
            vid.set(3,320)
            vid.set(4,240)
            try:
                img, frame = vid.read()
                encoded, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 25])
                msg = b64encode(buffer)
                #t1 = time()
                self.datachannel.source.put(msg)
            except Exception as e:
                print(e)
    
    def start(self):
        print("Started mirror")
        self.datachannel.start()
        self.thread = Thread(target=self.camera_loop)
        self.active = True
        self.thread.start() 

    def stop(self):
        print("Stopped mirror")
        self.active = False
        self.datachannel.destroy()  

class Main: 
    def __init__(self) -> None:
        fc_serial = serial.Serial(
             port='/dev/ttyS0',  # Use /dev/ttyAMA0 for older Raspberry Pi models
             baudrate=115200,      # Set the baud rate to match your device
             parity=serial.PARITY_NONE,
             stopbits=serial.STOPBITS_ONE,
             bytesize=serial.EIGHTBITS,
             timeout=1           # Read timeout in seconds
        )
        button_pin = 17
        GPIO.setmode(GPIO.BCM)
        #GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        #GPIO.add_event_detect(button_pin, GPIO.FALLING, callback=self.shutdown, bouncetime=300)
        self.video_datachannel = TcpDataChannel(source=Queue(), sink=Queue(), remote_host=tcp_gateA, recv=False) # TCP MODE
        #self.video_datachannel = UdpDataChannel(source=Queue(), sink=Queue(), remote_host=video_cmd_datachannel["remote_host"]) # UDP MODE
        self.video_datachannel.parent = "Video"
        self.video_datachannel.start()
        self.cmd_telemetry_datachannel = UdpDataChannel(source=Queue(), sink=Queue(), remote_host=video_cmd_datachannel["remote_host"])      #Default mode TCP Video
        #self.cmd_telemetry_datachannel = UdpDataChannel(source=Queue(), sink = Queue(), remote_host=telemetry_datachannel["remote_host"], recv=False)  # Mode UDP Video
        self.camera_connection = CameraConnection(datachannel=self.video_datachannel)
        self.camera_connection.start()
        #self.command = Command(datachannel=self.cmd_telemetry_datachannel, main=self)
        #self.telemetry = Telemetry(self.cmd_telemetry_datachannel, fc_serial)
        self.cmd_telemetry_datachannel.start()
        #self.telemetry.start()
        #self.command.start()

        #self.mirror = MirrorConnection()
        
        self.datalogger = DataLogger(fc_serial)
        self.datalogger.start()

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

