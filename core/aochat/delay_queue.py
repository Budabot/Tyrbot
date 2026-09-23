import threading
import time


class DelayQueue:
    """
    Rate-limited queue of outgoing packets.

    Used from both the bot's main thread (via Conn.add_packets_to_queue) and the AsyncService
    loop (via the packet loop), so every method that touches `items` or `next_packet` holds the
    lock. Without it two threads can both pass the `next_packet` check in the same tick and send
    back to back, which is what the chat server flood-kicks for.

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
