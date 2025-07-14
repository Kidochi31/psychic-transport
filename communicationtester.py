from socket import socket, AF_INET, SOCK_DGRAM
from select import select

show_keep_alive = False

def main():

    s = socket(family=AF_INET, type=SOCK_DGRAM)
    s.bind(('', 0))
    port: int = s.getsockname()[1]
    print(f"name: 127.0.0.1:{port}")

    port1 = input("first port: 127.0.0.1:")
    address1 = "127.0.0.1"
    port1 = int(port1)
    endpoint1 = (address1, port1)

    port2 = input("second port: 127.0.0.1:")
    address2 = "127.0.0.1"
    port2 = int(port2)
    endpoint2 = (address2, port2)

    while True:
        try:
            rlist, _, _ = select([s], [], [], 0)
            if len(rlist) != 0:
                data, client = s.recvfrom(2000)
                if client == endpoint1:
                    s.sendto(data, endpoint2)
                else:
                    s.sendto(data, endpoint1)
                print(data)
        except BaseException:
            break

if __name__ == "__main__":
    main()