from socket import socket, AddressFamily, SHUT_RDWR, SOCK_STREAM, AF_INET6, IPPROTO_IPV6, IPV6_V6ONLY
import traceback
from threading import Thread, Lock
from common import make_socket_reusable, debug_print
from iptools import IP_endpoint

HOLEPUNCH_TIMEOUT = 10

class HolePuncher:
    # local_endpoint: IP_endpoint - the endpoint the listener is bound to
    # family: AddressFamily
    # lock: Lock
    # hole_punchers: Dictionary[IP_endpoint, socket] - the dictionary of connecting TCP sockets and associated thread to the remote endpoint
    # hole_punch_fails: list[IP_endpoint] - a list of remote endpoints that could not be connected to (and have yet to be managed)
    # hole_punch_successes: list[socket] - a list of sockets that have succeeded in connecting (and have yet to be managed)
    
    def __init__(self, local_endpoint: IP_endpoint, family: AddressFamily):
        self.local_endpoint = local_endpoint
        self.family = family
        self.lock = Lock()
        self.hole_punchers:dict[IP_endpoint, socket] = {} 
        self.fails:set[IP_endpoint] = set()
        self.successes:set[socket] = set()

    def _on_success(self, endpoint: IP_endpoint):
        with self.lock:
            if endpoint in self.hole_punchers.keys():
                socket = self.hole_punchers.pop(endpoint)
                self.successes.add(socket)
    
    def _on_fail(self, endpoint: IP_endpoint):
        with self.lock:
            if endpoint in self.hole_punchers.keys():
                hp_socket = self.hole_punchers.pop(endpoint)
                self.try_close(hp_socket, "Closing Hole Puncher Exception")
                self.fails.add(endpoint)
    
    def remove_hole_puncher(self, endpoint: IP_endpoint):
        with self.lock:
            if endpoint in self.hole_punchers.keys():
                hp_socket = self.hole_punchers.pop(endpoint)
                self.try_close(hp_socket, "Closing Hole Puncher Exception")
            if endpoint in self.fails:
                self.fails.remove(endpoint)

    def hole_punch(self, endpoint: IP_endpoint, timeout: float | None):
        with self.lock:
            if endpoint in self.hole_punchers:
                debug_print(f"already hole puncher!")
                return
            if endpoint in self.fails:
                self.fails.remove(endpoint)
            try:
                hp_socket = self.create_hole_puncher_socket(self.local_endpoint, self.family)
            except Exception:
                self.fails.add(endpoint)
                return
            self.hole_punchers[endpoint] = hp_socket
            hp_thread = Thread(target=self.hole_punch_thread, args=(hp_socket, endpoint, timeout))
            hp_thread.start()
    
    def take_successes(self) -> list[socket]:
        with self.lock:
            successes = list(self.successes)
            self.successes.clear()
            return successes
        
    def take_fails(self) -> list[IP_endpoint]:
        with self.lock:
            fails = list(self.fails)
            self.fails.clear()
            return fails
        
    def clear(self):
        with self.lock:
            for endpoint in list(self.hole_punchers.keys()):
                hp_socket = self.hole_punchers.pop(endpoint)
                self.try_close(hp_socket, "Closing Hole Puncher Exception")
            for socket in self.successes:
                self.try_close(socket, "Closing Hole Puncher Exception", shutdown=True)
            self.hole_punchers.clear()
            self.successes.clear()
            self.fails.clear()

    def try_close(self, socket: socket, exception_log_name: str, shutdown:bool=False):
            if shutdown:
                try:
                    socket.shutdown(SHUT_RDWR)
                except Exception:
                    debug_print(f"At shutdown {exception_log_name}: {traceback.format_exc()}")
            try:
                socket.close()
            except Exception:
                debug_print(f"At close {exception_log_name}: {traceback.format_exc()}")

    def create_hole_puncher_socket(self, local_endpoint: IP_endpoint, family: AddressFamily) -> socket:
        hp_socket = socket(family, SOCK_STREAM)
        if family == AF_INET6:
            hp_socket.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 0)
        make_socket_reusable(hp_socket)
        hp_socket.bind(local_endpoint) # bind the socket
        return hp_socket

    def hole_punch_thread(self, hp_socket: socket, endpoint: IP_endpoint, timeout: float | None):
        try:
            if timeout is None or timeout <= 0:
                timeout = None
            hp_socket.settimeout(20)
            print("starting hole punch")
            hp_socket.connect(endpoint)
            print("success")
            hp_socket.settimeout(None)
            self._on_success(endpoint)
        except Exception:
            debug_print(f"Connect Exception: {traceback.format_exc()}")
            self._on_fail(endpoint)
        debug_print("stopping hole punch thread")