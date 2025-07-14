from socket import socket, timeout
from random import randbytes
from ipaddress import IPv4Address, IPv6Address
from iptools import IP_endpoint, unresolved_endpoint
import iptools

# Send a STUN message to a server, with optional extra data
def send_stun_request(sock: socket, addr: IP_endpoint) -> bytes:
    trans_id = randbytes(16)
    message_start = b'\x00\x01\x00\x00' # x0001 is bind msg rqst; 0000 is message length
    sock.sendto(message_start + trans_id, addr)
    return trans_id

def create_stun_request_and_trans_id() -> tuple[bytes, bytes]:
    trans_id = randbytes(16)
    message_start = b'\x00\x01\x00\x00' # x0001 is bind msg rqst; 0000 is message length
    message = message_start + trans_id
    return (message, trans_id)

def get_int(bytes: bytes) -> int:
    return int.from_bytes(bytes, byteorder="big")

def stun_response_valid(bytes: bytes, transaction_id: bytes) -> bool:
    # Too short, not a valid message
    if len(bytes) < 20:
        return False
    received_transaction_id = bytes[4:20]
    return received_transaction_id == transaction_id

# returns the external ip address and port number of the socket
def get_stun_response(sock: socket, addr: IP_endpoint, max_timeouts: int) -> IP_endpoint:
    timeouts = 0
    while True:
        try:
            transaction_id = send_stun_request(sock, addr)
            data, endpoint = sock.recvfrom(2048)
            endpoint = iptools.get_canonical_endpoint(endpoint, sock.family)
            if endpoint != addr: # ignore all other messages
                continue
            result = interpret_stun_response(data, transaction_id)
            if result is None:
                raise timeout # timeout if invalid response
            else:
                return result
            
        except timeout:
            timeouts += 1
            if timeouts >= max_timeouts:
                raise timeout
            continue
    
def interpret_stun_response(response: bytes, transaction_id: bytes) -> IP_endpoint | None:
    if not stun_response_valid(response, transaction_id):
        return None
    attributes = response[20:]
    while len(attributes) > 0:
        type, length = attributes[0:2], get_int(attributes[2:4])
        value = attributes[4:4+length]

        attributes = attributes[4+length:]
        
        if type == b'\x00\x01': # MAPPED-ADDRESS
            family = value[1]
            extPort = get_int(value[2:4])
            if family == 0x01:
                extAddress = IPv4Address(value[4:8]).compressed
                return (extAddress, extPort)
            else: #0x02
                extAddress = IPv6Address(value[4:20]).compressed
                return (extAddress, extPort, 0, 0)
    return None

# Get the network topology, external IP, and external port
def get_ip_info(sock: socket, stun_hosts: list[unresolved_endpoint], max_timeouts: int =5) -> IP_endpoint | None: 
    old_timeout = sock.gettimeout()
    sock.settimeout(0.5)
    response = None

    for stun_addr in stun_hosts:
        try:
            endpoint = iptools.resolve_to_canonical_endpoint(stun_addr, sock.family)
            if endpoint is None:
                continue
            response = get_stun_response(sock, endpoint, max_timeouts)
            break
        except Exception:  # host not found, or timeout
            continue
    
    sock.settimeout(old_timeout)
    return response

