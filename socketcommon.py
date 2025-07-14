from socket import SOCK_DGRAM, IPPROTO_IPV6, IPV6_V6ONLY, SOL_SOCKET, SO_REUSEADDR, SO_BROADCAST
from iptools import *
from typing import Any

BUFSIZE = 2000
DUMMY_ENDPOINT : unresolved_endpoint  = ("192.0.2.1", 2000)
LAN_BROADCAST_DESTINATION : unresolved_endpoint = ("255.255.255.255", 2000)
IPV6_LOOPBACK : unresolved_endpoint = ("::1", 2000)
IPV4_LOOPBACK : unresolved_endpoint = ("127.0.0.1", 2000)

previous_text = None
previous_printed_text = None
previous_amount = 1

def create_unbound_udp_socket(family: AddressFamily) -> socket:
    udp_socket = socket(family, SOCK_DGRAM)
    if family == AF_INET6:
        udp_socket.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 0)
    make_socket_reusable(udp_socket)
    return udp_socket
    
def create_ordinary_udp_socket(port: int, family: AddressFamily) -> socket:
    udp_socket = create_unbound_udp_socket(family)
    udp_socket.bind(('', port)) # bind the socket
    return udp_socket



def make_socket_reusable(socket: socket):
    socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    try:
        socket.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1) # unix version # type: ignore
    except (AttributeError, NameError):
        pass

def get_lan_endpoint(family: AddressFamily, local_endpoint: IP_endpoint) -> IP_endpoint | None:
    try:
        s = create_unbound_udp_socket(family)
        s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        s.bind(local_endpoint)
        endpoint = resolve_to_canonical_endpoint(LAN_BROADCAST_DESTINATION, family)
        if endpoint is None:
            return None
        s.connect(endpoint)
        return get_canonical_local_endpoint(s)
    except Exception:
        return None
    
def get_loopback_endpoint(family: AddressFamily, local_endpoint: IP_endpoint) -> IP_endpoint | None:
    try:
        s = create_unbound_udp_socket(family)
        s.bind(local_endpoint)
        endpoint = resolve_to_canonical_endpoint(IPV4_LOOPBACK if family == AF_INET else IPV6_LOOPBACK, family)
        if endpoint is None:
            return None
        s.connect(endpoint)
        return get_canonical_local_endpoint(s)
    except Exception:
        return None
    
def debug_print(text: Any):
    global previous_amount
    global previous_text
    global previous_printed_text

    string = str(text)
    if string == previous_text: #type:ignore
        previous_amount += 1
        previous_printed_text = f"{string} x{str(previous_amount)}"
        print(previous_printed_text, end='\r')
    else:
        new_line = '\n'
        print(f"{previous_printed_text + new_line if previous_printed_text is not None else ''}{string}", end='\r')
        previous_amount = 1
        previous_text = string
        previous_printed_text = string