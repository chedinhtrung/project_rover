from TcpForwarder import TcpForwarder
from UdpForwarder import UdpForwarder
from config import *

tcpfwdr = TcpForwarder(gateA=tcp_gateA, gateB=tcp_gateB)
tcpfwdr.start()

udpfwd1 = UdpForwarder(gateA=udp_gateA, gateB=udp_gateB)
udpfwd2 = UdpForwarder(gateA=udp_gateA1, gateB=udp_gateB1)

udpfwd1.start()
udpfwd2.start()