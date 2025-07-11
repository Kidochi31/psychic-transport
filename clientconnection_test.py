from clientconnection import ClientConnection
from packet import create_accept_packet, create_request_packet, create_data_packet
from random import randint

alphabet = 'abcdefghijklmnopqrstuvwxyz'

def generate_random_data() -> bytes:
    num_letters = randint(0, 10)
    random_word = [alphabet[randint(0, len(alphabet) - 1)] for _ in range(num_letters)]
    random_data = b''
    for c in random_word:
        random_data += c.encode()
    return random_data

def generate_data_events(events: list[list[tuple[int, bytes, bool]]]) -> tuple[list[list[bytes]], list[list[tuple[int, bytes]]]]:
    #events: [[(message_number, message, should_receive)]]
    packet_events: list[list[bytes]] = []
    expected_receives_after_event: list[list[tuple[int, bytes]]] = []
    for event in events:
        packet_event: list[bytes] = []
        expected_receive: list[tuple[int, bytes]] = []
        for message_number, message, should_receive in event:
            packet_event.append(create_data_packet(0, (message_number, message)))
            if should_receive:
                expected_receive.append((message_number, message))
        packet_events.append(packet_event)
        expected_receives_after_event.append(expected_receive)
    return packet_events, expected_receives_after_event

def test_data_messages(events: list[list[tuple[int, bytes, bool]]], max_queue: int = 200):
    packet_events, expected_receives_after_event = generate_data_events(events)
    test_messages(packet_events, expected_receives_after_event, max_queue)

def test_messages(packets_events: list[list[bytes]], expected_receives_after_event: list[list[tuple[int, bytes]]], max_queue: int = 200):
    client = ClientConnection(randint(10, 200))
    client.set_max_queue(max_queue)
    for i, event in enumerate(packets_events):
        for packet in event:
            client.report_received(packet)
        expected_receive = expected_receives_after_event[i]
        num_receives = 0
        while (receive_data := client.receive()) is not None:
            assert receive_data == expected_receive[num_receives]
            num_receives += 1
        assert num_receives == len(expected_receive)
    assert client.receive() is None




def test_receive_invalid_messages():
    print("-testing receiving invalid messages")
    print('testing no messages')
    test_messages([], [])
    print ('testing invalid messages')
    test_messages([[b'hi']],
                  [[]])
    test_messages([[b'hi'], [b'hello']],
                  [[],      []])
    test_messages([[b'hi', b'rubbish'], [b'hello', b'MORE RUBBISH', b'EVEN MORE RUBBISH'], [b'SO MUCH RUBBISH DATA']],
                  [[],                  [],                                                []])
    test_messages([[generate_random_data()], [generate_random_data(), generate_random_data()], [generate_random_data()]],
                  [[],                       [],                                               []])
    test_messages([[b''], [b'', b''], [b'', b'', b''], [b'', b'', b'', b'']],
                  [[],    [],         [],              []])
    print('testing receiving accept/request')
    test_messages([[create_accept_packet(100)], [create_request_packet(200)]],
                  [[],                          []])
    print("-completed testing receiving invalid messages")

def test_receive_valid_messages():
    print("-testing receiving valid messages")
    print('testing data packet with no data')
    test_messages([[create_data_packet(0, None)]],
                  [[]])
    test_messages([[create_data_packet(0, None), create_data_packet(0, None)], [create_data_packet(0, None), create_data_packet(0, None)]],
                  [[],                                                         []])
    print('testing data packet with data')
    test_data_messages([[(0, b'hi', True)]])
    test_data_messages([[(0, b'', True)]])
    test_data_messages([[(0, b'0', True), (1, b'1', True)]])
    test_data_messages([[(0, b'0', True)], [(1, b'1', True)]])
    test_data_messages([[(1, b'1', True)], [(0, b'0', True)]])
    test_data_messages([[(0, b'0', True), (3, b'3', True)], [(2, b'2', True), (1, b'1', True)]])
    test_data_messages([[(1, b'1', True), (3, b'3', True)], [(1, b'1', False), (0, b'0', True)]])
    test_data_messages([[(1, b'1', True), (3, b'3', True)], [(1, b'2', False), (0, b'0', True)]])
    print('testing data packet with invalid message numbers')
    test_data_messages([[(2**24-1, b'-1', False), (3, b'3', True)], [(1, b'1', True), (0, b'0', True)]], 200)
    test_data_messages([[(200, b'200', False), (3, b'3', True)], [(1, b'1', True), (0, b'0', True)]], 200)
    test_data_messages([[(199, b'199', True), (3, b'3', True)], [(1, b'1', True), (0, b'0', True)]], 200)
    test_data_messages([[(199, b'199', True)], [(200, b'200', False)]], 200)
    test_data_messages([[(200, b'200', False)], [(0, b'0', True)], [(200, b'200', True)]], 200)
    test_data_messages([[(200, b'200', False),(0, b'0', True),(200, b'200', True)]], 200)
    test_data_messages([[(201, b'201', False),(0, b'0', True),(201, b'201', False)]], 200)
    test_data_messages([[(201, b'201', False),(0, b'0', True),(1,b'1',True),(201, b'201', True)]], 200)
    test_data_messages([[(201, b'201', False),(1,b'1',True),(201, b'201', False)]], 200)
    test_data_messages([[(201, b'201', False)],[(1,b'1',True)],[(201, b'201', False)]], 200)
    test_data_messages([[(1, b'1', False)],[(0,b'0',True)],[(1, b'1', True)]], 1)
    test_data_messages([[(1, b'1', True)],[(0,b'0',True)],[(1, b'1', False)]], 2)
    print("-completed testing receiving valid messages")


def main():
    print("---------testing client connections")
    test_receive_invalid_messages()
    test_receive_valid_messages()
    print("---------completed testing client connections")


if __name__ == "__main__":
    main()