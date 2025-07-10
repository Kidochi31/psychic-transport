

class PsychicData:
    # Fields
    # ------
    # timestep : int - the timestep for this data
    # data : bytes - the data 
    def __init__(self, timestep: int, data: bytes):
        self.timestep = timestep
        self.data = data
    
    def get_timestep(self) -> int:
        return self.timestep
    
    def get_data(self) -> bytes:
        return self.data


class PsychicDataPrototype:
    # Fields
    # ------
    # timestep : int - the timestep for this data
    # num_segments : int - the number of data segments for this timestep
    # segments: list[bytes | None]
    # segments_remaining: int - the number of segments remaining
    def __init__(self, timestep: int, num_segments: int):
        self.timestep = timestep
        self.num_segments = num_segments
        self.segments: list[bytes | None] = [None] * num_segments
        self.segments_remaining = num_segments
    
    def add_segment(self, segment_number: int, data: bytes):
        if segment_number >= self.num_segments:
            return
        if self.segments[segment_number] is not None:
            return
        self.segments[segment_number] = data
        self.segments_remaining -= 1
    
    def is_complete(self) -> bool:
        return self.segments_remaining == 0
    
    def get_complete_segment(self) -> PsychicData | None:
        if not self.is_complete():
            return None
        
        data = b''
        for segment in self.segments:
            assert segment is not None
            data += segment
        return PsychicData(self.timestep, data)
