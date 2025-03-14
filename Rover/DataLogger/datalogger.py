import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
from time import sleep,time,perf_counter
import serial
from threading import Thread
from struct import pack, unpack
import RPi.GPIO as GPIO 
import struct
import datetime
import numpy as np
from queue import Queue, Empty
import csv

class FileWriter:
    def __init__(self, source:Queue):
        self.thread = Thread(target=self.writedata_loop)
        self.source = source
        self.active = False
        self.filename = f"../DataLogger/Data/Log_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        self.file = None
        self.buffer = []
        self.buffer_size = 1000   # 250 data/s => 1 write every 4s 
        self.header = ['Motor_fl', 'Motor_fr', 'Motor_bl', 'Motor_br', 'Gyro_x', 'Gyro_y', 'Gyro_z', 'Accel_x', 'Accel_y', 'Accel_z', 'Alt']
    
    def writedata_loop(self):
        while self.active:
            if len(self.buffer) == self.buffer_size:
                self.writer.writerows(self.buffer)
                self.buffer = []
            try: 
                data = self.source.get(timeout=0.01)
                self.buffer.append(data)
            except Exception as e:
                print(e)
                self.stop()

    
    def start(self):
        self.filename = f"../DataLogger/Data/Log_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        with open(self.filename, mode='w', newline='') as file:
            self.writer = csv.writer(file)
            self.writer.writerow(self.header)
        self.file = open(self.filename, mode='a', newline='')
        self.writer = csv.writer(self.file)
        print(str(self.file))
        self.active = True
        self.thread = Thread(target=self.writedata_loop)
        self.thread.start()
    
    def stop(self):
        self.active = False
        self.file.close()


class DataLogger:
    def __init__(self, serialport):
        self.thread = Thread(target=self.datagather_loop)
        self.active = True
        self.serial_port = serialport
        self.sink = Queue()
        self.filewriter = FileWriter(source=self.sink)
        self.recording = False

    def datagather_loop(self):
        format = "<4H7h"
        size = struct.calcsize(format)
        last_report = time()

        while self.active: 
            try:
                startbyte = ord(self.serial_port.read(1))
                if startbyte != 0x02:
                    continue

                if not self.filewriter.active:
                    print("Starting file writer")
                    self.filewriter.start()
                    #pass

                if not self.recording:
                    print("recording...")
                    self.recording = True
                
                b = self.serial_port.read(size)
                sens_vals = unpack(format, b)
                if self.filewriter.active:
                    self.sink.put(sens_vals)

                #print(sens_vals[0])
                #if time() - last_report > 0.25:
                    #print(sens_vals)
                    #last_report = time()

            except Exception as e:
                print(str(e))
                sleep(0.1)
                if self.recording:
                    self.recording = False
                    self.filewriter.stop()
    
    def start(self):
        print("Starting recording")
        self.thread = Thread(target=self.datagather_loop)
        self.thread.start()

    def stop(self):
        print("Stopped recording")
        self.active = False
        self.filewriter.stop()
        
