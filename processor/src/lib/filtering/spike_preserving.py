class SpikePreservingFilter:
    def __init__(self, alpha=0.05, spike_threshold=0.02):
        self.alpha = alpha
        self.spike_threshold = spike_threshold
        self.trend = None

    def update(self, new_sample):
        # Initialize trend
        if self.trend is None:
            self.trend = new_sample
            return {"trend": new_sample, "residual": 0.0, "output": new_sample}

        # Update slow trend
        self.trend = self.alpha * new_sample + (1 - self.alpha) * self.trend

        # Compute residual
        residual = new_sample - self.trend

        # Spike detection
        if abs(residual) > self.spike_threshold:
            output = new_sample  # preserve spike
        else:
            output = self.trend  # smooth baseline

        return {"trend": self.trend, "residual": residual, "output": output}
