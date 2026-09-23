import threading
import unittest

from core.aochat.delay_queue import DelayQueue


class DelayQueueTest(unittest.TestCase):
    def test_equivalent_priority(self):
        # when using default or equivalent priority, order should be insertion order
        delay_queue = DelayQueue(1, 100)

        delay_queue.enqueue("A")
        delay_queue.enqueue("B")
        delay_queue.enqueue("C")
        delay_queue.enqueue("D")
        delay_queue.enqueue("E")

        self.assertEqual("A", delay_queue.dequeue())
        self.assertEqual("B", delay_queue.dequeue())
        self.assertEqual("C", delay_queue.dequeue())
        self.assertEqual("D", delay_queue.dequeue())
        self.assertEqual("E", delay_queue.dequeue())

    def test_specified_priority(self):
        # when using differing priorities, order should be priority order and then insertion order
        delay_queue = DelayQueue(1, 100)

        delay_queue.enqueue("A", 5)
        delay_queue.enqueue("B", 5)
        delay_queue.enqueue("C", 3)
        delay_queue.enqueue("D", 1)
        delay_queue.enqueue("E", 1)

        # D should come before E since D was inserted first
        # then C
        # then A before B since A was inserted first

        self.assertEqual("D", delay_queue.dequeue())
        self.assertEqual("E", delay_queue.dequeue())
        self.assertEqual("C", delay_queue.dequeue())
        self.assertEqual("A", delay_queue.dequeue())
        self.assertEqual("B", delay_queue.dequeue())

    # The three tests below assert DelayQueue's thread-safety contract. Note that they cannot
    # currently fail against an unlocked DelayQueue: on CPython, dequeue() contains no backward
    # jump and no GIL-releasing call, so the interpreter never preempts inside it and the method
    # is atomic by accident. Insert any yield point into that critical section and the rate limit
    # collapses immediately (verified: 47/50 rounds). They are here to pin the contract and to
    # catch a regression on a free-threaded build, not as a reproduction of a live failure.

    def test_concurrent_dequeue_loses_nothing(self):
        # recovery of 0 removes the rate limit, leaving a plain queue
        delay_queue = DelayQueue(0, 0)
        expected = [f"item{i}" for i in range(500)]
        for item in expected:
            delay_queue.enqueue(item)

        drained = []
        drained_lock = threading.Lock()
        start = threading.Barrier(8)

        def drain():
            start.wait()
            mine = []
            while True:
                item = delay_queue.dequeue()
                if item is None:
                    break
                mine.append(item)
            with drained_lock:
                drained.extend(mine)

        threads = [threading.Thread(target=drain) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # every item comes out exactly once - no IndexError, no duplicates, none lost
        self.assertEqual(sorted(expected), sorted(drained))
        self.assertTrue(delay_queue.is_empty())

    def test_rate_limit_holds_under_concurrent_dequeue(self):
        # this is the flood-kick case: two threads must not both get past the next_packet
        # check in the same tick
        for _ in range(5):
            delay_queue = DelayQueue(10, 0)
            for i in range(50):
                delay_queue.enqueue(f"item{i}")

            escaped = []
            escaped_lock = threading.Lock()
            start = threading.Barrier(8)

            def drain():
                start.wait()
                item = delay_queue.dequeue()
                if item is not None:
                    with escaped_lock:
                        escaped.append(item)

            threads = [threading.Thread(target=drain) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

            # a recovery of 10s means exactly one packet may leave, however many threads ask
            self.assertEqual(1, len(escaped), f"{len(escaped)} packets escaped the rate limit")

    def test_concurrent_enqueue_loses_nothing(self):
        delay_queue = DelayQueue(0, 0)
        start = threading.Barrier(8)

        def fill(offset):
            start.wait()
            for i in range(100):
                delay_queue.enqueue(f"item{offset}-{i}")

        threads = [threading.Thread(target=fill, args=(n,)) for n in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(800, len(delay_queue))
