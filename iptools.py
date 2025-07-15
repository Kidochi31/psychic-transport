from socket import AddressFamily, AF_INET, AF_INET6, getaddrinfo, socket, inet_pton, inet_ntop
from ipaddress import ip_address
from typing import Union


IPv4_endpoint = tuple[str, int]
IPv6_endpoint = tuple[str, int, int, int]

ADDRESS = 0
PORT = 1
FLOWINFO = 2
SCOPEID = 3

IP_endpoint = Union[IPv4_endpoint,IPv6_endpoint]
unresolved_endpoint = tuple[str, int]


def get_endpoint_family(endpoint: IP_endpoint) -> AddressFamily:
    if len(endpoint) == 2:
        return AF_INET
    if len(endpoint) == 4:
        return AF_INET6
    return AF_INET6

def ipv4_to_canonical_ipv6(endpoint: IPv4_endpoint) -> IPv6_endpoint:
    addr_str = "::ffff:"+endpoint[ADDRESS]
    ip = ip_address(addr_str)
    return (ip.compressed, endpoint[PORT], 0, 0)

def ipv6_to_ipv4(endpoint: IPv6_endpoint) -> IPv4_endpoint | None:
    ip = ip_address(endpoint[ADDRESS]).ipv4_mapped # type: ignore
    if ip is None:
        return None
    return (ip.compressed, endpoint[PORT]) # type: ignore

def ipv6_to_canonical_ipv6(endpoint: IPv6_endpoint) -> IPv6_endpoint:
    ip = ip_address(endpoint[ADDRESS])
    return (ip.compressed, endpoint[PORT], endpoint[FLOWINFO], endpoint[SCOPEID])

def get_canonical_ipv6(endpoint: IP_endpoint) -> IPv6_endpoint:
    family = get_endpoint_family(endpoint)
    if family == AF_INET: # ipv4
        return ipv4_to_canonical_ipv6(endpoint) # type: ignore
    else: # ipv6
        return ipv6_to_canonical_ipv6(endpoint) # type: ignore

def get_ipv4(endpoint: IP_endpoint) -> IPv4_endpoint | None:
    family = get_endpoint_family(endpoint)
    if family == AF_INET: # ipv4
        return endpoint # type: ignore
    else: # ipv4
        return ipv6_to_ipv4(endpoint) # type: ignore
    
def get_canonical_endpoint(endpoint: IP_endpoint, family: AddressFamily) -> IP_endpoint | None:
    if family == AF_INET: # ipv4
        return get_ipv4(endpoint)
    else: # ipv6
        return get_canonical_ipv6(endpoint)

def resolve_to_canonical_ipv6(endpoint: unresolved_endpoint) -> IPv6_endpoint | None:
    try:
        address_ipv6:IPv6_endpoint = getaddrinfo(endpoint[ADDRESS], endpoint[PORT], family=AF_INET6)[0][-1] # type: ignore
        return ipv6_to_canonical_ipv6(address_ipv6)
    except Exception:
        pass
    try:
        address_ipv4:IPv4_endpoint = getaddrinfo(endpoint[ADDRESS], endpoint[PORT], family=AF_INET)[0][-1] # type: ignore
        return ipv4_to_canonical_ipv6(address_ipv4)
    except Exception:
        pass
    return None

def resolve_to_ipv4(endpoint: unresolved_endpoint) -> IPv4_endpoint | None:
    try:
        address_ipv4:IPv4_endpoint = getaddrinfo(endpoint[ADDRESS], endpoint[PORT], family=AF_INET)[0][-1] # type: ignore
        return address_ipv4
    except Exception:
        pass
    return None

def resolve_to_canonical_endpoint(endpoint: unresolved_endpoint, family: AddressFamily) -> IP_endpoint | None:
    if family == AF_INET: # ipv4
        return resolve_to_ipv4(endpoint)
    else: # ipv6
        return resolve_to_canonical_ipv6(endpoint)

def get_canonical_local_endpoint(socket: socket) -> IP_endpoint:
    return get_canonical_endpoint(socket.getsockname(), socket.family) # type: ignore

def get_canonical_remote_endpoint(socket: socket) -> IP_endpoint:
    return get_canonical_endpoint(socket.getpeername(), socket.family) # type: ignore

def get_canonical_endpoint_with_port(endpoint: IP_endpoint, port: int, family: AddressFamily) -> IP_endpoint | None:
    if len(endpoint) == 2:
        endpoint = (endpoint[0], port)
    else:
        endpoint = (endpoint[0], port, endpoint[2], endpoint[3])
    return get_canonical_endpoint(endpoint, family)

def endpoint_to_string(endpoint: IP_endpoint) -> str:
    if len(endpoint) == 2:
        return f"{endpoint[ADDRESS]}:{endpoint[PORT]}"
    else:
        return f"[{endpoint[ADDRESS]}]:{endpoint[PORT]}"

def string_to_endpoint(text: str) -> IP_endpoint | None:
    text = text.strip()
    if len(text) == 0:
        return None
    if text[0] == "[":
        # ipv6
        text = text[1:]
        split = text.split("]:", maxsplit=1)
        if len(split) < 2:
            return None
        address, port = split
        if not port.isdigit():
            return None
        port = int(port)
        return (address, port, 0, 0)
    else:
        # ipv4
        split = text.split(":", maxsplit=1)
        if len(split) < 2:
            return None
        address, port = split
        if not port.isdigit():
            return None
        port = int(port)
        return (address, port)
    
def address_to_bytes(address: str, family: AddressFamily) -> bytes:
    return inet_pton(family, address)

def bytes_to_address(address: bytes, family: AddressFamily) -> str:
    return inet_ntop(family, address)