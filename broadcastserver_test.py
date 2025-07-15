from broadcastserver import BroadcastServer
from socketcommon import get_lan_endpoint, get_loopback_endpoint
from threading import Thread
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
    server_endpoint: IP_endpoint = ('0.0.0.0', 0)
    server_data: bytes = b'default server info'

    server = BroadcastServer(address[0], address[1], server_endpoint, server_data)
    local_endpoint = server.get_local_endpoint()
    if local_endpoint is None:
        return
    family = server.get_family()
    if family is None:
        return
    lan_endpoint = get_lan_endpoint(family, local_endpoint)
    loopback_endpoint = get_loopback_endpoint(family, local_endpoint)
    print(f"LAN: {endpoint_to_string(lan_endpoint) if lan_endpoint is not None else 'None' }")
    print(f"Loopback: {endpoint_to_string(loopback_endpoint) if loopback_endpoint is not None else 'None' }")


    def tick():
        while not server.is_closed():
            server.tick()

    
    tick_thread = Thread(target=tick)
    tick_thread.start()

    try:
        while True:
            if server.closed:
                break
            text = input("")
            if text == "quit":
                server.close()
            if text.startswith("server "):
                text = text.removeprefix("server ")
                address = string_to_endpoint(text)
                if address is not None:
                    data = server.get_data()
                    server.set_endpoint_and_data(address, data)
            if text.startswith("data "):
                text = text.removeprefix("data ")
                data = text.encode()
                address = server.get_server_endpoint()
                server.set_endpoint_and_data(address, data)
    except BaseException:
        print(f"\nException in main loop: {traceback.format_exc()}")
        server.close()
    print("closing program...")
        
    


if __name__ == "__main__":
    main()