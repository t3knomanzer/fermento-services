class EMAFilter:
    def __init__(self, alpha):
        self.alpha = alpha
        self.value = None

    def update(self, new_sample):
        if self.value is None:
            self.value = new_sample  # initialize with first value
        else:
            self.value = self.alpha * new_sample + (1 - self.alpha) * self.value
        return self.value
