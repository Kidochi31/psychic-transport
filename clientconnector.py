from clientconnection import ClientConnection
from iptools import *
from socket import socket
from packet import *
from time import time_ns

VERS = 0
VERSION = 0
init_request_timeout_ns = 100_000_000

class ClientConnector:
    # Fields
    # ------
    # connection_info: ClientConnection | None
    # server: IP_endpoint
    # family: AddressFamily
    # socket: udp socket
    def __init__(self, max_timeouts: int, socket: socket, name: str, data: bytes, server: IP_endpoint):
        self.connection_info:  ClientConnection | None= None
        self.server = server
        self.time_request_sent: int = 0
        self.max_timeouts = max_timeouts
        self.num_timeouts = 0
        self.socket = socket
        self.name = name
        self.data = data
        self.failed = False

        if not self._send_request_to_server(self.server):
            self.failed = True

    def is_connected(self) -> bool:
        return self.connection_info is not None

    def connect_failed(self) -> bool:
        return self.failed
    
    def is_connecting(self) -> bool:
        return not self.is_connected() and not self.connect_failed()
        
    def report_data_received(self, data: bytes | None) -> None:
        if data is None or self.is_connected() or self.connect_failed():
            return
        info = interpret_packet_safe(data)
        if info is not None and info[0] == PacketType.ACCEPT:
            self._manage_accept_packet(info[1], self.server)
        # otherwise, ignore packet

    def tick(self) -> ClientConnection | bool:
        # ticks the client forward. Ensure to run tick() before receiving or sending.
        # returns true if currently connecting, false if failed
        if self.connection_info is not None:
            return self.connection_info

        if self.failed:
            return False # failed connecting -> return False
        # currently waiting for server response
        # check timeout
        if time_ns() >= self.time_request_sent + init_request_timeout_ns:
            self.num_timeouts += 1
            if self.num_timeouts >= self.max_timeouts:
                # timeout
                self.failed = True
                return False
            # resend
            self._send_request_to_server(self.server)
        return True

                    
    def _manage_accept_packet(self, data: dict[str, Any], server: IP_endpoint):
        #[("vers", ("version", ("timestep0", ("lentimestep", ("timestamp", ("data",
        if data["vers"] != VERS:
            self.failed = True
            return
        if data["version"] != VERSION:
            self.failed = True
            return
        rtt_ms = (time_ns() - self.time_request_sent) // 1_000_000
        one_way_ms = rtt_ms // 2
        timestamp = int(data["timestamp"])
        server_time = timestamp + one_way_ms
        server_time_minus_client_time = server_time - time_ns() // 1_000_000
        self.connection_info = ClientConnection(server, rtt_ms, server_time_minus_client_time, data["lentimestep"], data["timestep0"], data["data"])
    
    def _send_request_to_server(self, server: IP_endpoint) -> bool:
        try:
            request = create_request_packet(VERS, VERSION, self.name, self.data)
            if request is not None:
                self.socket.sendto(request, server)
                self.time_request_sent = time_ns()
                return True
        except:
            pass
        return False