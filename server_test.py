from psychicserver import PsychicServer
from socketcommon import get_lan_endpoint, get_loopback_endpoint
from threading import Thread, Lock
import traceback
from iptools import IP_endpoint, endpoint_to_string, string_to_endpoint, resolve_to_canonical_endpoint

STUN_SERVERS = [('stun.ekiga.net', 3478), ('stun.ideasip.com', 3478), ('stun.voiparound.com', 3478),
                ('stun.voipbuster.com', 3478), ('stun.voipstunt.com', 3478), ('stun.voxgratia.org', 3478)]

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

    print(f"LAN: {endpoint_to_string(lan_endpoint) if lan_endpoint is not None else 'None'}")
    print(f"Loopback: {endpoint_to_string(loopback_endpoint) if loopback_endpoint is not None else 'None'}")

    stun_hosts: list[IP_endpoint] = []
    for hosts in STUN_SERVERS:
        endpoint = resolve_to_canonical_endpoint(hosts, family)
        if endpoint is not None:
            stun_hosts.append(endpoint)
    server.start_stun(stun_hosts)
    

    def tick():
        stun_in_progress = True
        while not server.closed:
            connections, disconnections = server.tick()
            with clients_lock:
                for client in connections:
                    print(f"new connection from: {client}")
                    clients.append(client)
                for client in disconnections:
                    print(f"disconnected: {client}")
                    clients.remove(client)
                for target in server.get_hole_punch_fails():
                    print(f"hole punch failed: {target}")
                for client in clients:
                    while recv:= server.receive(client):
                        seg, message = recv
                        print(f"from {client}: {seg}: {message.decode()}")
            if not server.stun_in_progress() and stun_in_progress:
                stun_in_progress = False
                stun_result = server.get_stun_result()
                print(f"External: {endpoint_to_string(stun_result) if stun_result is not None else 'None'}")
            if server.stun_in_progress() and not stun_in_progress:
                stun_in_progress = True

    
    tick_thread = Thread(target=tick)
    tick_thread.start()

    try:
        while True:
            if server.closed:
                break
            text = input("")
            if text == "quit":
                server.close()
            elif text == "stun":
                server.start_stun(stun_hosts)
            elif text.startswith("rtt "):
                text = text.removeprefix("rtt ")
                target = string_to_endpoint(text)
                if target is not None:
                    print(server.get_rtt(target))
            elif text.startswith("hp "):
                text = text.removeprefix("hp ")
                target = string_to_endpoint(text)
                if target is not None:
                    server.hole_punch(target)
            elif text.startswith("stophp "):
                text = text.removeprefix("stophp ")
                target = string_to_endpoint(text)
                if target is not None:
                    server.stop_hole_punch(target)
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