from connection import Connection
from packet import interpret_packet, PacketType, create_request_packet


class ClientConnector:
    def __init__(self, convid: int, time_ms: int, max_timeouts: int, request_timeout_ms: int, init_rtt: int, wait_before_acking: int):
        self.connection_info:  Connection | None= None
        self.convid = convid

        self.time_request_sent: int | None = 0
        self.max_timeouts = max_timeouts
        self.num_timeouts: int = -1
        self.request_timeout_ms = request_timeout_ms

        self.init_rtt: int = init_rtt
        self.wait_before_acking = wait_before_acking

        self.last_tick_time: int = time_ms

        self.failed = False

    def is_connected(self) -> bool:
        return self.connection_info is not None

    def connect_failed(self) -> bool:
        return self.failed
    
    def is_connecting(self) -> bool:
        return not self.is_connected() and not self.connect_failed()
        
    def get_connection_info(self) -> Connection | None:
        return self.connection_info

    def report_receive(self, packet: bytes) -> None:
        if self.is_connected() or self.connect_failed():
            return
        result = interpret_packet(packet)
        if result is not None and result[0] == PacketType.ACCEPT:
            self._manage_accept_packet(result[1])
        # otherwise, ignore packet

    def tick(self, time_ms: int) -> list[bytes]:
        self.last_tick_time = time_ms
        # Ticks the client forward, returns data to be sent
        if self.connection_info is not None or self.failed:
            return []

        # currently waiting for server response
        # check timeout
        
        if self.time_request_sent is None or time_ms >= self.time_request_sent + self.request_timeout_ms:
            self.num_timeouts += 1
            if self.num_timeouts >= self.max_timeouts:
                # timeout
                self.failed = True
                return []
            # resend
            return [self._send_request_to_server(time_ms)]
        # do nothing
        return []

                    
    def _manage_accept_packet(self, convid: int):
        if convid != self.convid:
            self.failed = True
            return
        if self.time_request_sent is None:
            self.failed = True
            return
        self.connection_info = Connection(self.convid, self.last_tick_time, self.init_rtt, self.wait_before_acking)
    
    def _send_request_to_server(self, time: int) -> bytes:
        self.time_request_sent = time
        return create_request_packet(self.convid)