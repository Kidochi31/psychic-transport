from psychicclient import PsychicClient
from socketcommon import get_lan_endpoint, get_loopback_endpoint
from threading import Thread
import traceback
from iptools import string_to_endpoint, endpoint_to_string

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
    print(f"LAN: {endpoint_to_string(lan_endpoint) if lan_endpoint is not None else "None"}")
    print(f"Loopback: {endpoint_to_string(loopback_endpoint) if loopback_endpoint is not None else "None"}")

    def tick():
        while not client.closed:
            client.tick()
            while recv:= client.receive():
                seg, message = recv
                print(f"{seg}: {message.decode()}")

    
    tick_thread = Thread(target=tick)
    tick_thread.start()

    try:
        while True:
            if client.closed:
                break
            text = input("")
            if text == "quit":
                client.close()
            elif text.startswith("connect "):
                try:
                    text = text.removeprefix("connect ")
                    endpoint = string_to_endpoint(text)
                    if endpoint is not None:
                        print("connecting...")
                        client.connect(endpoint)
                except:
                    print("failed to connect")
            else:
                client.send(text.encode())
    except BaseException:
        print(f"\nException in main loop: {traceback.format_exc()}")
        client.close()
    print("closing program...")
        
    


if __name__ == "__main__":
    main()