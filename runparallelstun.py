from sys import argv
from parallelstun import ParallelStun
from iptools import *
from socketcommon import *
from select import select

STUN_SERVERS = [('stun.ekiga.net', 3478), ('stun.ideasip.com', 3478), ('stun.voiparound.com', 3478),
                ('stun.voipbuster.com', 3478), ('stun.voipstunt.com', 3478), ('stun.voxgratia.org', 3478)]

def main():
    if len(argv) < 2 or len(argv) > 3:
        print("Usage: python runstun.py port [server:port]")
        exit()
    
    port = int(argv[1])
    servers = STUN_SERVERS
    if len(argv) >= 3:
        host_name, host_port = argv[2].split(":")
        host_port = int(host_port)
        servers = [(host_name, host_port)] + servers
    
    sock = create_ordinary_udp_socket(port, AF_INET)

    stun = ParallelStun(1, 2, sock)

    if not stun.initiate_request(servers):
        print("could not initiate request")
        print(f"Failed servers: {stun.failed_servers}")
        return
    
    while stun.stun_in_progress():
        data: bytes | None = None
        address: IP_endpoint | None = None
        rl, _, _ = select([sock], [], [], 0)
        if len(rl) > 0:
            data, address = sock.recvfrom(2000)
            if address is None:
                data = None
            else:
                address = get_canonical_endpoint(address, sock.family)
                if address != stun.get_current_stun_server():
                    data = None
        result = stun.tick(data)
        if isinstance(result, tuple):
            print(result)
        else:
            if not result:
                print("stun failed to find a result")
    print(f"Failed servers: {stun.get_failed_servers()}")



if __name__ == "__main__":
    main()