from connection import Connection
from parallelstun import ParallelStun
from socket import socket, AddressFamily, AF_INET
from socketcommon import BUFSIZE, create_ordinary_udp_socket
from iptools import IP_endpoint, get_canonical_endpoint, get_canonical_local_endpoint
from time import perf_counter_ns
from select import select
from packet import PacketType, interpret_packet, create_accept_packet
from threading import Lock
from holepuncher import HolePuncher


class PsychicServer:
    def __init__(self, port: int = 0, family: AddressFamily = AF_INET, hole_punch_timeout: int = 3_000_000_000,  ack_delay_ns: int = 500_000_000):
        self.socket: socket = create_ordinary_udp_socket(port, family)
        self.client_endpoints: list[IP_endpoint] = []
        self.connections: list[Connection] = []
        self.hole_puncher: HolePuncher = HolePuncher(hole_punch_timeout, 5)
        self.stun: ParallelStun | None = None
        self.ack_delay_ns: int = ack_delay_ns

        self.new_connections: list[tuple[IP_endpoint, int]] = [] # client, convid
        self.disconnections: list[IP_endpoint] = []

        self.lock: Lock = Lock()
        self.closed = False
    
    def get_clients(self) -> list[IP_endpoint]:
        with self.lock:
            if self.closed:
                return []
            return self.client_endpoints.copy()

    def get_rtt(self, client: IP_endpoint) -> float | None:
        with self.lock:
            if self.closed:
                return None
            endpoint = get_canonical_endpoint(client, self.socket.family)
            if endpoint is None or endpoint not in self.client_endpoints:
                return None
            index = self.client_endpoints.index(endpoint)
            return self.connections[index].get_rtt()

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

    def stop_hole_punch(self, target: IP_endpoint):
        with self.lock:
            if self.closed:
                return
            endpoint = get_canonical_endpoint(target, self.socket.family)
            if endpoint is None:
                return
            self.hole_puncher.stop_hole_punch(endpoint)

    def get_hole_punch_fails(self) -> list[IP_endpoint]:
        with self.lock:
            if self.closed:
                return []
            return self.hole_puncher.get_fails()

    def hole_punch(self, target: IP_endpoint):
        with self.lock:
            if self.closed:
                return
            endpoint = get_canonical_endpoint(target, self.socket.family)
            if endpoint is None or endpoint in self.client_endpoints:
                return
            self.hole_puncher.hole_punch(endpoint)

    def disconnect(self, client: IP_endpoint):
        with self.lock:
            if self.closed:
                return
            endpoint = get_canonical_endpoint(client, self.socket.family)
            if endpoint is None or endpoint not in self.client_endpoints:
                return
            self._disconnect(endpoint)
    
    def _disconnect(self, client: IP_endpoint):
        index = self.client_endpoints.index(client)
        self.client_endpoints.pop(index)
        self.connections.pop(index)
        self.disconnections.append(client)
    
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

    def _manage_new_client(self, data: bytes, address: IP_endpoint):
        result = interpret_packet(data)
        if result is None:
            return
        if result[0] == PacketType.REQUEST:
            convid = result[1]
            
            new_connection = Connection(convid, perf_counter_ns(), 1_000_000_000, self.ack_delay_ns)
            self.client_endpoints.append(address)
            self.connections.append(new_connection)
            self.new_connections.append((address, convid))
            self.hole_puncher.stop_hole_punch(address)

    def _report_receive(self, data: bytes, address: IP_endpoint):
        if self.stun is not None and address == self.stun.get_current_stun_server():
            self.stun.report_receive(data)
            return
        if address in self.client_endpoints:
            index = self.client_endpoints.index(address)
            self.connections[index].report_receive(data)
            return
        # packet from somewhere else -> check if new connection
        self._manage_new_client(data, address)

    def _tick_all(self) -> list[tuple[bytes, IP_endpoint]]:
        send_data: list[tuple[bytes, IP_endpoint]] = []
        if self.stun is not None and self.stun.stunning:
            stun_data = self.stun.tick(perf_counter_ns())
            server = self.stun.get_current_stun_server()
            if server is not None:
                send_data.extend([(data, server) for data in stun_data])
        # send accept data for any new connections
        send_data.extend([(create_accept_packet(convid), endpoint) for endpoint, convid in self.new_connections])
        

        # tick all connections and get data to send
        remove_connections: list[IP_endpoint] = []
        for i, connection in enumerate(self.connections):
            send_data.extend([(data, self.client_endpoints[i]) for data in connection.tick(perf_counter_ns())])
            if not connection.is_connected():
                remove_connections.append(self.client_endpoints[i])
        # remove any endpoints that are disconnected
        for endpoint in remove_connections:
            self._disconnect(endpoint)

        # tick the holepuncher
        send_data.extend(self.hole_puncher.tick(perf_counter_ns()))
        
        return send_data

    def tick(self) -> tuple[list[IP_endpoint], list[IP_endpoint]]: # returns new connections and disconnections
        with self.lock:
            if self.closed:
                return ([], [])
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
            new_connections = [endpoint for endpoint, _ in self.new_connections]
            disconnections = self.disconnections.copy()
            self.new_connections.clear()
            self.disconnections.clear()
            return (new_connections, disconnections)
        
    def send(self, message: bytes, destination: IP_endpoint):
        with self.lock:
            if self.closed:
                return
            endpoint = get_canonical_endpoint(destination, self.socket.family)
            if endpoint is None or endpoint not in self.client_endpoints:
                return
            index = self.client_endpoints.index(endpoint)
            self.connections[index].send(message)
    
    def receive(self, source: IP_endpoint) -> tuple[int, bytes] | None:
        with self.lock:
            if self.closed:
                return
            endpoint = get_canonical_endpoint(source, self.socket.family)
            if endpoint is None or endpoint not in self.client_endpoints:
                return
            index = self.client_endpoints.index(endpoint)
            return self.connections[index].receive()
    
    def is_closed(self):
        return self.closed

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            self.socket.close()
            self.client_endpoints.clear()
            self.connections.clear()
            self.stun = None
            self.new_connections.clear()
            self.disconnections.clear()