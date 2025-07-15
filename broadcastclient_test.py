from broadcastclient import BroadcastClient
from socketcommon import get_lan_endpoint, get_loopback_endpoint
from threading import Thread
import traceback
from iptools import string_to_endpoint, endpoint_to_string
from sys import argv


def main():
    if len(argv) < 2:
        print("usage: python broadcastclient_test.py multicast_address:port")
        return
    address = string_to_endpoint(argv[1])
    if address is None:
        print("invalid address")
        return
    
    client = BroadcastClient(address, 0)
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


    def tick():
        while not client.is_closed():
            new_servers = client.tick()
            if len(new_servers) > 0:
                print('neew servers')
            for endpoint, data in new_servers:
                print(f"server found at {endpoint}: {data}")


    
    tick_thread = Thread(target=tick)
    tick_thread.start()

    try:
        while True:
            if client.closed:
                break
            text = input("")
            if text == "quit":
                client.close()
            elif text == "request":
                client.send_request()
    except BaseException:
        print(f"\nException in main loop: {traceback.format_exc()}")
        client.close()
    print("closing program...")
        
    


if __name__ == "__main__":
    main()