from connection import Connection
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

def test_messages(packets_events: list[list[bytes]], expected_receives_after_event: list[list[tuple[int, bytes]]], max_queue: int = 200, convid: int = 0):
    client = Connection(convid, 0, randint(10, 200), 50)
    client.set_max_receive_queue(max_queue)
    for i, event in enumerate(packets_events):
        for packet in event:
            client.report_receive(packet)
        expected_receive = expected_receives_after_event[i]
        num_receives = 0
        while (receive_data := client.receive()) is not None:
            assert receive_data == expected_receive[num_receives]
            num_receives += 1
        assert num_receives == len(expected_receive)
    assert client.receive() is None

def test_message_ack_wait(receive_events: list[tuple[int, bytes]], expect_events: list[tuple[int, bytes]], test_time_ms: int, wait_before_acking: int = 50, convid:int = 0):
    # receive_events: [(time_ms, data)], expect_events: [(time_ms, data)]
    start_time = 0
    client = Connection(convid, start_time, randint(10, 200), wait_before_acking)

    current_time = start_time
    end_time = start_time + test_time_ms
    while current_time < end_time:
        # first receive if any is necessary
        new_events = list([event for event in receive_events if current_time >= start_time + event[0]])
        if any(new_events):
            for event in new_events:
                receive_events.remove(event)
                client.report_receive(event[1])

        # tick the client and get data to send
        time_since_start = current_time - start_time
        data_to_send = client.tick(current_time)
        # check to see if it was expected
        leeway_ms = 1 # 1 ms
        events_completed = list([event for event in expect_events if abs(time_since_start - event[0]) <= leeway_ms and event[1] in data_to_send])
        for event in events_completed:
            data_to_send.remove(event[1])
            expect_events.remove(event)
        # all data must be expected
        # if len(data_to_send) != 0:
        #     print(time_since_start)
        #     print(abs(time_since_start - expect_events[0][0]))
        #     print(abs(time_since_start - expect_events[0][0]) <= leeway_ms)
        #     print(expect_events[0][1])
        #     print(data_to_send[0])

        assert len(data_to_send) == 0, f"at {current_time}: {data_to_send}"
        current_time += 1
    # all expected events must have occurred
    assert len(expect_events) == 0

def test_unacknowledged_retransmissions(send_events: list[tuple[int, bytes]], expect_events: list[tuple[int, bytes]], test_time_ms: int, rtt: int, max_timeouts: int, fail_time: int | None, convid:int = 0):
    # send_events: [(time_ms, message)], expect_events: [(time_ms, data)]
    start_time = 0
    client = Connection(convid, start_time, rtt, 50)
    client.set_max_timeouts(max_timeouts)

    current_time = start_time
    end_time = start_time + test_time_ms
    while current_time < end_time:
        # first send if any is necessary
        new_events = list([event for event in send_events if current_time >= start_time + event[0]])
        if any(new_events):
            for event in new_events:
                send_events.remove(event)
                client.send(event[1])

        # tick the client and get data to send
        time_since_start = current_time - start_time
        data_to_send = client.tick(current_time)
        # check to see if it was expected
        leeway_ms = 1 # 1 ms
        events_completed = list([event for event in expect_events if abs(time_since_start - event[0]) <= leeway_ms and event[1] in data_to_send])
        for event in events_completed:
            data_to_send.remove(event[1])
            expect_events.remove(event)
        # all data must be expected
        # if len(data_to_send) != 0:
        #     print(time_since_start )
        #     print(abs(time_since_start - expect_events[0][0]))
        #     print(abs(time_since_start - expect_events[0][0]) <= leeway_ns)
        #     print(expect_events[0][1])
        #     print(data_to_send[0])

        assert len(data_to_send) == 0, f"{data_to_send} at {current_time}, still expecting {expect_events}"

        if fail_time is not None and current_time >= fail_time:
            assert not client.is_connected(), f"at {current_time}, still expecting {expect_events}"
            assert all([event[0] > current_time for event in expect_events]), f"{expect_events}"
            return
        if fail_time is not None and current_time < fail_time:
            assert client.is_connected(), f"at {current_time}"

        
        current_time += 1
    # all expected events must have occurred
    assert all([event[0] > current_time for event in expect_events]), f"{expect_events}"

