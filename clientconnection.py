from packet import interpret_packet, PacketType

INIT_MAX_QUEUE = 200

class ClientConnection:
    def __init__(self, rtt_ms: int):
        self.rtt = rtt_ms
        self.d_rtt = rtt_ms / 2
        self.average_receive_delay = self.rtt / 2
        self.max_queue = INIT_MAX_QUEUE

        self.lowest_unreceived_message_number: int = 0
        self.received_messages: list[bool] = []
        self.received_data_for_user: list[tuple[int, bytes]] = []

        self.connected = True

    def set_max_queue(self, max_queue: int):
        self.max_queue = max_queue
    
    def get_max_queue(self, max_queue: int) -> int:
        return self.max_queue

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

    def tick(self):
        pass

    def receive(self) -> tuple[int, bytes] | None:
        # Receives new data from the other endpoint
        if len(self.received_data_for_user) == 0:
            return None
        data = self.received_data_for_user[0]
        self.received_data_for_user.pop(0)
        return data
    
    def send(self, message: bytes):
        # Sends data to the other endpoint
        pass


    def _report_ack_received(self, ack: int):
        pass

    def _report_message_received(self, message_number: int, message: bytes):
        if message_number < self.lowest_unreceived_message_number:
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
        # remove all sequentially received messages from the list
        while len(self.received_messages) > 0 and self.received_messages[0]:
            self.received_messages.pop(0)
            self.lowest_unreceived_message_number += 1
