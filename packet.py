from enum import Enum

class PacketType(Enum):
    REQUEST = 0b10000000
    ACCEPT = 0b01000000
    DATA = 0b00100000

def create_request_packet(convid: int) -> bytes:
    type_bytes = PacketType.REQUEST.value.to_bytes(1, 'big')
    convid_bytes = convid.to_bytes(4, 'big')
    return type_bytes + convid_bytes

def create_accept_packet(convid: int) -> bytes:
    type_bytes = PacketType.ACCEPT.value.to_bytes(1, 'big')
    convid_bytes = convid.to_bytes(4, 'big')
    return type_bytes + convid_bytes

def create_data_packet(ack: int, message: tuple[int, bytes] | None) -> bytes:
    data = PacketType.DATA.value.to_bytes(1, 'big')
    data += ack.to_bytes(3, 'big')
    if message is not None:
        data += message[0].to_bytes(3, 'big')
        data += message[1]
    return data

def interpret_packet(packet: bytes) -> tuple[PacketType, int, tuple[int, bytes] | None] | None:
    # returns the packet type, acknowledgement/version, and data (if there is data)
    if len(packet) < 2:
        return None
    if not packet[0] in [type.value for type in PacketType]:
        return None
    type = PacketType(packet[0])
    match type:
        case PacketType.REQUEST:
            if len(packet) < 5:
                return None
            convid = int.from_bytes(packet[1:5])
            return (type, convid, None)
        case PacketType.ACCEPT:
            if len(packet) < 5:
                return None
            convid = int.from_bytes(packet[1:5])
            return (type, convid, None)
        case PacketType.DATA:
            if len(packet) < 4:
                return None
            acknowledgement = int.from_bytes(packet[1:4], 'big')
            if len(packet) == 4:
                return (type, acknowledgement, None)
            # if it is greater, expect message number
            if len(packet) < 7:
                return None
            message_number = int.from_bytes(packet[4:7], 'big')
            return (type, acknowledgement, (message_number, packet[7:]))