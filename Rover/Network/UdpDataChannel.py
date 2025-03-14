import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
from queue import Queue, Empty
import socket
from Network.config import *
from threading import Thread


class ConnectionStatus:
    def __init__(self) -> None:
        self.sending = False
        self.receiving = False
        self.sending_timedout = False
        self.receiving_timedout = False
        self.sending_err = None
        self.receiving_err = None

    def set_sending(self, state: bool):
        self.sending = state

    def set_receiving(self, state: bool):
        self.receiving = state

    def set_sendingtimedout(self, state: bool):
        self.sending_timedout = state

    def set_receivingtimedout(self, state: bool):
        self.receiving_timedout = state
    
    def set_receiving_err(self, exception):
        self.receiving_err = exception
    
    def set_sending_err(self, exception):
        self.sending_err = exception

    # TODO: implement status report on the UI


class UdpDataChannel:
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
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if localhost is not None:
            self.socket.bind(localhost)
        self.socket.settimeout(1)
        self.sendthread = Thread(target=self.sendloop)
        self.recvthread = Thread(target=self.recvloop)
        self.recvactive = True
        self.sendactive = True
        self.status = ConnectionStatus()
        self.parent = parent
        self.send_enabled = send
        self.recv_enabled = recv

    def sendloop(self):
        while self.source is not None and self.sendactive:
            try:
                data = self.source.get(timeout=1)
                self.socket.sendto(data, self.remote_host)
                self.status.set_sendingtimedout(False)
                self.status.set_sending(True)
            except Empty:
                if not self.sendactive:
                    return
                else:
                    continue
            except socket.error as e:
                print(f"error sending: {e}, lost {len(data)}")
                #Logger.log(f"Network error: {e} from {self.parent}")
                pass
            
            except Exception as e: 
                if not self.sendactive:
                    return

    def recvloop(self):
        print("Waiting for connection...")
        while self.sink is not None and self.recvactive:
            try:
                data, remote = self.socket.recvfrom(65536)
                if remote == self.remote_host:
                    self.sink.put(data)
                self.status.set_receivingtimedout(False)
                self.status.set_receiving(True)
            except socket.timeout:
                if not self.recvactive:
                    return
                if self.status.receiving:
                    #Logger.log(f"Receive loop timeout from {self.parent}")
                    self.status.set_receivingtimedout(True)
                continue

            except socket.error as e:
                print(f"Network error: {e}")
                self.status.set_receiving_err(e)
            
            except Exception as e:
                if not self.recvactive:
                    return

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
    
if __name__ == "__main__":
    from time import sleep
    source = Queue()
    sink = Queue()
    channel = UdpDataChannel(source=source, sink=sink, remote_host=("127.0.0.1", 9000), localhost=None)
    channel.start()
    for i in range(40):
        source.put(bytes("Hello", "utf-8"))
        print("sent")
        sleep(1)
