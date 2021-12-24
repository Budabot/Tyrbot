import time


class DelayQueue:
    def __init__(self, recovery: int, burst=0):
        self.recovery = recovery
        self.burst = burst
        self.items = []
        self.next_packet = 0

    def enqueue(self, item, priority=50):
        """

        :param item:
        :param priority: 0 is highest priority
        :return:
        """
        index = 0
        for _priority, _item in self.items:
            if priority < _priority:
                index += 1
            else:
                break

        self.items.insert(index, (priority, item))

    def dequeue(self):
        if self.items:
            t = time.time()
            time_with_burst = t - (self.burst * self.recovery)
            if self.next_packet < time_with_burst:
                self.next_packet = time_with_burst

            if t >= self.next_packet:
                self.next_packet += self.recovery
                (priority, item) = self.items.pop()
                return item
        else:
            return None

    def __len__(self):
        return len(self.items)

    def clear(self):
        self.items = []

    def is_empty(self):
        return len(self.items) == 0
