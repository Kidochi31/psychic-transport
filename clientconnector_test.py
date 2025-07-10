from clientconnector import ClientConnector, VERS, VERSION
from clientconnection import ClientConnection
from socketcommon import create_ordinary_udp_socket, get_loopback_endpoint
from socket import AF_INET, socket
from iptools import *
from select import select
from time import time_ns
from packet import *

def create_server() -> tuple[socket, IP_endpoint]:
    server_socket = create_ordinary_udp_socket(2010, AF_INET)
    server_socket_address = get_loopback_endpoint(AF_INET, get_canonical_local_endpoint(server_socket))
    if server_socket_address is None:
        return (server_socket, get_canonical_local_endpoint(server_socket))
    return (server_socket, server_socket_address)

def complete_client_connection(client: ClientConnector, server: socket, server_response: bytes | None, response_delay_ns: int):
    start_time = time_ns()

    while client.is_connecting():
        rl, _, _ = select([server], [], [], 0)
        if len(rl) > 0:
            data = server.recv(2000)
            result = interpret_packet_safe(data)
            print(result)
        
        if time_ns() >= start_time + response_delay_ns:
            client.report_data_received(server_response)
        
        tick_result = client.tick()

        if tick_result == False:
            print("Connection failed")
        if isinstance(tick_result, ClientConnection):
            print("new connection made")
    print(f"Connected: {client.is_connected()}")

def test_connecting_to_nothing():
    print('connecting to silent server')
    server_socket, server_address = create_server()
    client_socket = create_ordinary_udp_socket(2000, AF_INET)
    client = ClientConnector(5, client_socket, "BOB", b'CONNECTING', server_address)

    

    print(f"connection worked: {client.is_connecting()}")

    complete_client_connection(client, server_socket, None, 999999999999999999999)
    
    print("connecting to invalid address")
    client_socket = create_ordinary_udp_socket(2000, AF_INET)
    client = ClientConnector(5, client_socket, "BOB", b'CONNECTING', ('', 0))
    print(f"connection worked: {client.is_connecting()}")
    complete_client_connection(client, server_socket, None, 999999999999999999999)
    
    client_socket = create_ordinary_udp_socket(2000, AF_INET)
    client = ClientConnector(5, client_socket, "BOB", b'CONNECTING', server_address)
    print("connecting to valid address")
    print(f"connection worked: {client.is_connecting()}")

    complete_client_connection(client, server_socket, create_data_packet(100,100,100,10,10,b'hi'), 50_000_000)

    client_socket = create_ordinary_udp_socket(2000, AF_INET)
    client = ClientConnector(5, client_socket, "BOB", b'CONNECTING', server_address)
    print("connecting to valid address but random data sent back")
    print(f"connection worked: {client.is_connecting()}")

    complete_client_connection(client, server_socket, b'HELLO, WORLD!!', 50_000_000)


def test_receiving_accept():
    print('connecting to server that will respond with accept')
    server_socket, server_address = create_server()
    client_socket = create_ordinary_udp_socket(2000, AF_INET)
    client = ClientConnector(5, client_socket, "ALICE", b'HELLO', server_address)

    print(f"connection worked: {client.is_connecting()}")

    complete_client_connection(client, server_socket, create_accept_packet(VERS, VERSION, 100, 10, 1, b'HIIIII FROM SERVER'), 50_000_000)
    
    print(f"connected: {client.is_connected()}")
    print(f"connecting: {client.is_connecting()}")

def test_receiving_accept_wrong_version():
    print('connecting to server that will respond with an accept with the wrong version')
    server_socket, server_address = create_server()
    client_socket = create_ordinary_udp_socket(2000, AF_INET)
    client = ClientConnector(5, client_socket, "ALICE", b'HI', server_address)

    print(f"connection worked: {client.is_connecting()}")
    complete_client_connection(client, server_socket, create_accept_packet(VERS + 1, VERSION, 100, 10, 1, b'HIIIII FROM SERVER'), 50_000_000)
    print(f"connected: {client.is_connected()}")
    print(f"connecting: {client.is_connecting()}")

    client_socket = create_ordinary_udp_socket(2000, AF_INET)
    client = ClientConnector(5, client_socket, "ALICE", b'HI', server_address)
    print(f"connection worked: {client.is_connecting()}")
    complete_client_connection(client, server_socket, create_accept_packet(VERS, VERSION + 1, 100, 10, 1, b'HIIIII FROM SERVER'), 50_000_000)
    print(f"connected: {client.is_connected()}")
    print(f"connecting: {client.is_connecting()}")

    client_socket = create_ordinary_udp_socket(2000, AF_INET)
    client = ClientConnector(5, client_socket, "ALICE", b'HI', server_address)
    print(f"connection worked: {client.is_connecting()}")
    complete_client_connection(client, server_socket, create_accept_packet(VERS + 1, VERSION + 1, 100, 10, 1, b'HIIIII FROM SERVER'), 50_000_000)
    print(f"connected: {client.is_connected()}")
    print(f"connecting: {client.is_connecting()}")

    client_socket = create_ordinary_udp_socket(2000, AF_INET)
    client = ClientConnector(5, client_socket, "ALICE", b'HI', server_address)
    print(f"connection worked: {client.is_connecting()}")
    complete_client_connection(client, server_socket, create_accept_packet(VERS, VERSION, 100, 10, 1, b'HIIIII FROM SERVER'), 50_000_000)
    print(f"connected: {client.is_connected()}")
    print(f"connecting: {client.is_connecting()}")

def main():
    print("----------Starting Client Connection Tests----------")
    test_connecting_to_nothing()
    test_receiving_accept()
    test_receiving_accept_wrong_version()
    print("----------Finished Client Connection Tests----------")

if __name__ == "__main__":
    main()
    