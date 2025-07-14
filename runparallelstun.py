from sys import argv
from parallelstun import ParallelStun
from iptools import *
from socketcommon import *
from select import select
from time import time_ns

STUN_SERVERS = [('stun.ekiga.net', 3478), ('stun.ideasip.com', 3478), ('stun.voiparound.com', 3478),
                ('stun.voipbuster.com', 3478), ('stun.voipstunt.com', 3478), ('stun.voxgratia.org', 3478)]

def main():
    if len(argv) < 2 or len(argv) > 3:
        print("Usage: python runstun.py port [server:port]")
        exit()
    
    port = int(argv[1])
    sock = create_ordinary_udp_socket(port, AF_INET)
    servers = STUN_SERVERS
    if len(argv) >= 3:
        host_name, host_port = argv[2].split(":")
        host_port = int(host_port)
        servers = [(host_name, host_port)] + servers
    stun_hosts: list[IP_endpoint] = []
    for server in servers:
        endpoint = resolve_to_canonical_endpoint(server, sock.family)
        if endpoint is not None:
            stun_hosts.append(endpoint)

    stun = ParallelStun(1 * 1_000_000_000, 2, stun_hosts)
    
    while stun.stun_in_progress():
        rl, _, _ = select([sock], [], [], 0)
        if len(rl) > 0:
            data, address = sock.recvfrom(2000)
            if address is not None and get_canonical_endpoint(address, sock.family) == stun.get_current_stun_server():
                stun.report_receive(data)
        send_data = stun.tick(time_ns())
        server = stun.get_current_stun_server()
        if send_data != [] and server is not None:
            for data in send_data:
                sock.sendto(data, server)
    print(f"Stun result: {stun.get_stun_result()}")



if __name__ == "__main__":
    main()