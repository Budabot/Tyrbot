import threading
import unittest
import unittest.mock

from core.aochat.mmdb_parser import MMDBParser
from core.aochat.server_packets import SystemMessage, PublicChannelMessage
from core.tyrbot import Tyrbot


class TyrbotTest(unittest.TestCase):

    def test_system_message_ext_msg_handling(self):
        # tests SystemMessage with an ExtendedMessage containing a reference param
        mmdb_parser = MMDBParser("./text.mdb")
        bot = Tyrbot()
        bot.mmdb_parser = mmdb_parser

        packet = SystemMessage.from_bytes(b'\x00\x05\xc0\xbe\x00\x00\x00\x00\x03@\xe2E\x00\x05l\x0f\xcf\xcaw')
        packet = bot.system_message_ext_msg_handling(packet)

        self.assertEqual("Could not send message to offline player: the message is too big to fit in the inbox", packet.extended_message.get_message())

    def test_public_channel_message_ext_msg_handling(self):
        # tests PublicChannelMessage with an ExtendedMessage containing a tower attack
        mmdb_parser = MMDBParser("./text.mdb")
        bot = Tyrbot()
        bot.mmdb_parser = mmdb_parser

        packet = PublicChannelMessage.from_bytes(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x53~&!!!&r!5b/RR!!!8S!!!!#s\x09TestOrg1s\x09TestCharR!!!8S!!!!"s\x09TestOrg2s\x05Morti!!!Dui!!!Eu~\x00\x04Test')

        packet = bot.public_channel_message_ext_msg_handling(packet)

        self.assertEqual("The omni organization TestOrg1 just entered a state of war! TestChar attacked the clan organization TestOrg2's tower in Mort at location (3059,3144).", packet.extended_message.get_message())

    def test_register_packet_handler(self):
        packet_id = 1
        bot = Tyrbot()

        def callback(conn, packet):
            pass

        def callback2(conn, packet):
            pass

        bot.register_packet_handler(packet_id, callback2, 20)
        bot.register_packet_handler(packet_id, callback)
        bot.register_packet_handler(packet_id, callback, 50)
        bot.register_packet_handler(packet_id, callback, 10)
        self.assertEqual(
            [{'priority': 10, 'handler': callback}, {'priority': 20, 'handler': callback2}, {'priority': 50, 'handler': callback}, {'priority': 50, 'handler': callback}],
            bot.packet_handlers.get(packet_id))

    def test_remove_packet_handler(self):
        packet_id = 1
        bot = Tyrbot()

        def callback(conn, packet):
            pass

        def callback2(conn, packet):
            pass

        bot.register_packet_handler(packet_id, callback2, 20)
        bot.register_packet_handler(packet_id, callback)
        bot.register_packet_handler(packet_id, callback, 50)
        bot.register_packet_handler(packet_id, callback, 10)
        bot.remove_packet_handler(packet_id, callback2)
        self.assertEqual(
            [{'priority': 10, 'handler': callback}, {'priority': 50, 'handler': callback}, {'priority': 50, 'handler': callback}],
            bot.packet_handlers.get(packet_id))

    def test_run_on_main_thread_defers_work(self):
        bot = Tyrbot()
        ran_on = []

        def callback():
            ran_on.append(threading.current_thread().name)

        worker = threading.Thread(target=lambda: bot.run_on_main_thread(callback), name="worker")
        worker.start()
        worker.join()

        # queued from the worker thread, but must not have run there
        self.assertEqual([], ran_on)

        bot.process_main_thread_queue()

        self.assertEqual([threading.current_thread().name], ran_on)

    def test_process_main_thread_queue_runs_in_order(self):
        bot = Tyrbot()
        calls = []

        for i in range(3):
            bot.run_on_main_thread(lambda i=i: calls.append(i))
        bot.process_main_thread_queue()

        self.assertEqual([0, 1, 2], calls)

    def test_process_main_thread_queue_survives_a_failing_callback(self):
        bot = Tyrbot()
        calls = []

        def boom():
            raise Exception("callback blew up")

        future = bot.run_on_main_thread(boom)
        bot.run_on_main_thread(lambda: calls.append("after"))

        # the failure is expected here, so the log it produces is captured and asserted on rather
        # than printed - an unmuted traceback in the suite output should always mean a real problem
        with unittest.mock.patch.object(bot, "logger") as logger:
            bot.process_main_thread_queue()

        # fire-and-forget callers never look at the future, so the error must still be logged
        self.assertEqual(1, logger.error.call_count)

        # one bad Discord event must not stop the rest of the queue
        self.assertEqual(["after"], calls)

        # ... and the failure is still reported to anyone waiting on it
        with self.assertRaises(Exception):
            future.result(timeout=0)

    def test_run_on_main_thread_returns_the_callback_result(self):
        bot = Tyrbot()

        future = bot.run_on_main_thread(lambda: "the answer")
        self.assertFalse(future.done())

        bot.process_main_thread_queue()

        self.assertEqual("the answer", future.result(timeout=0))

    def test_waiting_caller_gets_the_result_across_threads(self):
        # this is the MCP server case: a request thread blocks until the main loop runs its work
        bot = Tyrbot()
        got = []

        def requester():
            got.append(bot.run_on_main_thread(lambda: "done").result(timeout=5))

        thread = threading.Thread(target=requester, name="requester")
        thread.start()

        # the requester is blocked until the main loop drains the queue
        while bot.main_thread_queue.empty():
            pass
        bot.process_main_thread_queue()

        thread.join(timeout=5)
        self.assertEqual(["done"], got)

    def test_cancelled_callback_is_not_run(self):
        bot = Tyrbot()
        calls = []

        future = bot.run_on_main_thread(lambda: calls.append("should not run"))
        self.assertTrue(future.cancel())

        bot.process_main_thread_queue()

        # a caller that gave up waiting must not have its work run behind its back
        self.assertEqual([], calls)

    def test_iterate_refuses_to_run_off_the_main_thread(self):
        bot = Tyrbot()
        errors = []

        def call_iterate():
            try:
                bot.iterate(0)
            except RuntimeError as e:
                errors.append(str(e))

        worker = threading.Thread(target=call_iterate, name="worker")
        worker.start()
        worker.join(timeout=5)

        # a second thread in the dispatch loop steals packets from the main loop - it must be loud
        self.assertEqual(1, len(errors))
        self.assertIn("may only run on the main thread", errors[0])
        self.assertIn("worker", errors[0])

    def test_iterate_runs_on_the_main_thread(self):
        bot = Tyrbot()

        # no packets queued, so it returns the default rather than raising
        self.assertIsNone(bot.iterate(0))

    def test_process_main_thread_queue_is_a_noop_when_empty(self):
        bot = Tyrbot()
        bot.process_main_thread_queue()
        self.assertTrue(bot.main_thread_queue.empty())
