
import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
from queue import Queue, Empty
import socket
from Network.config import *
from threading import Thread
from time import sleep
from Network.ConnectionStatus import ConnectionStatus
from Logger.Telemetry import Telemetry

class TcpDataChannel:
    def __init__(self, source: Queue, sink: Queue, remote_host: tuple, localhost:tuple=None, parent=None, send=True, recv=True):
        """
        source: FIFO Queue used to buffer data to send to the remote
        sink: FIFO Queue used to buffer data for internal processes
        parent: a string roughly describing what is using the socket. For logging and debug purpose
        if localhost is not specified, it does not bind the socket
        """
        self.sink = sink
        self.source = source
        self.remote_host = remote_host
        self.localhost = localhost
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if localhost is not None:
            self.socket.bind(localhost)
        self.socket.settimeout(3)
        self.sendthread = Thread(target=self.sendloop)
        self.recvthread = Thread(target=self.recvloop)
        self.recvactive = True
        self.sendactive = True
        self.status = ConnectionStatus()
        self.parent = parent
        self.send_enabled = send
        self.recv_enabled = recv
        self.connected = False
        self.connecting = False
        self.errored = False

    def sendloop(self):
        self.connect()
        while self.source is not None and self.sendactive:
            try:
                data = self.source.get(timeout=1)
                if self.connected:
                    self.socket.sendall(data)
                    #print("sending")
                self.status.set_sending(True)
                self.errored = False
            except Empty:
                if not self.sendactive:
                    return
                else:
                    continue

            except Exception as e: 
                print(f"Send exception {e} from {self.parent}")
                Telemetry.error(f"Send exception {e} from {self.parent}")
                if not self.sendactive:
                    return
                self.connected = False
                self.errored = True
                self.connect()

    def recvloop(self):
        self.connect()
        while self.sink is not None and self.recvactive:
            try:
                data = self.socket.recv(262144)
                if not data:
                    self.connected = False
                    self.errored = True
                    self.connect()
                self.sink.put(data)
                self.status.set_receivingtimedout(False)
                self.status.set_receiving(True)
                initialized = True
                self.errored = False
            except Exception as e:
                print(f"receive exception {e} from {self.parent}")
                sleep(1)
                if not self.recvactive:
                    return
                self.connected = False
                self.errored = True
                self.connect()

    def connect(self):
        print(f"Connecting to TCP port of {self.parent}")
        if self.errored:
            try:
                self.socket.close()
            except:
                pass
        while (self.sendactive or self.recvactive) and not self.connected:
            try:
                try:
                    self.socket.close()
                except:
                    self.socket = None
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(3)
                self.socket.connect(self.remote_host)
                self.connecting = False
                self.errored = False
                self.connected = True
                print(f"Connected to TCP port {self.remote_host} of {self.parent}")
            except Exception as e:
                print(f"Error {e} trying to connect to TCP port {self.remote_host} from {self.parent}")
                Telemetry.error(f"Error {e} trying to connect to TCP port {self.remote_host} from {self.parent}")
                self.connected = False
                sleep(3)
                continue

    def start(self):
        self.send_thread = Thread(target=self.sendloop)
        self.recvthread = Thread(target=self.recvloop)
        if self.send_enabled:
            self.sendthread.start()
        if self.recv_enabled:
            self.recvthread.start()

    def stop(self):
        self.sendactive = False
        self.recvactive = False

    def destroy(self):
        self.stop()
        self.socket.close()
