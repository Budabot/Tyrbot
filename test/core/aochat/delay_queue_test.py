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
