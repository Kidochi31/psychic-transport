from psychicclient import PsychicClient
from socketcommon import get_lan_endpoint, get_loopback_endpoint
from threading import Thread
import traceback
from iptools import string_to_endpoint, endpoint_to_string, IP_endpoint, resolve_to_canonical_endpoint

STUN_SERVERS = [('stun.ekiga.net', 3478), ('stun.ideasip.com', 3478), ('stun.voiparound.com', 3478),
                ('stun.voipbuster.com', 3478), ('stun.voipstunt.com', 3478), ('stun.voxgratia.org', 3478)]

def main():
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

    stun_hosts: list[IP_endpoint] = []
    for server in STUN_SERVERS:
        endpoint = resolve_to_canonical_endpoint(server, family)
        if endpoint is not None:
            stun_hosts.append(endpoint)
    client.start_stun(stun_hosts)
    

    def tick():
        connected = client.is_connected()
        connecting = client.connecting()
        stun_in_progress = client.stun_in_progress()
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
            if not client.stun_in_progress() and stun_in_progress:
                stun_in_progress = False
                stun_result = client.get_stun_result()
                print(f"External: {endpoint_to_string(stun_result) if stun_result is not None else 'None' }")
            if client.stun_in_progress() and not stun_in_progress:
                stun_in_progress = True


    
    tick_thread = Thread(target=tick)
    tick_thread.start()

    try:
        while True:
            if client.closed:
                break
            text = input("")
            if text == "quit":
                client.close()
            elif text == "stun":
                client.start_stun(stun_hosts)
            elif text.startswith("connect "):
                try:
                    text = text.removeprefix("connect ")
                    endpoint = string_to_endpoint(text)
                    if endpoint is not None:
                        print("connecting...")
                        client.connect(endpoint)
                except:
                    print("failed to connect")
            if text == "dc":
                client.disconnect()
            else:
                client.send(text.encode())
    except BaseException:
        print(f"\nException in main loop: {traceback.format_exc()}")
        client.close()
    print("closing program...")
        
    


if __name__ == "__main__":
    main()