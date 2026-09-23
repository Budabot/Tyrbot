import asyncio
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


def make_bot():
    bot = Tyrbot()
    bot.loop = asyncio.get_running_loop()
    return bot


class MainThreadHandoffTest(unittest.IsolatedAsyncioTestCase):
    """
    run_on_main_thread is the hand-off other threads use to reach bot state. It used to queue onto
    a FifoQueue the main loop drained; it now schedules onto the loop with call_soon_threadsafe.
    The contract other threads rely on is unchanged, so these pin it.
    """

    async def test_work_is_deferred_and_runs_on_the_loop(self):
        bot = make_bot()
        ran_on = []

        worker = threading.Thread(target=lambda: bot.run_on_main_thread(
            lambda: ran_on.append(threading.current_thread().name)), name="worker")
        worker.start()
        worker.join()

        # scheduled from the worker thread, but must not have run there
        self.assertEqual([], ran_on)

        await asyncio.sleep(0)

        self.assertEqual([threading.current_thread().name], ran_on)

    async def test_callbacks_run_in_order(self):
        bot = make_bot()
        calls = []

        for i in range(3):
            bot.run_on_main_thread(lambda i=i: calls.append(i))
        await asyncio.sleep(0)

        self.assertEqual([0, 1, 2], calls)

    async def test_a_failing_callback_is_logged_and_does_not_stop_the_rest(self):
        bot = make_bot()
        calls = []

        def boom():
            raise Exception("callback blew up")

        # the failure is expected here, so the log it produces is captured and asserted on rather
        # than printed - an unmuted traceback in the suite output should always mean a real problem
        with unittest.mock.patch.object(bot, "logger") as logger:
            future = bot.run_on_main_thread(boom)
            bot.run_on_main_thread(lambda: calls.append("after"))
            await asyncio.sleep(0)

            # fire-and-forget callers never look at the future, so the error must still be logged
            self.assertEqual(1, logger.error.call_count)

        # one bad Discord event must not stop the rest of the queue
        self.assertEqual(["after"], calls)

        # ... and the failure is still reported to anyone waiting on it
        with self.assertRaises(Exception):
            future.result(timeout=0)

    async def test_the_callback_result_reaches_the_future(self):
        bot = make_bot()

        future = bot.run_on_main_thread(lambda: "the answer")
        self.assertFalse(future.done())

        await asyncio.sleep(0)

        self.assertEqual("the answer", future.result(timeout=0))

    async def test_a_coroutine_callback_is_awaited_before_the_future_resolves(self):
        # the MCP server's work is now a coroutine, because running a command is. If the coroutine
        # were not awaited the future would resolve with the coroutine object itself and the
        # command would silently never run
        bot = make_bot()

        async def work():
            await asyncio.sleep(0)
            return "awaited"

        future = bot.run_on_main_thread(work)
        for _ in range(10):
            if future.done():
                break
            await asyncio.sleep(0.01)

        self.assertEqual("awaited", future.result(timeout=0))

    async def test_a_failing_coroutine_callback_is_logged_and_reported(self):
        bot = make_bot()

        async def work():
            raise Exception("coroutine blew up")

        with unittest.mock.patch.object(bot, "logger") as logger:
            future = bot.run_on_main_thread(work)
            for _ in range(10):
                if future.done():
                    break
                await asyncio.sleep(0.01)

            self.assertEqual(1, logger.error.call_count)

        with self.assertRaises(Exception):
            future.result(timeout=0)

    async def test_waiting_caller_gets_the_result_across_threads(self):
        # this is the MCP server case: a request thread blocks until the loop runs its work
        bot = make_bot()
        got = []

        thread = threading.Thread(
            target=lambda: got.append(bot.run_on_main_thread(lambda: "done").result(timeout=5)),
            name="requester")
        thread.start()

        # the requester stays blocked until the loop gets a turn
        while thread.is_alive():
            await asyncio.sleep(0.01)
        thread.join(timeout=5)

        self.assertEqual(["done"], got)

    async def test_cancelled_callback_is_not_run(self):
        bot = make_bot()
        calls = []

        future = bot.run_on_main_thread(lambda: calls.append("should not run"))
        self.assertTrue(future.cancel())

        await asyncio.sleep(0)

        # a caller that gave up waiting must not have its work run behind its back
        self.assertEqual([], calls)


class IterateTest(unittest.IsolatedAsyncioTestCase):

    async def test_empty_queue_returns_none(self):
        bot = make_bot()
        self.assertIsNone(await bot.iterate(0))

    async def test_a_timeout_returns_none_rather_than_raising(self):
        bot = make_bot()
        self.assertIsNone(await bot.iterate(0.01))

    async def test_handlers_run_in_priority_order_and_coroutines_are_awaited(self):
        # dispatch is serial by design: each handler finishes before the next one starts, which is
        # what lets the 384 existing synchronous handlers keep their semantics
        bot = make_bot()
        calls = []

        async def slow_handler(conn, packet):
            await asyncio.sleep(0.01)
            calls.append("slow")

        def fast_handler(conn, packet):
            calls.append("fast")

        packet = unittest.mock.Mock(id=77)
        bot.register_packet_handler(77, slow_handler, priority=10)
        bot.register_packet_handler(77, fast_handler, priority=20)
        bot.incoming_queue.put_nowait((None, packet))

        self.assertIs(packet, await bot.iterate(1))
        self.assertEqual(["slow", "fast"], calls)

    async def test_iterate_refuses_to_run_off_the_main_thread(self):
        bot = Tyrbot()
        errors = []

        def call_iterate():
            # its own loop on its own thread: the dispatch chain assumes it owns the bot
            try:
                asyncio.run(bot.iterate(0))
            except RuntimeError as e:
                errors.append(str(e))

        worker = threading.Thread(target=call_iterate, name="worker")
        worker.start()
        worker.join(timeout=5)

        self.assertEqual(1, len(errors))
        self.assertIn("may only run on the main thread", errors[0])
        self.assertIn("worker", errors[0])
