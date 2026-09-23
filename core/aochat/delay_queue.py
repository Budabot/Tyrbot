import threading
import time


class DelayQueue:
    """
    Rate-limited queue of outgoing packets.

    Producers (Conn.add_packets_to_queue) and the consumer (the conn's packet loop) all run on
    the bot's single event loop now, so the lock below is no longer load-bearing - it is kept as
    cheap insurance for any future caller that runs on a worker thread. What it guards against is
    two producers both passing the `next_packet` check in the same tick and sending back to back,
    which is what the chat server flood-kicks for.

    The lock is not reentrant, so no method here may call another one.
    """

    def __init__(self, recovery: int, burst=0):
        self.recovery = recovery
        self.burst = burst
        self.items = []
        self.next_packet = 0
        self.lock = threading.Lock()

    def enqueue(self, item, priority=50):
        """

        :param item:
        :param priority: 0 is highest priority
        :return:
        """
        with self.lock:
            index = 0
            for _priority, _item in self.items:
                if priority < _priority:
                    index += 1
                else:
                    break

            self.items.insert(index, (priority, item))

    def dequeue(self):
        with self.lock:
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
        with self.lock:
            return len(self.items)

    def clear(self):
        with self.lock:
            self.items = []

    def is_empty(self):
        with self.lock:
            return len(self.items) == 0
