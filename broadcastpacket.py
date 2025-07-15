from iptools import IP_endpoint, PORT, ADDRESS, get_endpoint_family, address_to_bytes, bytes_to_address
from socket import AF_INET, AF_INET6

REQUEST_START = b'REQUEST.'
ANSWER_START = b'ANSW.'

def create_request_packet() -> bytes:
    return REQUEST_START

def is_request_packet(packet: bytes) -> bool:
    return packet == REQUEST_START

def create_answer_packet(endpoint: IP_endpoint, data: bytes) -> bytes:
    start = ANSWER_START
    family = get_endpoint_family(endpoint)
    ip_version = 4 if family == AF_INET else 6
    ip_version_bytes = ip_version.to_bytes(1, 'big')
    port = endpoint[PORT]
    port_bytes = port.to_bytes(2, 'big')
    address = endpoint[ADDRESS]
    address_bytes = address_to_bytes(address, family)
    return start + ip_version_bytes + port_bytes + address_bytes + data

def interpret_answer_packet(packet: bytes) -> tuple[IP_endpoint, bytes] | None:
    if not packet.startswith(ANSWER_START):
        return None
    packet = packet.removeprefix(ANSWER_START)
    if len(packet) < 3:
        return None
    ip_version = packet[0]
    family = AF_INET if ip_version == 4 else AF_INET6
    port = int.from_bytes(packet[1:3], 'big')
    packet = packet[3:]
    if (family == AF_INET and len(packet) < 4) or (family == AF_INET6 and len(packet) < 16):
        return None
    address_bytes = packet[:4] if family == AF_INET else packet[:16]
    address = bytes_to_address(address_bytes, family)
    data = packet[4:] if family == AF_INET else packet[16:]
    ip_endpoint = (address, port) if family == AF_INET else (address, port, 0, 0)
    return (ip_endpoint, data)