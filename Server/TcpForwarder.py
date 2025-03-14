import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
import socket
from queue import Queue, Empty
from threading import Thread
from time import sleep

class TcpForwarder:
    def __init__(self, gateA, gateB):
        self.gateA = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.gateB = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.gateA.bind(gateA)
        self.gateB.bind(gateB)
        self.AtoBbuffer = Queue()
        self.BtoAbuffer = Queue()
        self.gateA.settimeout(None)
        self.gateB.settimeout(None)

        self.clientA = None
        self.clientB = None

        self.threadA = Thread(target=self.listen_loopA)
        self.threadB = Thread(target=self.listen_loopB)
        self.threadfwdA = Thread(target=self.fwd_loopA)
        self.threadfwdB = Thread(target=self.fwd_loopB)

    def listen_loopA(self): 
        print(f"Gate A listening on {self.gateA}")
        while True: 
            self.gateA.listen()
            clientA, ipA = self.gateA.accept()
            try:
                self.clientA.close()
                print("New connection. Shut down old one on side A")
            except:
                pass
            self.clientA = None
            sleep(0.01)
            self.clientA = clientA
            self.clientA.settimeout(1)
            print(f"Rover: {ipA}")
    
    def fwd_loopA(self):
        while True:
            if self.clientA is not None:
                try:
                    data = self.clientA.recv(262144)
                    print("Recv from " + str(self.clientA))
                    if not data:
                        try:
                            self.clientA.close()
                            print("ouch, no data. shutting down connection on side A")
                        except:
                            pass
                        self.clientA = None
                    if (self.clientB is not None) and data:
                        self.AtoBbuffer.put(data)
                        #print(f"A to B: {len(data)}")
                        sleep(0)
                except Exception as e:
                    print(e)
            sleep(0)
    
    def listen_loopB(self): 
        print(f"Gate B listening on {self.gateB}")
        while True: 
            self.gateB.listen()
            clientB, ipB = self.gateB.accept()
            try:
                self.clientB.close()
                print("new connection. shut down old one on side B")
            except:
                pass
            self.clientB = None
            sleep(0.01)
            self.clientB = clientB
            self.clientB.settimeout(1)
            print(f"Control: {ipB}")
    
    def fwd_loopB(self):
        while True:
                if self.clientB is not None:
                    try:
                        data = self.AtoBbuffer.get(timeout=1)
                        sleep(0)
                        if self.clientB is not None:
                            self.clientB.sendall(data)
                            print("Sent to " + str(self.clientB))
                    except Empty:
                        pass
                    except Exception as e:
                        print(f"cant send to B with error {e}")
                sleep(0)

    def start(self):
        self.threadA.start()
        self.threadB.start()
        self.threadfwdA.start()
        self.threadfwdB.start()
    

    
    
                    

