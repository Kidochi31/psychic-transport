from socket import socket
from iptools import IP_endpoint, unresolved_endpoint, resolve_to_canonical_endpoint
from time import time_ns
from socketcommon import debug_print
from stun import send_stun_request, interpret_stun_response

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
    
    def __init__(self, timeout: float, max_timeouts: int, socket: socket):
        self.socket:'socket' = socket
        self.timeout : float = timeout
        self.max_timeouts: int = max_timeouts

        self.stun_hosts: list[unresolved_endpoint] = []
        self.failed_servers: list[unresolved_endpoint] = []
        self.stun_server: tuple[IP_endpoint, unresolved_endpoint] | None = None
        self.request_info: tuple[bytes, int] | None = None # transaction_id and time request was sent (ns)
        self.num_timeouts: int = 0

    def get_current_stun_server(self) -> IP_endpoint | None:
        return self.stun_server[0] if self.stun_server is not None else None
    
    def get_failed_servers(self) -> list[unresolved_endpoint]:
        return self.failed_servers
    
    def stun_in_progress(self) -> bool:
        return self.stun_server is not None

    def initiate_request(self, stun_hosts: list[unresolved_endpoint]) -> bool:
        self.failed_servers = []
        self.stun_hosts = stun_hosts
        return self._initiate_request_from_first_host()
       
    def tick(self, received_data_from_server: bytes | None) -> IP_endpoint | bool:
        # received_data_from_server must have been received from the stun_server endpoint or None if no data was received
        if self.stun_server is None or  self.request_info is None:
            return False
        if received_data_from_server is not None:
            result = interpret_stun_response(received_data_from_server, self.request_info[0])
            if result is None:
                debug_print(f'result from {self.stun_server[1]} was invalid: {received_data_from_server}')
                self.num_timeouts += 1
            else:
                self._reset_request_variables()
                return result
        else:
            # no result received
            if time_ns() >= self.request_info[1] + self.timeout * 1_000_000_000:
                debug_print(f'timeout for {self.stun_server[1]}')
                self.num_timeouts += 1
            else:
                return True
        
        if self.num_timeouts >= self.max_timeouts:
            debug_print(f"too many timeouts: {self.stun_server[1]}")
            self.failed_servers.append(self.stun_server[1])
            return self._initiate_request_from_first_host()
        else:
            return self._start_next_stun_request_to_server()

    def _reset_request_variables(self):
        self.stun_server = None
        self.request_info = None
        self.num_timeouts = 0

    def _initiate_request_from_first_host(self) -> bool:
        while len(self.stun_hosts) > 0:
            self._reset_request_variables()
            unresolved_host = self.stun_hosts[0]
            debug_print(f"potential stun server: {unresolved_host}")
            self.stun_hosts = self.stun_hosts[1:]
            stun_server_endpoint = resolve_to_canonical_endpoint(unresolved_host, self.socket.family)
            if stun_server_endpoint is None:
                self.failed_servers.append(unresolved_host)
                debug_print(f"server failed - could not resolve")
                continue
            self.stun_server = (stun_server_endpoint, unresolved_host)
            if not self._start_stun_request_to_server(self.stun_server):
                debug_print(f"server failed - could not send request")
                continue
            # successfully initiated request
            return True
        # reached end -> no more servers available
        self._reset_request_variables()
        return False
    
    def _start_next_stun_request_to_server(self) -> bool:
        if self.stun_server is None:
            return self._initiate_request_from_first_host()
        if not self._start_stun_request_to_server(self.stun_server):
            return self._initiate_request_from_first_host()
        # successfully sent new stun request
        return True

    def _start_stun_request_to_server(self, stun_server: tuple[IP_endpoint, unresolved_endpoint]) -> bool:
        debug_print(f"requesting from {stun_server[1]}")
        try:
            self.request_info = send_stun_request(self.socket, stun_server[0]), time_ns()
            return True
        except:
            self.request_info = None
            self.failed_servers.append(stun_server[1])
            return False
