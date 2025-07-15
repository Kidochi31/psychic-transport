from clientconnector import ClientConnector
from packet import *
from random import randint

alphabet = 'abcdefghijklmnopqrstuvwxyz'

def test_client_connection(convid: int, max_timeouts: int, request_timeout_ms: int, server_responses: list[tuple[int, bytes, bool, bool]]) -> bool:
    # server_responses: (delay_ms, data, should_connect, immediate_fail)
    start_time = 0
    client = ClientConnector(convid, start_time, max_timeouts, request_timeout_ms, 50_000_000, 50_000_000)
    if not client.is_connecting():
        print('should be connecting at start')
        return False
    if client.is_connected():
        print('should not be connected at start')
        return False
    if client.connect_failed():
        print('should not be failed at start')

    current_time = start_time
    num_packets = 0
    time_last_request = 0
    should_connect = False
    immediate_fail = False

    while client.is_connecting():
        if should_connect:
            print('should have connected')
            return False
        if immediate_fail:
            print('should have failed')
            return False

        new_responses = list([response for response in server_responses if current_time >= start_time + response[0] * 1_000_000])
        if any(new_responses):
            for response in new_responses:
                server_responses.remove(response)
                client.report_receive(response[1])
                should_connect = response[2]
                immediate_fail = response[3]
        
        data_to_send = client.tick(current_time)
        for packet in data_to_send:
            num_packets += 1
            if num_packets > max_timeouts:
                print('too many requests')
                return False
            if time_last_request == 0:
                time_last_request = current_time
            else:
                if current_time - time_last_request <  request_timeout_ms - 1: # 1 ms leeway
                    print('request sent too early')
                    return False
                time_last_request = current_time
            if client.is_connected():
                print('request sent after connecting')
                return False
            if immediate_fail or client.connect_failed() or not client.is_connecting():
                print('request sent after failing')
                return False

            result = interpret_packet(packet)
            if result is None:
                print("invalid packet made")
                return False
            if result[0] != PacketType.REQUEST:
                print("should be a request packet")
                return False
            if result[1] != convid:
                print(f'convid should match: {result[1]} but expected {convid}')
                return False
        if time_last_request != 0 and current_time - time_last_request > request_timeout_ms + 1:
            print(f'request taken too long: {(current_time - time_last_request)} ms but expected {request_timeout_ms}')
            return False
        current_time += 1

    if client.tick(current_time) != []:
        print(f'request sent after no longer connecting: ')
        return False

    if should_connect and client.is_connected():
        connection = client.get_connection_info()
        if connection is None:
            print("connection is None after connecting")
            return False
        
        if abs(abs(current_time - time_last_request) - connection.rtt) >= 1: #must be within 1 ms
            print(f"rtt not within 10 ms of correct value: {connection.rtt} expected: {abs(current_time - time_last_request)}")
            return False
        return True

    if should_connect and (not client.is_connected() or client.connect_failed() or client.is_connecting()):
        print('should be connected')
        return False
    if immediate_fail and (not client.connect_failed() or client.is_connected() or client.is_connecting()):
        print('should not be connected')
        return False
    if not client.connect_failed():
        print('should have failed')
        return False
    
    if not immediate_fail and num_packets != max_timeouts:
        print(f'packets sent do not match: {num_packets}, expected {max_timeouts}')
        return False
    return True

def test_connecting_to_nothing():
    print('connecting to silent server')
    assert test_client_connection(0, 5, 100, [])
    print('passed connecting to silent server')

    print('connecting to server that sends random data')
    #assert test_client_connection(0, 3, 200, [(100, b'hi', False, False), (200, b'hiiiii from server', False, False), (450, b'byee from server', False, False)])
    for _ in range(10):
        print("testing...")
        attempts = randint(1, 5)
        timeout = randint(50, 200)
        version = randint(0, 255)
        num_responses = randint(0, 10)
        responses: list[tuple[int, bytes, bool, bool]] = []
        for _ in range(num_responses):
            responses.append(create_random_response(attempts, timeout))
        assert test_client_connection(version, attempts, timeout, responses)
    print('passed')
    print('passed connecting to server that sends random data')

def create_random_response(attempts: int, timeout: int) -> tuple[int, bytes, bool, bool]:
    send_time = randint(0, (attempts + 1) * timeout)
    num_letters = randint(0, 10)
    random_word = [alphabet[randint(0, len(alphabet) - 1)] for _ in range(num_letters)]
    random_data = b''
    for c in random_word:
        random_data += c.encode()
    return (send_time, random_data, False, False)

def create_accept_response(attempts: int, timeout: int, version: int) -> tuple[int, bytes, bool, bool]:
    send_time = randint(0, (attempts + 1) * timeout)
    return (send_time, create_accept_packet(version), True, False)

def create_incorrect_version_accept_response(attempts: int, timeout: int, version: int) -> tuple[int, bytes, bool, bool]:
    send_time = randint(0, (attempts + 1) * timeout)
    different_version = (version + randint(1, 2**32 - 1)) % 2**32
    return (send_time, create_accept_packet(different_version), False, True)

def test_receiving_accept():
    print('connecting to server that will respond with accept')
    for _ in range(10):
        print("testing...")
        attempts = randint(1, 5)
        timeout = randint(50, 200)
        version = randint(0, 2**32 - 1)
        assert test_client_connection(version, attempts, timeout, [create_accept_response(attempts, timeout, version)])
    print('passed')

def test_receiving_accept_wrong_version():
    print('connecting to server that will respond with an accept with the wrong version')
    for _ in range(10):
        print('testing...')
        attempts = randint(1, 5)
        timeout = randint(50, 200)
        version = randint(0, 2**32 - 1)
        assert test_client_connection(version, attempts, timeout, [create_incorrect_version_accept_response(attempts, timeout, version)])
    print('passed')

def main():
    print("----------Starting Client Connection Tests----------")
    test_connecting_to_nothing()
    test_receiving_accept()
    test_receiving_accept_wrong_version()
    print("----------Finished Client Connection Tests----------")

if __name__ == "__main__":
    main()
    