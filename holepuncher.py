from iptools import IP_endpoint

TARGET = 0
NEXT_TIMEOUT = 1
NUM_TIMEOUTS = 2

class HolePuncher:
    def __init__(self, timeout: int, max_timeouts: int):
        self.timeout = timeout
        self.max_timeouts = max_timeouts
        self.targets: list[IP_endpoint] = []
        self.hole_punchers : list[tuple[IP_endpoint, int, int]] = [] # (endpoint, next timeout, num timeouts)
        self.fails: list[IP_endpoint] = []

        self.last_tick_time = 0

    def get_fails(self) -> list[IP_endpoint]:
        fails = self.fails.copy()
        self.fails.clear()
        return fails

    def stop_hole_punch(self, endpoint: IP_endpoint):
        if endpoint not in self.targets:
            return
        index = self.targets.index(endpoint)
        self.targets.pop(index)
        self.hole_punchers.pop(index)

    def hole_punch(self, endpoint: IP_endpoint):
        if endpoint in self.targets:
            self.stop_hole_punch(endpoint)
        self.targets.append(endpoint)
        self.hole_punchers.append((endpoint, self.last_tick_time, -1))

    def tick(self, time: int) -> list[tuple[bytes, IP_endpoint]]:
        send_data : list[tuple[bytes, IP_endpoint]] = []
        self.last_tick_time = time
        timeouts = [hole_puncher for hole_puncher in self.hole_punchers if time >= hole_puncher[NEXT_TIMEOUT]]
        for target, _, num_timeouts in timeouts:
            num_timeouts += 1
            if num_timeouts >= self.max_timeouts:
                self.fails.append(target)
                self.stop_hole_punch(target)
                continue
            # set new timeout and add send data
            index = self.targets.index(target)
            self.hole_punchers[index] = (target, time + self.timeout, num_timeouts)
            send_data.append((b'', target))
        return send_data