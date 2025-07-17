from broadcastclient import BroadcastClient
from socketcommon import get_lan_endpoint, get_loopback_endpoint
from threading import Thread
import traceback
from iptools import string_to_endpoint, endpoint_to_string, IP_endpoint
from sys import argv
from psychicclient import PsychicClient


def main():
    if len(argv) < 2:
        print("usage: python broadcastclient_test.py multicast_address:port")
        return
    address = string_to_endpoint(argv[1])
    if address is None:
        print("invalid address")
        return
    
    potential_servers: dict[str, IP_endpoint] = {}
    next_server_char: str = "a"

    client = PsychicClient(0, ack_delay_ns=0)
    local_endpoint = client.get_local_endpoint()
    if local_endpoint is None:
        return
    family = client.get_family()
    if family is None:
        return
    lan_endpoint = get_lan_endpoint(family, local_endpoint)
    loopback_endpoint = get_loopback_endpoint(family, local_endpoint)
    print(f"LAN: {endpoint_to_string(lan_endpoint) if lan_endpoint is not None else 'None' }")
    print(f"Loopback: {endpoint_to_string(loopback_endpoint) if loopback_endpoint is not None else 'None' }")
    
    broadcast = BroadcastClient(address, 0)


    def tick():
        nonlocal next_server_char

        connected = client.is_connected()
        connecting = client.connecting()
        while not client.closed:
            client.tick()
            while recv:= client.receive():
                seg, message = recv
                print(f"{seg}: {message.decode()}")
            if client.is_connected() and not connected:
                connected = True
                print("connected!")
            elif not client.is_connected() and connected:
                connected = False
                print("disconnected!")
            if client.connecting() and not connecting:
                connecting = True
            elif not client.connecting() and connecting:
                connecting = False
                if not client.is_connected():
                    print("failed to connect!")
            
            if not broadcast.is_closed():
                new_servers = broadcast.tick()
                for endpoint, data in new_servers:
                    print(f"server ({next_server_char}) found at {endpoint_to_string(endpoint)} with data: {data}")
                    potential_servers[next_server_char] = endpoint
                    next_server_char = chr(ord(next_server_char) + 1)

    tick_thread = Thread(target=tick)
    tick_thread.start()

    try:
        while True:
            if client.is_closed():
                break
            text = input("")
            if text == "quit":
                client.close()
                broadcast.close()
            elif text.startswith("connect "):
                text = text.removeprefix("connect ")
                if text in potential_servers:
                    print(f"connecting to {endpoint_to_string(potential_servers[text])}")
                    connect_result = client.connect(potential_servers[text])
                    if not connect_result:
                        print(f"could not connect to {endpoint_to_string(potential_servers[text])}")
                else:
                    print("server could not be found")
            elif text == "dc":
                client.disconnect()
            elif text == "request":
                potential_servers.clear()
                next_server_char = "a"
                broadcast.send_request()
            else:
                client.send(text.encode())
    except BaseException:
        print(f"\nException in main loop: {traceback.format_exc()}")
        client.close()
    print("closing program...")
        
    


if __name__ == "__main__":
    main()