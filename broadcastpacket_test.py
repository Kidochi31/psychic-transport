from broadcastpacket import create_request_packet, create_accept_packet, interpret_accept_packet, is_request_packet
from random import randint
from collections.abc import Callable
from ipaddress import IPv6Address, IPv4Address

alphabet = 'abcdefghijklmnopqrstuvwxyz'

def generate_random_data() -> bytes:
    num_letters = randint(0, 10)
    random_word = [alphabet[randint(0, len(alphabet) - 1)] for _ in range(num_letters)]
    random_data = b''
    for c in random_word:
        random_data += c.encode()
    return random_data

def test_correct_request() -> bool:
    packet = create_request_packet()
    return is_request_packet(packet)

def test_incorrect_request() -> bool:
    packet = generate_random_data()
    return not is_request_packet(packet)

def test_ipv6_accept() -> bool:
    rand_port = randint(0, 2**16 -1)
    rand_address_int = randint(0, 2**128 - 1)
    rand_address = IPv6Address(rand_address_int).compressed
    endpoint = (rand_address, rand_port, 0, 0)
    data = generate_random_data()
    packet = create_accept_packet(endpoint, data)
    result = interpret_accept_packet(packet)
    if result is None:
        return False
    int_endpoint, int_data = result
    return int_endpoint == endpoint and int_data == data

def test_ipv4_accept() -> bool:
    rand_port = randint(0, 2**16 -1)
    rand_address_int = randint(0, 2**32 - 1)
    rand_address = IPv4Address(rand_address_int).compressed
    endpoint = (rand_address, rand_port)
    data = generate_random_data()
    packet = create_accept_packet(endpoint, data)
    result = interpret_accept_packet(packet)
    if result is None:
        return False
    int_endpoint, int_data = result
    return int_endpoint == endpoint and int_data == data

def test_random_accept() -> bool:
    packet = generate_random_data()
    return interpret_accept_packet(packet) == None

# def test_accept() -> bool:
#     type = PacketType.ACCEPT
#     convid = randint(0, 2**32 - 1)
#     packet = create_accept_packet(convid)
#     return test_packet((type, convid, None), packet)

# def test_data() -> bool:
#     type = PacketType.DATA
#     ack = randint(0, 2 ** 24 - 1)
#     data_options: list[tuple[int, bytes] | None] = [None, (0, b'HI'), (1, b'HELLO'), (1000, b'HEY'), (2 ** 24 - 1, b'KONNICHIWA')]
#     data = data_options[randint(0, len(data_options) - 1)]
#     packet = create_data_packet(ack, data)
#     return test_packet((type, ack, data), packet)

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
    test_number(1, "Correct Request Packet", test_correct_request)
    test_number(100, "Incorrect Request Packet", test_incorrect_request)
    test_number(100, "IPv4 Accept Packet", test_ipv4_accept)
    test_number(100, "IPv6 Accept Packet", test_ipv6_accept)
    test_number(100, "Random Accept Packet", test_random_accept)

    print("")
    print("-------------Finished All Packet Tests-------------")
    



if __name__ == "__main__":
    main()