from psychicserver import PsychicServer
from socketcommon import get_lan_endpoint, get_loopback_endpoint
from threading import Thread, Lock
import traceback
from iptools import IP_endpoint, endpoint_to_string

def main():
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

    print(f"LAN: {endpoint_to_string(lan_endpoint) if lan_endpoint is not None else "None"}")
    print(f"Loopback: {endpoint_to_string(loopback_endpoint) if loopback_endpoint is not None else "None"}")

    def tick():
        while not server.closed:
            connections, disconnections = server.tick()
            with clients_lock:
                for client in connections:
                    print(f"new connection from: {client}")
                    clients.append(client)
                for client in disconnections:
                    print(f"disconnected: {client}")
                    clients.remove(client)
                for client in clients:
                    while recv:= server.receive(client):
                        seg, message = recv
                        print(f"from {client}: {seg}: {message.decode()}")

    
    tick_thread = Thread(target=tick)
    tick_thread.start()

    try:
        while True:
            if server.closed:
                break
            text = input("")
            if text == "quit":
                server.close()
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