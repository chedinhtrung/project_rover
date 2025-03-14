import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
from queue import Queue
import socket
from threading import Thread

class UdpForwarder:
    def __init__(self, gateA, gateB):
        self.AtoBBuffer = Queue()
        self.BtoABuffer = Queue()
        self.remoteA = ("127.0.0.0", 50000)
        self.remoteB = ("127.0.0.0", 50001)
        self.sockA = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sockA.bind(gateA)
        self.sockB = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sockB.bind(gateB)

        self.threadABuff = Thread(target=self.loopAtoBuff)
        self.threadBBuff = Thread(target=self.loopBtoBuff)
        self.threadBuffB = Thread(target=self.loopBufftoB)
        self.threadBuffA = Thread(target=self.loopBufftoA)

    def loopAtoBuff(self):
        while True:
            try:
                data, self.remoteA = self.sockA.recvfrom(65536)
                self.AtoBBuffer.put(data)
            except:
                pass
    
    def loopBufftoB(self):
        while True:
            try:
                data = self.AtoBBuffer.get()
                self.sockB.sendto(data, self.remoteB)
            except:
                pass
    
    def loopBtoBuff(self):
        while True:
            try:
                data, self.remoteB = self.sockB.recvfrom(65536)
                self.BtoABuffer.put(data)
            except:
                pass
    
    def loopBufftoA(self):
        while True:
            try:
                data = self.BtoABuffer.get()
                self.sockA.sendto(data, self.remoteA)
            except:
                pass
    
    def start(self):
        self.threadABuff.start()
        self.threadBBuff.start()
        self.threadBuffA.start()
        self.threadBuffB.start()
        
