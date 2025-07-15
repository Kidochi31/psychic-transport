from socket import socket, AF_INET
from socketcommon import *
from iptools import IP_endpoint
from select import select
from threading import Lock
from broadcastpacket import is_request_packet, create_answer_packet


class BroadcastServer:
    def __init__(self, multicast_group: str, port: int, server_endpoint: IP_endpoint, server_data: bytes):
        self.socket: socket = create_broadcast_receiving_socket(port, multicast_group, AF_INET)
        self.lock : Lock = Lock()
        self.closed: bool = False
        self.server_endpoint = server_endpoint
        self.server_data = server_data
    
    def is_closed(self) -> bool:
        return self.closed

    def get_family(self) -> AddressFamily | None:
        with self.lock:
            if self.closed:
                return None
            return self.socket.family

    def get_local_endpoint(self) -> IP_endpoint | None:
        with self.lock:
            if self.closed:
                return None
            return get_canonical_local_endpoint(self.socket)
    
    def get_data(self) -> bytes:
        with self.lock:
            return self.server_data
    
    def get_server_endpoint(self) -> IP_endpoint:
        with self.lock:
            return self.server_endpoint

    def set_endpoint_and_data(self, endpoint: IP_endpoint, data: bytes):
        with self.lock:
            if self.closed:
                return
            self.server_endpoint = endpoint
            self.server_data = data

    def tick(self):
        with self.lock:
            if self.closed:
                return
            rl, _, _ = select([self.socket], [], [], 0)
            while len(rl) > 0:
                try:
                    data, address = self.socket.recvfrom(BUFSIZE)
                    
                    address = get_canonical_endpoint(address, self.socket.family)
                    if is_request_packet(data) and address is not None:
                        self._send_answer_to(address)
                except:
                    pass
                rl, _, _ = select([self.socket], [], [], 0)
    
    def _send_answer_to(self, endpoint: IP_endpoint):
        answer = create_answer_packet(self.server_endpoint, self.server_data)
        self.socket.sendto(answer, endpoint)

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            self.socket.close()