import time


class DelayQueue:
    def __init__(self, delay: int, burst=0):
        self.delay = delay
        self.burst = burst
        self.items = []
        self.next_packet = 0

    def enqueue(self, item):
        time_with_burst = time.time() - (self.burst * self.delay)
        if self.next_packet < time_with_burst:
            self.next_packet = time_with_burst
        self.items.insert(0, item)

    def dequeue(self):
        if self.items and time.time() > self.next_packet:
            self.next_packet += self.delay
            return self.items.pop()
        else:
            return None
