from packet import interpret_packet, PacketType, create_data_packet
from time import time_ns

INIT_MAX_QUEUE = 200
INIT_WAIT_BEFORE_ACKING = 50

class ClientConnection:
    def __init__(self, rtt_ms: int):
        self.rtt = rtt_ms
        self.d_rtt = rtt_ms / 2
        self.average_receive_delay = self.rtt / 2
        self.max_queue = INIT_MAX_QUEUE

        self.lowest_unreceived_message_number: int = 0
        self.received_messages: list[bool] = []
        self.received_data_for_user: list[tuple[int, bytes]] = []
        
        self.wait_before_acking: int = INIT_WAIT_BEFORE_ACKING
        self.ack_time: int | None = None

        self.connected = True

    def set_wait_before_acking(self, wait_before_acking_ms: int):
        self.wait_before_acking = wait_before_acking_ms

    def set_max_queue(self, max_queue: int):
        self.max_queue = max_queue

    def is_connected(self) -> bool:
        return self.connected

    def report_received(self, packet: bytes):
        if not self.connected:
            return
        
        result = interpret_packet(packet)
        if result is None:
            return
        type = result[0]
        match type:
            case PacketType.REQUEST:
                # will not receive request from server -> ignore
                return
            case PacketType.ACCEPT:
                # may receive multiple accepts from server -> ignore
                return
            case PacketType.DATA:
                ack = result[1]
                message = result[2]
                self._report_ack_received(ack)
                if message is not None:
                    self._report_message_received(message[0], message[1])

    def tick(self) -> list[bytes]:

        # if no data to send, but an ack needs to be sent anyway -> send an ack
        if self.ack_time is not None and time_ns() >= self.ack_time:
            self.ack_time = None # reset ack time
            return [create_data_packet(self.lowest_unreceived_message_number, None)]
        # otherwise, no data to send, and no ack to send -> do nothing
        return []

    def receive(self) -> tuple[int, bytes] | None:
        # Receives new data from the other endpoint
        if len(self.received_data_for_user) == 0:
            return None
        data = self.received_data_for_user[0]
        self.received_data_for_user.pop(0)
        return data
    
    def send(self, message: bytes):
        # Prepares to send data to the other endpoint
        pass


    def _report_ack_received(self, ack: int):
        pass

    def _report_must_send_ack(self):
        # set ack time if there is no expected ack
        if self.ack_time is None:
            self.ack_time = time_ns() + self.wait_before_acking * 1_000_000
        # otherwise, the ack time is already set -> do not need to change

    def _report_message_received(self, message_number: int, message: bytes):
        if message_number < self.lowest_unreceived_message_number:
            self._report_must_send_ack()
            return # already received -> ignore
        relative_message_number = message_number - self.lowest_unreceived_message_number
        if relative_message_number >= self.max_queue:
            return # too far ahead
        # extend list of unreceived message records if needed
        if relative_message_number >= len(self.received_messages):
            self.received_messages.extend([False] * (relative_message_number - len(self.received_messages) + 1))
        # check if the message has been received
        if self.received_messages[relative_message_number]:
            return # already received -> ignore
        # it is a new message -> mark it as such and add it to the received data
        self.received_messages[relative_message_number] = True
        self.received_data_for_user.append((message_number, message))
        if relative_message_number != 0:
            return
        # the next required message has been received
        # remove all sequentially received messages from the list
        self._report_must_send_ack()
        while len(self.received_messages) > 0 and self.received_messages[0]:
            self.received_messages.pop(0)
            self.lowest_unreceived_message_number += 1