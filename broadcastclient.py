from socket import socket, AF_INET
from socketcommon import *
from iptools import IP_endpoint
from select import select
from threading import Lock
from broadcastpacket import create_request_packet, interpret_answer_packet


class BroadcastClient:
    def __init__(self, multicast_endpoint: IP_endpoint, port: int = 0):
        self.socket: socket = create_broadcast_sending_socket(port, AF_INET)
        self.multicast_endpoint: IP_endpoint = multicast_endpoint
        self.lock : Lock = Lock()
        self.closed: bool = False
    
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

    def tick(self) -> list[tuple[IP_endpoint, bytes]]:
        with self.lock:
            if self.closed:
                return []
            answers: list[tuple[IP_endpoint, bytes]] = []
            rl, _, _ = select([self.socket], [], [], 0)
            while len(rl) > 0:
                try:
                    data, address = self.socket.recvfrom(BUFSIZE)
                    address = get_canonical_endpoint(address, self.socket.family)
                    answer = interpret_answer_packet(data)
                    if answer is not None and address is not None:
                        answers.append(answer)
                except:
                    pass
                rl, _, _ = select([self.socket], [], [], 0)
            return answers
    
    def send_request(self):
        with self.lock:
            if self.closed:
                return
            request = create_request_packet()
            self.socket.sendto(request, self.multicast_endpoint)

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            self.socket.close()