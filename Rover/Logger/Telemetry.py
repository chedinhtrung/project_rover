import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
from time import sleep,time
import serial
from threading import Thread
import pickle
from struct import pack, unpack
#import pynmea2
import RPi.GPIO as GPIO
import json 
import struct
from Network import NetworkQuality

class Telemetry:
    state = {
            "GPS": False,
            "Lon": 0.0,
            "Lat": 0.0,
            "Spd": 0,
            "Ctl": False,
            "Cam": "Offline",
            "Vol": 0,
            "Rol": 0,
            "Ptc": 0,
            "Yaw": 0,
            "Alt": 0,
            "Err": [],
            "Mea": False,
            "Sig": None
        }
    def __init__(self, datachannel, serialport):
        self.thread = Thread(target=self.telemetry_loop)
        self.network_quality_thread = Thread(target=self.network_quality_loop)
        self.datachannel = datachannel
        self.active = True
        self.serial_port = serialport
        self.control = False
        self.meas = False 
  
    def network_quality_loop(self):
        try:
            NetworkQuality.Login()
            sleep(1)
        except Exception as e:
            print(e)
            Telemetry.error(str(e))
            
        while self.active:
            try:
                Telemetry.state["Sig"] = NetworkQuality.getData()
            except:
                pass
            sleep(20)

    def telemetry_loop(self):
        format = "7f"           # 6 float values, 4 bytes each
        size = struct.calcsize(format)
        while self.active:
            try:
                while ord(self.serial_port.read(1)) != 0x02:    # Block until start byte is detected
                    pass
                b = self.serial_port.read(size)
                sens_vals = unpack(format, b)
                Telemetry.state['Rol'] = sens_vals[0]
                Telemetry.state['Ptc'] = sens_vals[1]
                Telemetry.state['Yaw'] = sens_vals[2]
                Telemetry.state['Lon'] = sens_vals[3]
                Telemetry.state['Lat'] = sens_vals[4]
                Telemetry.state['Alt'] = sens_vals[5]
                Telemetry.state['Vol'] = sens_vals[6]
                msg = json.dumps(Telemetry.state)
                self.datachannel.source.put(bytes(msg, "utf-8"))
                Telemetry.state["Err"] = [] # Resets the error string after sending
                #sleep(0.02)
                sleep(0.08)
            except struct.error:
                pass
            except Exception as e:
                print('telemetry error: ' + str(e))
                Telemetry.error(f"Telemetry error: {e}")
                self.meas = False
    
    @classmethod
    def error(cls, message):
        Telemetry.state["Err"].append(message)
    
    def start(self):
        self.thread.start()
        self.network_quality_thread.start()

    def stop(self):
        self.active = False
        self.datachannel.destroy()
    
