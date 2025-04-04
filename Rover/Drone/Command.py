import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
from time import sleep,time
import serial
from threading import Thread
import pickle
from struct import pack, unpack
from Logger.Telemetry import Telemetry
import subprocess
from queue import Empty
# This has beed edited from console tool of Mission Control
class Command:
    def __init__(self, datachannel, main=None):
        self.thread = Thread(target=self.command_loop)
        self.control = False
        self.active = True
        self.state = {"pan":45, "tilt": 45, "left": 0, "right": 0}
        self.datachannel = datachannel
        self.main = main
           

        try:
            print("Connecting to Control")
            self.serial = serial.Serial(port='/dev/tty0', baudrate=115200,bytesize=serial.EIGHTBITS, timeout=1,
            parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
            self.control = True
            print("Connected to Control")
            Telemetry.state["Ctl"] = True
        except Exception as e: 
            self.serial = None
            print(f"Control connecteion error: {e}")
            Telemetry.error(f"Control connection error: {e}")

    def command_loop(self):
        while (not self.control) and self.active:
            try:
                print(f"Connecting to Control")
                self.serial = serial.Serial(port='/dev/tty0', baudrate=115200,bytesize=serial.EIGHTBITS, timeout=1,
                                         parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
                self.control = True
                Telemetry.state["Ctl"] = True
                print("Connected to Control")
            except Exception as e:
                print(f"Control connecteion error: {e}")
                Telemetry.error(f"Control connection error: {e}")
                Telemetry.state["Ctl"] = False

        pan = 45 
        tilt = 40
        while self.active:
            try:
                cmd_data = self.datachannel.sink.get(timeout=0.5)
                command = pickle.loads(cmd_data)
                #print(command)
                header = command[0]
                if (header == 'M') or (header == 'B'): # M = Move, B = Brake
                    left = int(98*command[1])
                    right = int(99*command[2])
                    if left > 0 and left < 2: 
                        left = 0
                    if right > 0 and right < 2:
                        right = 0
                    #print([left, right])
                    self.serial.write(bytes(header, 'utf-8'))
                    cmd = pack('ii', left, right)
                    self.serial.write(cmd)
                elif header == 'C':     # Controls the pan tilt 
                    self.serial.write(bytes(header, 'utf-8'))
                    pan -= command[1]
                    tilt -= command[2]
                    if pan > 90:
                        pan = 90
                    elif pan < 0:
                        pan = 0
                    if tilt > 90:
                        tilt = 90
                    elif tilt < 0:
                        tilt = 0
                    cmd = pack('ii', pan, tilt)
                    self.serial.write(cmd)
                    #print((pan, tilt))
                elif header == 'D':     # Realigns pan tilt
                    self.serial.write(bytes('C', 'utf-8'))
                    pan = 45
                    tilt = 45
                    cmd = pack('ii', pan, tilt)
                    self.serial.write(cmd)
                
                elif header == 'L':     # Turn on/off light
                    self.serial.write(bytes('L', 'utf-8'))
                    cmd = pack('ii', 0, 0)
                    self.serial.write(cmd)
                elif header == 'V':
                    if self.main is None:
                        continue     # TODO: switch camera to data saving mode
                    self.main.camera_connection.set_mode_datasaving()
                elif header == 'N':
                    if self.main is None:
                       continue
                    self.main.camera_connection.set_mode_normal()
                elif header == 'F':     # F = Fire
                    self.serial.write(bytes('F', 'utf-8'))
                    cmd = pack('ii', 0, 0)
                    self.serial.write(cmd)
                elif header == 'R':
                    self.reboot()
                elif header == 'K':    # Turn on/off mirror
                    if not self.control.mirror.active:
                        self.control.mirror.active = True
                        self.control.mirror.start()
                    else:
                        self.control.mirror.active = False
                        self.control.mirror.stop()
                self.control = True
                Telemetry.state["Ctl"] = True
                sleep(0.03)
            except pickle.UnpicklingError:
                pass
            except Empty:
                Telemetry.state["Ctl"] = False
            except Exception as e:
                Telemetry.error(f"Command error: {e}")
                Telemetry.state["Ctl"] = False
                #self.control = False

    def start(self):
        self.thread.start()
    
    def stop(self):
        self.active = False
    
    def reboot(self):
        try:
            Telemetry.error("Rover shutting down...")
            sleep(2)
            self.stop()
            subprocess.call(["sudo", "reboot", "-h", "now"])
        except Exception as e:
            pass

        finally:
            subprocess.call(["sudo", "reboot", "-h", "now"])
