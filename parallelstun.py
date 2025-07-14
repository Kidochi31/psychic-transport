from iptools import IP_endpoint
from stun import create_stun_request_and_trans_id, interpret_stun_response

class ParallelStun:
    # fields
    # ------
    # socket: socket - socket used to send messages
    # timeout: float - the length of time in seconds to wait for a response from a stun server
    # max_timeouts: int - the number of timeouts allowed per server

    # stun_hosts: list[unresolved_endpoint] - the current list of stun hosts this is requesting from
    # failed_servers: list[unresolved_endpoint] - the endpoints which could not be successfully used
    # stun_server: tuple[IP_endpoint, unresolved_endpoint] | None - the current stun server this is requesting from
    # request_info: tuple[bytes, int] | None - the transaction id for the current request and the time when it was sent
    # num_timeouts: int - the number of timeouts that have occurred
    
    def __init__(self, timeout: int, max_timeouts: int, stun_hosts: list[IP_endpoint]):
        self.timeout : int = timeout
        self.max_timeouts: int = max_timeouts

        self.stun_hosts: list[IP_endpoint] = stun_hosts
        self.stun_info: tuple[IP_endpoint, bytes, int] | None = None #server, transaction_id, and time request was sent
        self.num_timeouts: int = 0
        self.stun_result: IP_endpoint | None = None

        self.stunning = True

    def get_stun_result(self) -> IP_endpoint | None:
        return self.stun_result

    def get_current_stun_server(self) -> IP_endpoint | None:
        return self.stun_info[0] if self.stun_info is not None else None
    
    def stun_in_progress(self) -> bool:
        return self.stunning
    
    def report_receive(self, received_data_from_server: bytes):
        if self.stun_info is None:
            return
        result = interpret_stun_response(received_data_from_server, self.stun_info[1])
        if result is not None:
            self._reset_request_variables()
            self.stun_result = result
            self.stunning = False
            return

    def tick(self, time: int) -> list[bytes]:
        # returns data to send
        if not self.stunning:
            return []
        
        if self.stun_info is None:
            return self._initiate_request_from_first_host(time)
        
        if time < self.stun_info[2] + self.timeout:
            return [] # no timeout just yet

        self.num_timeouts += 1
        if self.num_timeouts >= self.max_timeouts:
            return self._initiate_request_from_first_host(time)
        else:
            return self._get_stun_request_to_server(self.stun_info[0], time)

    def _reset_request_variables(self):
        self.stun_info = None
        self.num_timeouts = 0

    def _initiate_request_from_first_host(self, time: int) -> list[bytes]:
        while len(self.stun_hosts) > 0:
            self._reset_request_variables()
            stun_host = self.stun_hosts[0]
            self.stun_hosts = self.stun_hosts[1:]
            # successfully initiated request
            return self._get_stun_request_to_server(stun_host, time)
        # reached end -> no more servers available
        self._reset_request_variables()
        self.stunning = False
        return []

    def _get_stun_request_to_server(self, stun_server: IP_endpoint, time: int) -> list[bytes]:
        request, trans_id = create_stun_request_and_trans_id()
        self.stun_info = (stun_server, trans_id, time)
        return [request]
