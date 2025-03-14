import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
from queue import Queue, Empty
import subprocess
from Network.UdpDataChannel import UdpDataChannel
from threading import Thread
import numpy as np
from Network.config import *
from time import sleep
from PyQt5.QtGui import QImage
from PyQt5.QtCore import pyqtSignal, QObject
from Logger.MissionControl_Logger import MCLogger
import time

class Decoder:
    def __init__(self, config, source: Queue, sink: Queue):
        """
        Contains the ffmpeg subprocess pipeline for decoding and returning frames
        """
        self.config = config
        self.source = source
        self.sink = sink
        self.subprocess = None
        self.decode_inthread = Thread(target=self.decode_inloop)
        self.decode_outthread = Thread(target=self.decode_outloop)
        self.active = True
        ffmpeg_cmd = ['ffmpeg', 
        '-analyzeduration','0', 
        '-probesize', '32',
        '-flags', 'low_delay',
        '-hwaccel', 'd3d11va',
        '-fflags', 'nobuffer', 
        '-framerate', '18',
        #'-err_detect', 'ignore_err',
        '-vsync', 'passthrough',
        '-i', '-',
        '-c:v', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-f', 'rawvideo',
        '-']
        self.process = subprocess.Popen(
            ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.start()

    def decode_inloop(self):
        """
        Continuously read from the source and write into the ffmpeg subprocess
        """
        while self.active:
            try:
                undecoded_frame = self.source.get(timeout=1)
                self.process.stdin.write(undecoded_frame)
            except Empty:
                if not self.active:
                    return

    def decode_outloop(self):
        """
        Continuously read from the ffmpeg subprocess and write into the sink
        """
        frame_size = self.config["width"] * self.config["height"] * 3
        while self.active:
            try:
                decoded_frame = self.process.stdout.read(frame_size)
                self.sink.put(decoded_frame)
            except Empty:
                if not self.active:
                    return
    
    def start(self):
        self.decode_inthread.start()
        self.decode_outthread.start()
    
    def stop(self):
        self.active = False
    
    def destroy(self):
        self.stop() 
        self.process.terminate()

class VideoConnector(QObject):

    frame_signal = pyqtSignal(object)
    status_signal = pyqtSignal(str)

    def __init__(self, datachannel, config=None, name: str = ""):
        super(VideoConnector, self).__init__()
        self.datachannel = datachannel
        self.datachannel.parent = f"Video Connector {name}"
        self.config = config
        self.source = Queue()  # Decoder pushes his results here
        self.decoder = Decoder(
            config=config, source=self.datachannel.sink, sink=self.source)  # Decoder eats data from datachannel
        self.streamthread = Thread(target=self.streamloop)
        self.active = True

    def streamloop(self):
        MCLogger.logOK("Streaming started. Waiting for rover...")
        receiving = False
        while self.active:
            try:
                raw_frame = self.source.get(timeout=1)
                #print(len(raw_frame))
                frame = np.frombuffer(
                    raw_frame, dtype=np.uint8).reshape(self.config["height"], self.config["width"], 3)
                # Process the frame as needed (e.g., display or save)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qimage = QImage(
                    frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
                
                self.frame_signal.emit(qimage)
                if not receiving: 
                    MCLogger.logOK("Receiving video from rover...")
                receiving = True
            except Empty:
                if self.active:
                    pass
                else:
                    return
            except ValueError:
                pass

            except Exception as e:
                MCLogger.logError("Video error: " + e)
    
    def start(self):
        self.streamthread.start()
    
    def stop(self):
        self.active = False
        self.streamthread.join()
    
    def destroy(self):
        self.stop()
        self.decoder.destroy()




