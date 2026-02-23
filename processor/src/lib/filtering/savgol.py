import numpy as np
from collections import deque
from scipy.signal import savgol_coeffs


class SGFilter:
    def __init__(self, window=21, polyorder=3, deriv=0, dt=1):
        """
        Causal Savitzky–Golay filter.

        window     : number of past samples used
        polyorder  : polynomial degree
        deriv      : 0=smooth, 1=rate, 2=acceleration
        dt         : sampling interval (seconds)
        """

        if polyorder >= window:
            raise ValueError("polyorder must be < window")

        self.window = window
        self.polyorder = polyorder
        self.deriv = deriv
        self.dt = dt

        # Precompute trailing coefficients
        self.coeffs = savgol_coeffs(
            window_length=window,
            polyorder=polyorder,
            deriv=deriv,
            delta=dt,
            pos=window - 1,  # causal: evaluate at last point
            use="dot",
        )

        self.buffer = deque(maxlen=window)

    def update(self, value):
        """
        Add one new sample and return filtered value.
        Returns np.nan until buffer is full.
        """
        self.buffer.append(value)

        if len(self.buffer) < self.window:
            return 0.0

        segment = np.array(self.buffer)
        return float(np.dot(self.coeffs, segment))

    def reset(self):
        """Clear internal buffer."""
        self.buffer.clear()
