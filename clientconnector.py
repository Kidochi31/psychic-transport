from clientconnection import ClientConnection
from packet import interpret_packet, PacketType, create_request_packet
from time import time_ns

init_request_timeout_ns = 100_000_000

class ClientConnector:
    def __init__(self, version: int, max_timeouts: int, request_timeout_ms: int):
        self.connection_info:  ClientConnection | None= None
        self.version = version

        self.time_request_sent: int = 0
        self.max_timeouts = max_timeouts
        self.num_timeouts = -1
        self.request_timeout_ms = request_timeout_ms


        self.failed = False

    def is_connected(self) -> bool:
        return self.connection_info is not None

    def connect_failed(self) -> bool:
        return self.failed
    
    def is_connecting(self) -> bool:
        return not self.is_connected() and not self.connect_failed()
        
    def get_connection_info(self) -> ClientConnection | None:
        return self.connection_info

    def report_receive(self, packet: bytes) -> None:
        if self.is_connected() or self.connect_failed():
            return
        result = interpret_packet(packet)
        if result is not None and result[0] == PacketType.ACCEPT:
            self._manage_accept_packet(result[1])
        # otherwise, ignore packet

    def tick(self) -> list[bytes]:
        # Ticks the client forward, returns data to be sent
        if self.connection_info is not None or self.failed:
            return []

        # currently waiting for server response
        # check timeout
        
        if self.time_request_sent == 0 or time_ns() >= self.time_request_sent + self.request_timeout_ms * 1_000_000:
            self.num_timeouts += 1
            if self.num_timeouts >= self.max_timeouts:
                # timeout
                self.failed = True
                return []
            # resend
            return [self._send_request_to_server()]
        # do nothing
        return []

                    
    def _manage_accept_packet(self, version: int):
        if version != self.version:
            self.failed = True
            return
        
        rtt_ms = (time_ns() - self.time_request_sent) // 1_000_000
        self.connection_info = ClientConnection(rtt_ms)
    
    def _send_request_to_server(self) -> bytes:
        self.time_request_sent = time_ns()
        return create_request_packet(self.version)