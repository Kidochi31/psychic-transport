from packet import interpret_packet, PacketType, create_data_packet, create_accept_packet

INIT_MAX_QUEUE = 200
INIT_MAX_TIMEOUTS = 5
INIT_RTT_TEMPERATURE = 0.2
INIT_DEV_RTT_TEMPERATURE = 0.2
INIT_DUPLICATE_ACKS_BEFORE_RETRANSMISSION = 3

FIRST_SEND_TIME = 0
TIME_SENT = 1
ACK_TIMEOUT = 2
TIMEOUTS = 3
MESSAGE = 4

class Connection:
    def __init__(self, convid: int, time_ms: int, rtt_ms: int, wait_before_acking: int):
        self.convid = convid
        self.rtt: float = rtt_ms
        self.rtt_temperature = INIT_RTT_TEMPERATURE
        self.dev_rtt: float = rtt_ms // 2
        self.dev_rtt_temperature = INIT_DEV_RTT_TEMPERATURE
        self.average_receive_delay = self.rtt / 2
        self.max_receive_queue = INIT_MAX_QUEUE
        self.max_timeouts = INIT_MAX_TIMEOUTS

        self.lowest_unreceived_message_number: int = 0
        self.received_messages: list[bool] = []
        self.received_data_for_user: list[tuple[int, bytes]] = []
        
        self.wait_before_acking: int = wait_before_acking
        self.ack_time: int | None = None

        self.lowest_unacked_message_number: int = 0
        self.unacked_messages: list[tuple[int, int, int, int, bytes]] = [] # (first send time, time sent, ack timeout, timeouts, message)
        self.duplicate_acks: int | None = None
        self.duplicate_acks_before_retransmission = INIT_DUPLICATE_ACKS_BEFORE_RETRANSMISSION

        self.send_accept: bool = False

        self.last_tick_time: int = time_ms

        self.connected = True

    def set_wait_before_acking(self, wait_before_acking_ms: int):
        self.wait_before_acking = wait_before_acking_ms

    def set_max_receive_queue(self, max_receive_queue: int):
        self.max_receive_queue = max_receive_queue

    def set_max_timeouts(self, max_timeouts: int):
        self.max_timeouts = max_timeouts
    
    def set_rtt_temperature(self, rtt_temperature: float):
        self.rtt_temperature = rtt_temperature
    
    def set_dev_rtt_temperature(self, dev_rtt_temperature: float):
        self.dev_rtt_temperature = dev_rtt_temperature
    
    def set_duplicate_acks_before_retransmission(self, duplicate_acks_before_retransmission: int):
        self.duplicate_acks_before_retransmission = duplicate_acks_before_retransmission

    def get_rtt(self) -> float:
        return self.rtt
    
    def get_dev_rtt(self) -> float:
        return self.dev_rtt

    def is_connected(self) -> bool:
        return self.connected

    def report_receive(self, packet: bytes):
        if not self.connected:
            return
        
        result = interpret_packet(packet)
        if result is None:
            return
        type = result[0]
        match type:
            case PacketType.REQUEST:
                # respond to all request packets with an accept, only if the convid matches
                convid = result[1]
                if convid == self.convid:
                    self.send_accept = True
                else:
                    # disconnect if it doesn't match
                    self.connected = False
                return
            case PacketType.ACCEPT:
                # ignore any further request packets
                return
            case PacketType.DATA:
                ack = result[1]
                message = result[2]
                self._report_ack_received(ack)
                if message is not None and not isinstance(message, int):
                    self._report_message_received(message[0], message[1])

    def tick(self, time_ms: int) -> list[bytes]:
        if not self.connected:
            return []

        self.last_tick_time = time_ms
        packets_to_send: list[bytes] = []
        # if an accept needs to be sent, do that
        if self.send_accept:
            self.send_accept = False
            packets_to_send.append(create_accept_packet(self.convid))
        
        # check if data to send
        timeout_packets = self._manage_and_get_timeout_packets()
        if len(timeout_packets) > 0:
            packets_to_send.extend(timeout_packets)
            self.ack_time = None # reset ack time
        # if no data to send, but an ack needs to be sent anyway -> send an ack
        elif self.ack_time is not None and time_ms >= self.ack_time:
            self.ack_time = None # reset ack time
            packets_to_send.append(create_data_packet(self.lowest_unreceived_message_number, None))
        
        return packets_to_send

    def receive(self) -> tuple[int, bytes] | None:
        # Receives new data from the other endpoint
        if len(self.received_data_for_user) == 0:
            return None
        data = self.received_data_for_user[0]
        self.received_data_for_user.pop(0)
        return data
    
    def send(self, message: bytes):
        # Prepares to send data to the other endpoint
        timeout = self.last_tick_time # send immediately on next tick
        self.unacked_messages.append((self.last_tick_time, self.last_tick_time, timeout, -1, message))

    def _report_rtt_estimate(self, rtt: int):
        self.rtt = rtt * self.rtt_temperature + (1 - self.rtt_temperature) * self.rtt
        self.dev_rtt = abs(rtt - self.rtt) * self.dev_rtt_temperature + (1 - self.dev_rtt_temperature) * self.dev_rtt

    def _manage_duplicate_ack(self):
        if len(self.unacked_messages) == 0: # if no messages are being sent -> ignore
            return
        if self.last_tick_time >= self.unacked_messages[0][TIME_SENT] + self.rtt: # if it's been at least 1 rtt since it was sent -> duplicate
            # increment number of duplicate acks
            if self.duplicate_acks is None:
                self.duplicate_acks = 1
            else:
                self.duplicate_acks += 1
            # check if reached threshold (fast retransmit)
            if self.duplicate_acks >= self.duplicate_acks_before_retransmission:
                # reset duplicate acks and make the message retransmit immediately (fast retransmit)
                self.duplicate_acks = None
                self.unacked_messages[0] = (self.unacked_messages[0][FIRST_SEND_TIME], self.last_tick_time, self.last_tick_time, self.unacked_messages[0][TIMEOUTS], self.unacked_messages[0][MESSAGE])

    def _report_ack_received(self, ack: int):
        if ack == self.lowest_unacked_message_number:
            self._manage_duplicate_ack()
        if ack <= self.lowest_unacked_message_number:
            return # already received ack
        
        num_to_ack = ack - self.lowest_unacked_message_number
        highest_time_sent: int | None = None
        for _ in range(num_to_ack):
            if len(self.unacked_messages) == 0:
                break
            # remove from unacked messages, and increment the lowest unacked message number
            self.lowest_unacked_message_number += 1
            time, _, _, _, _ = self.unacked_messages.pop(0)
            # find the lowest time a packet was sent (to estimate rtt)
            if highest_time_sent is None or time < highest_time_sent:
                highest_time_sent = time
        if highest_time_sent is None:
            return
        # reset duplicate acks
        self.duplicate_acks = None
        # report the rtt found
        self._report_rtt_estimate(self.last_tick_time - highest_time_sent)


    def _report_must_send_ack(self):
        # set ack time if there is no expected ack
        if self.ack_time is None:
            self.ack_time = self.last_tick_time + self.wait_before_acking
        # otherwise, the ack time is already set -> do not need to change

    def _report_message_received(self, message_number: int, message: bytes):
        if message_number < self.lowest_unreceived_message_number:
            self._report_must_send_ack()
            return # already received -> ignore
        relative_message_number = message_number - self.lowest_unreceived_message_number
        if relative_message_number >= self.max_receive_queue:
            return # too far ahead
        # extend list of unreceived message records if needed
        if relative_message_number >= len(self.received_messages):
            self.received_messages.extend([False] * (relative_message_number - len(self.received_messages) + 1))
        # check if the message has been received
        if self.received_messages[relative_message_number]:
            self._report_must_send_ack()
            return # already received -> ignore
        # it is a new message -> mark it as such and add it to the received data
        self.received_messages[relative_message_number] = True
        self.received_data_for_user.append((message_number, message))
        if relative_message_number != 0:
            self._report_must_send_ack()
            return
        # the next required message has been received
        # remove all sequentially received messages from the list
        self._report_must_send_ack()
        while len(self.received_messages) > 0 and self.received_messages[0]:
            self.received_messages.pop(0)
            self.lowest_unreceived_message_number += 1
    
    def _calculate_ack_timeout(self) -> int:
        return int(self.last_tick_time + (self.rtt + 4 * self.dev_rtt))
    
    def _manage_and_get_timeout_packets(self) -> list[bytes]:
        packets_to_send: list[bytes] = []
        timeout_messages: list[int] = []

        # go through all messages and check for timeouts -> if so, prepare to retransmit
        for i, message_info in enumerate(self.unacked_messages):
            if self.last_tick_time >= message_info[ACK_TIMEOUT]:
                timeout_messages.append(i)
                message_number = i + self.lowest_unacked_message_number
                message = message_info[MESSAGE]
                data = create_data_packet(self.lowest_unreceived_message_number, (message_number, message))
                packets_to_send.append(data)
        
        # go through all timeout messages, reset timeout, and incremenet number of timeouts
        for i in timeout_messages:
            first_send_time, _, _, timeouts, message = self.unacked_messages[i]
            timeouts += 1
            if timeouts >= self.max_timeouts:
                # too many timeouts -> close connection
                self.connected = False
                return []
            self.unacked_messages[i] = (first_send_time, self.last_tick_time, self._calculate_ack_timeout(), timeouts, message)
        
        return packets_to_send