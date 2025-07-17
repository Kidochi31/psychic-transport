from broadcastserver import BroadcastServer
from psychicserver import PsychicServer
from socketcommon import get_lan_endpoint, get_loopback_endpoint
from threading import Thread, Lock
import traceback
from iptools import string_to_endpoint, endpoint_to_string, IP_endpoint
from sys import argv


def main():
    if len(argv) < 2:
        print("usage: python broadcastserver_test.py multicast_address:port")
        return
    address = string_to_endpoint(argv[1])
    if address is None:
        print("invalid address")
        return
    

    server = PsychicServer(0, ack_delay_ns=0)
    local_endpoint = server.get_local_endpoint()
    if local_endpoint is None:
        return
    family = server.get_family()
    if family is None:
        return
    lan_endpoint = get_lan_endpoint(family, local_endpoint)
    loopback_endpoint = get_loopback_endpoint(family, local_endpoint)
    clients_lock: Lock = Lock()
    clients: list[IP_endpoint] = []

    print(f"LAN: {endpoint_to_string(lan_endpoint) if lan_endpoint is not None else 'None'}")
    print(f"Loopback: {endpoint_to_string(loopback_endpoint) if loopback_endpoint is not None else 'None'}")
    server_endpoint: IP_endpoint = lan_endpoint if lan_endpoint is not None else ('0.0.0.0', 0)
    server_data: bytes = b'default server info'

    broadcast = BroadcastServer(address[0], address[1], server_endpoint, server_data)


    def tick():
        while not server.is_closed():
            connections, disconnections = server.tick()
            with clients_lock:
                for client in connections:
                    print(f"new connection from: {endpoint_to_string(client)}")
                    clients.append(client)
                for client in disconnections:
                    print(f"disconnected: {endpoint_to_string(client)}")
                    clients.remove(client)
                for target in server.get_hole_punch_fails():
                    print(f"hole punch failed: {endpoint_to_string(target)}")
                for client in clients:
                    while recv:= server.receive(client):
                        seg, message = recv
                        print(f"from {endpoint_to_string(client)}: {seg}: {message.decode()}")
            if not broadcast.is_closed():
                broadcast.tick()

    
    tick_thread = Thread(target=tick)
    tick_thread.start()

    try:
        while True:
            if server.closed:
                break
            text = input("")
            if text == "quit":
                server.close()
                broadcast.close()
            elif text.startswith("data "):
                text = text.removeprefix("data ")
                data = text.encode()
                address = broadcast.get_server_endpoint()
                broadcast.set_endpoint_and_data(address, data)
            elif text.startswith("dc "):
                text = text.removeprefix("dc ")
                target = string_to_endpoint(text)
                if target is not None:
                    server.disconnect(target)
            else:
                with clients_lock:
                    for client in clients:
                        server.send(text.encode(), client)
    except BaseException:
        print(f"\nException in main loop: {traceback.format_exc()}")
        server.close()
    print("closing program...")
        
    


if __name__ == "__main__":
    main()