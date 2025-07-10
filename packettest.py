from packet import PacketType, create_packet, interpret_packet
from random import randint
from typing import Any
from collections.abc import Callable

def test_request() -> bool:
    random_names = ["alice", "bob", "charlie", "david eric III", "archduke fredrick ferdinand II of austria"]
    
    type = PacketType.REQUEST
    vers = randint(0, 255)
    version = randint(0, 65535)
    name = random_names[randint(0, len(random_names) - 1)]
    data = b"request packet"

    packet_data: dict[str, Any] = {"vers": vers, "version": version, "name": name, "data": data}
    return test_packet(packet_data, type)

def test_accept() -> bool:
    type = PacketType.ACCEPT
    vers = randint(0, 255)
    version = randint(0, 65535)
    timestep0 = randint(0, 2 ** 64 - 1)
    lentimestep = randint(0, 65535)
    timestamp = randint(0, 2**32 - 1)
    data = b"accept packet"

    packet_data: dict[str, Any] = {"vers": vers, "version": version, "timestep0": timestep0, "lentimestep": lentimestep, "timestamp": timestamp, "data": data}
    return test_packet(packet_data, type)

def test_data() -> bool:
    type = PacketType.DATA
    timestep = randint(0, 2 ** 24 -1)
    timestamp = randint(0, 65535)
    delay = randint(- 2 ** 15, 2 ** 15 - 1)
    seg = randint(0, 65535)
    totalsegs = randint(0, 65535)
    data = b"data packet"

    packet_data: dict[str, Any] = {"timestep": timestep, "timestamp": timestamp, "delay": delay, "seg": seg, "totalsegs": totalsegs, "data": data}
    return test_packet(packet_data, type)

def test_nak() -> bool:
    type = PacketType.NAK
    timestep = randint(0, 2 ** 24 -1)
    num_segs = randint(0, 20)
    segs: list[int] = []
    for _ in range(num_segs):
        segs.append(randint(0, 65535))

    packet_data: dict[str, Any] = {"timestep": timestep, "segs": segs}
    return test_packet(packet_data, type)

def test_packet(data: dict[str, Any], type: PacketType) -> bool:
    try:
        packet = create_packet(type, data)
        int_type, int_data = interpret_packet(packet)

        try:
            assert data == int_data
            assert type == int_type
            return True
        except:
            print(f"test failed for packet of type {type} (found {int_type})")
            print(f"original packet: {data}")
            print(f"interpreted packet: {int_data}")
            return False
    except:
        return False

def test_number(amount: int, name: str, test: Callable[[], bool]):
    print("")
    print(f"Testing {name}-------------")
    passed = 0
    for _ in range(amount):
        if test():
            passed += 1
    if passed == amount:
        print(f"PASSED ALL {name.upper()} TESTS")
    else:
        fail_rate = 100 - passed / amount * 100
        print(f"FAILED {fail_rate}% OF {name.upper()} TESTS")
    print(f"Finished {name}------------")


def main():
    print("-------------Starting All Packet Tests-------------")
    test_number(100, "Request Packet", test_request)
    test_number(100, "Accept Packet", test_accept)
    test_number(100, "Data Packet", test_data)
    test_number(100, "NAK Packet", test_nak)

    print("")
    print("-------------Finished All Packet Tests-------------")
    



if __name__ == "__main__":
    main()