from clientconnector import ClientConnector
from connection import Connection
from parallelstun import ParallelStun
from socket import socket, AddressFamily, AF_INET
from socketcommon import BUFSIZE, create_ordinary_udp_socket
from iptools import IP_endpoint, get_canonical_endpoint, get_canonical_local_endpoint
from time import perf_counter_ns
from select import select
from threading import Lock



class PsychicClient:
    def __init__(self, port: int = 0, family: AddressFamily = AF_INET, ack_delay_ns: int = 500_000_000):
        self.socket: socket = create_ordinary_udp_socket(port, family)
        self.connector: tuple[ClientConnector, IP_endpoint] | None = None
        self.connection: tuple[Connection, IP_endpoint] | None = None
        self.stun: ParallelStun | None = None
        self.lock: Lock = Lock()
        self.ack_delay_ns: int = ack_delay_ns

        self.closed = False
    
    def get_server(self) -> IP_endpoint | None:
        with self.lock:
            if self.closed or self.connection is None:
                return None
            return self.connection[1]

    def get_rtt(self) -> float | None:
        with self.lock:
            if self.closed or self.connection is None:
                return None
            return self.connection[0].get_rtt()

    def stun_in_progress(self) -> bool:
        with self.lock:
            if self.closed or self.stun is None:
                return False
            return self.stun.stun_in_progress()

    def get_local_endpoint(self) -> IP_endpoint | None:
        with self.lock:
            if self.closed:
                return None
            return get_canonical_local_endpoint(self.socket)
    
    def get_family(self) -> AddressFamily | None:
        with self.lock:
            if self.closed:
                return None
            return self.socket.family

    def connecting(self) -> bool:
        with self.lock:
            if self.connector is None:
                return False
            return not self.connector[0].connect_failed()

    def is_connected(self) -> bool:
        with self.lock:
            if self.connection is None:
                return False
            return self.connection[0].is_connected()
    
    def disconnect(self):
        with self.lock:
            self.connector = None
            self.connection = None

    def connect(self, server: IP_endpoint):
        with self.lock:
            if (self.connection is not None and not self.connection[0].is_connected()) or self.closed:
                return
            self.connector = None
            server_endpoint = get_canonical_endpoint(server, self.socket.family)
            if server_endpoint is None:
                return
            self.connector = (ClientConnector((perf_counter_ns() // 1_000_000) % (2**32), perf_counter_ns(), 5, 500_000_000, 1_000_000_000, self.ack_delay_ns), server_endpoint)
    
    def start_stun(self, servers: list[IP_endpoint]):
        with self.lock:
            if self.closed:
                return
            self.stun = ParallelStun(1_000_000_000, 3, servers)
    
    def get_stun_result(self) -> IP_endpoint | None:
        with self.lock:
            if self.stun is None:
                return None
            return self.stun.get_stun_result()

    def _report_receive(self, data: bytes, address: IP_endpoint):
        if self.connector is not None and address == self.connector[1]:
            self.connector[0].report_receive(data)
            return
        if self.stun is not None and address == self.stun.get_current_stun_server():
            self.stun.report_receive(data)
            return
        if self.connection is not None and address == self.connection[1]:
            self.connection[0].report_receive(data)
            return

    def _tick_all(self) -> list[tuple[bytes, IP_endpoint]]:
        send_data: list[tuple[bytes, IP_endpoint]] = []
        if self.connector is not None:
            send_data.extend([(data, self.connector[1]) for data in self.connector[0].tick(perf_counter_ns())])
            possible_connection = self.connector[0].get_connection_info()
            if possible_connection is not None:
                server = self.connector[1]
                self.connector = None # remove connector
                self.connection = (possible_connection, server)
            elif self.connector[0].connect_failed():
                self.connector = None
        if self.stun is not None and self.stun.stunning:
            stun_data = self.stun.tick(perf_counter_ns())
            server = self.stun.get_current_stun_server()
            if server is not None:
                send_data.extend([(data, server) for data in stun_data])
        if self.connection is not None:
            send_data.extend([(data, self.connection[1]) for data in self.connection[0].tick(perf_counter_ns())])
            if not self.connection[0].is_connected():
                self.connection = None
        return send_data

    def tick(self):
        with self.lock:
            if self.closed:
                return
            # first get all info from the socket
            rl, _, _ = select([self.socket], [], [], 0)
            while len(rl) > 0:
                try:
                    data, address = self.socket.recvfrom(BUFSIZE)
                    address = get_canonical_endpoint(address, self.socket.family)
                    if address is not None:
                        self._report_receive(data, address)
                except:
                    pass
                rl, _, _ = select([self.socket], [], [], 0)
            send_data = self._tick_all()
            for data, destination in send_data:
                try:
                    self.socket.sendto(data, destination)
                except:
                    pass
        
    def send(self, message: bytes):
        with self.lock:
            if self.connection is None:
                return
            self.connection[0].send(message)
    
    def receive(self) -> tuple[int, bytes] | None:
        with self.lock:
            if self.connection is None:
                return None
            return self.connection[0].receive()
    
    def is_closed(self):
        return self.closed

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            self.socket.close()
            self.connector = None
            self.connection = None
            self.stun = None