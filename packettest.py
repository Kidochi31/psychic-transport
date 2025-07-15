from packet import PacketType, create_accept_packet, create_data_packet, create_request_packet, interpret_packet
from random import randint
from collections.abc import Callable

def test_request() -> bool:
    type = PacketType.REQUEST
    convid = randint(0, 2**32 - 1)
    packet = create_request_packet(convid)
    return test_packet((type, convid, None), packet)

def test_accept() -> bool:
    type = PacketType.ACCEPT
    convid = randint(0, 2**32 - 1)
    packet = create_accept_packet(convid)
    return test_packet((type, convid, None), packet)

def test_data() -> bool:
    type = PacketType.DATA
    ack = randint(0, 2 ** 24 - 1)
    data_options: list[tuple[int, bytes] | None] = [None, (0, b'HI'), (1, b'HELLO'), (1000, b'HEY'), (2 ** 24 - 1, b'KONNICHIWA')]
    data = data_options[randint(0, len(data_options) - 1)]
    packet = create_data_packet(ack, data)
    return test_packet((type, ack, data), packet)


def test_packet(expected: tuple[PacketType, int, tuple[int, bytes] | None] | None, packet: bytes) -> bool:
    result = interpret_packet(packet)
    return result == expected

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

    print("")
    print("-------------Finished All Packet Tests-------------")
    



if __name__ == "__main__":
    main()