def test_acknowledged_messages(receive_events: list[tuple[int, bytes]], send_events: list[tuple[int, bytes]], expect_events: list[tuple[int, bytes]], test_time_ms: int, rtt: int, max_timeouts: int, fail_time: int | None, rtt_temp: float, expected_rtt: float, fast_retransmit_threshold: int=3, convid:int = 0):
    # send_events: [(time_ms, message)], expect_events: [(time_ms, data)]
    start_time = 0
    client = Connection(convid, start_time, rtt, 50)
    client.set_max_timeouts(max_timeouts)
    client.set_rtt_temperature(rtt_temp)
    client.set_duplicate_acks_before_retransmission(fast_retransmit_threshold)

    current_time = start_time
    end_time = start_time + test_time_ms
    while current_time < end_time:
        # receive if any is necessary
        new_events = list([event for event in receive_events if current_time >= start_time + event[0]])
        if any(new_events):
            for event in new_events:
                receive_events.remove(event)
                client.report_receive(event[1])
        
        # send if any is necessary
        new_events = list([event for event in send_events if current_time >= start_time + event[0]])
        if any(new_events):
            for event in new_events:
                send_events.remove(event)
                client.send(event[1])

        # tick the client and get data to send
        time_since_start = current_time - start_time
        data_to_send = client.tick(current_time)
        # check to see if it was expected
        leeway_ms = 1 # 1 ms
        events_completed = list([event for event in expect_events if abs(time_since_start - event[0]) <= leeway_ms and event[1] in data_to_send])
        for event in events_completed:
            data_to_send.remove(event[1])
            expect_events.remove(event)
        # all data must be expected
        # if len(data_to_send) != 0:
        #     print(time_since_start )
        #     print(abs(time_since_start - expect_events[0][0]))
        #     print(abs(time_since_start - expect_events[0][0]) <= leeway_ns)
        #     print(expect_events[0][1])
        #     print(data_to_send[0])

        assert len(data_to_send) == 0, f"{data_to_send} at {current_time}, still expecting {expect_events}"

        if fail_time is not None and current_time >= fail_time:
            assert not client.is_connected(), f"at {current_time}, still expecting {expect_events}"
            assert all([event[0] > current_time for event in expect_events]), f"{expect_events}"
            assert abs(client.get_rtt() - expected_rtt) <= 0.5, f"expected: {expected_rtt}, got: {client.get_rtt()}" # 1 ms leeway
            return
        if fail_time is not None and current_time < fail_time:
            assert client.is_connected(), f"at {current_time}"

        
        current_time += 1
    # all expected events must have occurred
    assert all([event[0] > current_time for event in expect_events]), f"{expect_events}"
    assert abs(client.get_rtt() - expected_rtt) <= 0.5, f"expected: {expected_rtt}, got: {client.get_rtt()}" # 1 ms leeway

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

def test_ack_waiting():
    print('-testing waiting before sending acks')
    print('testing nothing being received')
    test_message_ack_wait([], [], 100)
    print('testing recieving invalid data or accept')
    test_message_ack_wait([(0, b'hi')], [], 100)
    test_message_ack_wait([(0, create_accept_packet(100))], [], 100)
    print('testing receiving request')
    test_message_ack_wait([(0, create_request_packet(200))], [(0, create_accept_packet(200))], 100, convid=200)
    print('testing receiving a valid message')
    test_message_ack_wait([(0, create_data_packet(0, (0, b'hello')))], [(50, create_data_packet(1, None))], 100, 50)
    test_message_ack_wait([(50, create_data_packet(0, (0, b'hello')))], [(150, create_data_packet(1, None))], 300, 100)
    print('testing immediately acknowledging if set to do so')
    test_message_ack_wait([(0, create_data_packet(0, (0, b'hello')))], [(0, create_data_packet(1, None))], 100, 0)
    print('testing receiving multiple valid messages')
    test_message_ack_wait([(50, create_data_packet(0, (0, b'hello'))), (100, create_data_packet(0, (1, b'hi')))], [(150, create_data_packet(2, None))], 300, 100)
    test_message_ack_wait([(0, create_data_packet(0, (0, b'hello'))), (10, create_data_packet(0, (1, b'hi'))), (20, create_data_packet(0, (2, b'hi!')))], [(75, create_data_packet(3, None))], 300, 75)
    print('testing receiving messages out of order')
    test_message_ack_wait([(0, create_data_packet(0, (1, b'hello')))], [(75, create_data_packet(0, None))], 150, 75)
    test_message_ack_wait([(0, create_data_packet(0, (1, b'hello'))), (50, create_data_packet(0, (0, b'hi')))], [(75, create_data_packet(2, None))], 150, 75)
    test_message_ack_wait([(0, create_data_packet(0, (2, b'2'))), (25, create_data_packet(0, (1, b'1'))), (50, create_data_packet(0, (0, b'0!')))], [(30, create_data_packet(0, None)), (80, create_data_packet(3, None))], 150, 30)
    print('testing data packet with no data')
    test_message_ack_wait([(0, create_data_packet(100, None))], [], 100)
    print('testing data packet with invalid message numbers')
    test_message_ack_wait([(0, create_data_packet(0, (2**24-1, b'-1')))], [], 100)
    test_message_ack_wait([(0, create_data_packet(0, (200, b'200')))], [], 100)
    print('testing sending already acknowledged data')
    test_message_ack_wait([(0, create_data_packet(0, (0, b'0'))), (500, create_data_packet(0, (0, b'0')))], [(250, create_data_packet(1, None)), (750, create_data_packet(1, None))], 1000, 250)
    test_message_ack_wait([(0, create_data_packet(0, (0, b'0'))), (50, create_data_packet(0, (1, b'1'))), (500, create_data_packet(0, (0, b'0')))], [(250, create_data_packet(2, None)), (750, create_data_packet(2, None))], 1000, 250)
    test_message_ack_wait([(0, create_data_packet(0, (0, b'0'))), (400, create_data_packet(0, (1, b'1'))), (500, create_data_packet(0, (0, b'0')))], [(250, create_data_packet(1, None)), (650, create_data_packet(2, None))], 1000, 250)
    print('-completed testing waiting before sending acks')

