from psychicdata import PsychicData, PsychicDataPrototype
from iptools import *
from packet import interpret_packet_safe, PacketType
from time import time_ns

class ClientConnection:
    def __init__(self, server: IP_endpoint, rtt_ms: int, relative_server_time_ms: int, timestep_period_ms: int, timestep0: int, server_data: bytes):
        self.server = server
        self.rtt = rtt_ms
        self.d_rtt = rtt_ms / 2
        self.average_receive_delay = self.rtt / 2
        self.relative_server_time = relative_server_time_ms
        self.timestep_period = timestep_period_ms
        self.timestep0 = timestep0
        self.server_data = server_data

        self.lowest_incomplete_timestep: int = 0
        self.incomplete_timesteps: list[PsychicDataPrototype | None] = []

    def get_current_tick(self) -> int:
        return (time_ns() // 1_000_000 - self.timestep0 + self.relative_server_time) // self.timestep_period

    def report_received_data(self, data: bytes):
        interpret_result = interpret_packet_safe(data)
        if interpret_result is None:
            return
        type = interpret_result[0]
        info = interpret_result[1]
        match type:
            case PacketType.REQUEST:
                return # ignore
            case PacketType.ACCEPT:
                return # ignore
            case PacketType.DATA:
                # [("timestep"("timestamp"("delay"("seg"("totalsegs"("data", FieldType.ENDDATA)]
                timestep = int(info["timestep"])
                if timestep > self.get_current_tick():
                    return # ignore if from a future timestep
                segment = int(info["seg"])
                total_segments = int(info["totalsegs"])
                segment_data = info["data"]
                self._manage_data(timestep, segment, total_segments, segment_data)
                timestamp = int(info["timestamp"])
                delay = int(info["delay"])
                self._report_delay_received(timestep, timestamp, delay)
                return # finished managing the data
            case PacketType.NAK:
                pass

    def _manage_data(self, timestep: int, segment: int, total_segments: int, data: bytes):
        if timestep < self.lowest_incomplete_timestep:
            return # ignore -> already managed
        relative_timestep = timestep - self.lowest_incomplete_timestep
        # extend incomplete_timsteps if necessary
        if relative_timestep >= len(self.incomplete_timesteps):
            self.incomplete_timesteps.extend([None] * (len(self.incomplete_timesteps) - relative_timestep + 1))
        # initialise the segment if necessary
        data_prototype = self.incomplete_timesteps[relative_timestep]
        if data_prototype is None:
            data_prototype = PsychicDataPrototype(timestep, total_segments)
            self.incomplete_timesteps[relative_timestep] = data_prototype
        # add the segment to the prototype
        data_prototype.add_segment(segment, data)

    def _report_delay_received(self, timestep: int, timestamp: int, delay: int):
        # first, calculate the delay of the received packet
        time_sent = self.timestep0 + timestep * self.timestep_period + timestamp
        time_received = time_ns() // 1_000_000
        receive_delay_estimate = time_sent - time_received

        # rtt is estimated by adding the two delays together
        rtt_estimate = receive_delay_estimate + delay

        # relative server time is estimated by finding the


    def tick(self):
        pass

    def receive(self) -> list[PsychicData]:
        # Receives new data from the other endpoint
        return []
    
    def send(self, data: PsychicData):
        # Sends data to the other endpoint
        pass