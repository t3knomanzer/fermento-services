from collections import deque


class DerivativeComputation:
    def __init__(self, window_size=5):
        self.window = deque(maxlen=window_size)
        self.time_window = deque(maxlen=window_size)

    def update(self, growth_value, timestamp):
        self.window.append(growth_value)
        self.time_window.append(timestamp)

        if len(self.window) < 2:
            return 0.0  # not enough samples

        # rate = (last - first) / (time difference)
        dt_minutes = (self.time_window[-1] - self.time_window[0]).total_seconds() / 60.0
        if dt_minutes == 0:
            return 0.0

        derivative = (self.window[-1] - self.window[0]) / dt_minutes
        return derivative