def calculate_ack_time(rtt: int, dev_rtt: int) -> int:
        return rtt + 4 * dev_rtt

def create_retransmission_test_without_acks(times: list[int], rtt: int, max_timeouts: int, test_time: int):
    times.sort()
    send_events = [(time, generate_random_data()) for time in times]
    ack_time = calculate_ack_time(rtt, rtt // 2)
    expect_events: list[tuple[int, bytes]] = []
    fail_time: int | None = None
    for message_number, (time, message) in enumerate(send_events):
        this_fail_time = time + ack_time * max_timeouts
        if fail_time is None or this_fail_time < fail_time:
            fail_time = this_fail_time
        for n in range(max_timeouts):
            expect_events.append((time + n * ack_time, create_data_packet(0, (message_number, message))))
    test_unacknowledged_retransmissions(send_events, expect_events, test_time, rtt, max_timeouts, fail_time)




def test_retransmissions_without_acks():
    print("-testing retransmissions without acks")
    print('testing no messages sent')
    test_unacknowledged_retransmissions([], [], 100, 10, 5, None)
    print ('testing one message sent')
    test_unacknowledged_retransmissions([(0, b'0')], [(0, create_data_packet(0, (0, b'0')))], 50, 10, 1, calculate_ack_time(10, 5))
    test_unacknowledged_retransmissions([(10, b'10')], [(10, create_data_packet(0, (0, b'10')))], 100, 30, 1, 10 + calculate_ack_time(30, 15))
    test_unacknowledged_retransmissions([(0, b'0')], [(0, create_data_packet(0, (0, b'0'))), (calculate_ack_time(10, 5), create_data_packet(0, (0, b'0')))], 100, 10, 2, 2 * calculate_ack_time(10, 5))
    test_unacknowledged_retransmissions([(0, b'0')], [(0, create_data_packet(0, (0, b'0'))),
                                                      (calculate_ack_time(10, 5), create_data_packet(0, (0, b'0'))),
                                                      (2 * calculate_ack_time(10, 5), create_data_packet(0, (0, b'0')))], 200, 10, 3, 3 * calculate_ack_time(10, 5))
    create_retransmission_test_without_acks([0], 10, 5, 500)
    create_retransmission_test_without_acks([10], 30, 10, 1000)
    print ('testing multiple message sent')
    test_unacknowledged_retransmissions([(0, b'0'), (1, b'1')], [(0, create_data_packet(0, (0, b'0'))), (1, create_data_packet(0, (1, b'1')))], 50, 10, 1, calculate_ack_time(10, 5))
    test_unacknowledged_retransmissions([(0, b'0'), (1, b'1')], [(0, create_data_packet(0, (0, b'0'))), (1, create_data_packet(0, (1, b'1'))), (calculate_ack_time(10, 5), create_data_packet(0, (0, b'0'))), (1 + calculate_ack_time(10, 5), create_data_packet(0, (1, b'1')))], 50, 10, 2, 2 * calculate_ack_time(10, 5))
    create_retransmission_test_without_acks([0, 10, 20], 10, 5, 500)
    create_retransmission_test_without_acks([0, 1, 2, 30, 100, 500], 30, 10, 1000)
    print("-completed testing retransmissions without acks")

def test_acknowledgements():
    print("-testing acknowledgements")
    print('testing a message sent that is immediately acknowledged')
    test_acknowledged_messages([(0 + 1, create_data_packet(1, None))], [(0, b'0')], [(0, create_data_packet(0, (0, b'0')))], 50, 10, 1, None, 0.5, 5)
    test_acknowledged_messages([(1 + 1, create_data_packet(1, None))], [(0, b'0')], [(0, create_data_packet(0, (0, b'0')))], 50, 10, 5, None, 1, 1)
    print('testing receiving request with valid invalid convid')
    test_acknowledged_messages([(10, create_request_packet(100))], [], [(10, create_accept_packet(100))], 100, 10, 5, None, 0.2, 10, 3, 100)
    test_acknowledged_messages([(10, create_request_packet(100))], [], [], 100, 10, 5, 10, 0.2, 10, 3, 50)
    print('testing a message sent that is retransmitted and then acknowledged')
    test_acknowledged_messages([(10 + calculate_ack_time(10, 5) + 1, create_data_packet(1, None))], [(0, b'0')], [(0, create_data_packet(0, (0, b'0'))), (calculate_ack_time(10, 5), create_data_packet(0, (0, b'0')))], 100, 10, 5, None, 0.5, 25)
    print('testing two messages which are cumulatively acknowledged')
    test_acknowledged_messages([(5 + 1, create_data_packet(2, None))], [(0, b'0'), (0, b'1')], [(0, create_data_packet(0, (0, b'0'))), (0, create_data_packet(0, (1, b'1')))], 100, 10, 5, None, 0.5, 7.5)
    test_acknowledged_messages([(10 + 1, create_data_packet(2, None))], [(0, b'0'), (5, b'1')], [(0, create_data_packet(0, (0, b'0'))), (5, create_data_packet(0, (1, b'1')))], 100, 10, 5, None, 0.5, 10)
    print('testing two messages, which are cumulatively acknowledged after the first is retransmitted')
    test_acknowledged_messages([(5 + calculate_ack_time(10, 5) + 1, create_data_packet(2, None))], [(0, b'0'), (10, b'1')], [(0, create_data_packet(0, (0, b'0'))), (10, create_data_packet(0, (1, b'1'))), (calculate_ack_time(10, 5), create_data_packet(0, (0, b'0')))], 100, 10, 5, None, 0.5, 22.5)
    print('testing a message which is not acknowledged at first but then is')
    test_acknowledged_messages([(10 + 1, create_data_packet(0, None)), (10 + calculate_ack_time(10, 5) + 1, create_data_packet(1, None))], [(0, b'0')], [(0, create_data_packet(0, (0, b'0'))), (calculate_ack_time(10, 5), create_data_packet(0, (0, b'0')))], 100, 10, 5, None, 0.5, 25)
    print('testing receiving an ack without anything sent')
    test_acknowledged_messages([(10, create_data_packet(1, None))], [], [], 100, 10, 5, None, 0.5, 10)
    print('testing receiving two separate acks for two messages')
    test_acknowledged_messages([(6 + 1, create_data_packet(1, None)), (9 + 1, create_data_packet(2, None))], [(0, b'0'), (3, b'1')], [(0, create_data_packet(0, (0, b'0'))), (3, create_data_packet(0, (1, b'1')))], 100, 10, 5, None, 0.5, 7.5)
    print("-completed testing acknowledgements")

def test_fast_retransmit():
    print("-testing fast retransmit")
    print('testing sending retransmission after 1 ack')
    test_acknowledged_messages([(10 + 1, create_data_packet(0, None)), (20 + 1, create_data_packet(2, None))], [(0, b'0'), (1, b'1')], [(0, create_data_packet(0, (0, b'0'))), (1, create_data_packet(0, (1, b'1'))), (11, create_data_packet(0, (0, b'0')))], 100, 10, 5, None, 0.5, 15, 1)
    print('testing sending retransmission after 2 acks')
    test_acknowledged_messages([(10 + 1, create_data_packet(0, None)), (15, create_data_packet(0, None)), (25 + 1, create_data_packet(3, None))], [(0, b'0'), (1, b'1'), (15, b'2')], [(0, create_data_packet(0, (0, b'0'))), (1, create_data_packet(0, (1, b'1'))), (16, create_data_packet(0, (0, b'0'))), (15, create_data_packet(0, (2, b'2')))], 100, 10, 5, None, 0.5, 17.5, 2)
    print('testing no retransmission if 1 dup + new ack + 1 dup')
    test_acknowledged_messages([(10 + 1, create_data_packet(0, None)), (15 + 1, create_data_packet(2, None)), (25 + 1, create_data_packet(2, None)), (30, create_data_packet(4, None))], [(0, b'0'), (5, b'1'), (15, b'2'), (20, b'3')], [(0, create_data_packet(0, (0, b'0'))), (5, create_data_packet(0, (1, b'1'))), (15, create_data_packet(0, (2, b'2'))), (20, create_data_packet(0, (3, b'3')))], 100, 10, 5, None, 0.5, 13.75, 2)
    print("-completed fast retransmit")

def main():
    print("---------testing client connections")
    test_receive_invalid_messages()
    test_receive_valid_messages()
    test_ack_waiting()
    test_retransmissions_without_acks()
    test_acknowledgements()
    test_fast_retransmit()
    print("---------completed testing client connections")


if __name__ == "__main__":
    main()