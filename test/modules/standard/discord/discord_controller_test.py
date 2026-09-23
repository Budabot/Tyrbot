import asyncio
import threading
import time
import unittest

from core.async_service import AsyncService
from core.dict_object import DictObject
# noinspection PyUnresolvedReferences
from core.util import Util  # noqa: F401 - registers 'util', which @timerevent needs at import time
from modules.standard.discord.discord_controller import DiscordController


class DiscordControllerTest(unittest.TestCase):

    def test_format_message(self):
        discord_controller = DiscordController()

        msg = "Title <header2>Header</header2> <highlight>message</highlight>"

        self.assertEqual("Title ```yaml\nHeader\n``` `message`", discord_controller.format_message(msg))


class _StubTask:
    def done(self):
        return False


class _StubClient:
    """Stands in for DiscordWrapper; records which thread its coroutines run on."""

    def __init__(self, ran_on):
        self.ran_on = ran_on
        self.default_channel_id = None

    def is_ready(self):
        return True

    async def get_channel_snapshot(self):
        self.ran_on.append(threading.current_thread().name)
        return [DictObject({"id": 7, "name": "general", "guild_name": "Guild"})]

    async def get_server_snapshot(self):
        self.ran_on.append(threading.current_thread().name)
        return [DictObject({"id": 3, "name": "Guild", "member_count": 2,
                            "owner_nick": None, "owner_str": "owner#1234"})]

    async def set_default_channel(self, channel_id):
        self.ran_on.append(threading.current_thread().name)
        self.default_channel_id = channel_id
        return True


class DiscordStateReadTest(unittest.TestCase):

    def setUp(self):
        self.async_service = AsyncService()
        self.async_service.start_loop()

        self.ran_on = []
        self.controller = DiscordController()
        self.controller.async_service = self.async_service
        self.controller.client = _StubClient(self.ran_on)
        self.controller.dtask = _StubTask()

    def tearDown(self):
        self.async_service.stop_loop()

    def test_channel_read_happens_on_the_loop_thread(self):
        channels = self.controller.get_text_channels()

        self.assertEqual(["general"], [c.name for c in channels])
        self.assertEqual("Guild", channels[0].guild_name)

        # the point of the exercise: discord state was read on the loop, not on this thread
        self.assertEqual(["AsyncServiceThread"], self.ran_on)
        self.assertNotEqual(threading.current_thread().name, self.ran_on[0])

    def test_server_read_happens_on_the_loop_thread(self):
        servers = self.controller.get_servers()

        self.assertEqual([3], [s.id for s in servers])
        self.assertEqual(2, servers[0].member_count)
        self.assertEqual(["AsyncServiceThread"], self.ran_on)

    def test_set_channel_happens_on_the_loop_thread(self):
        self.controller.update_discord_channel("discord_channel_id", None, "7")

        self.assertEqual("7", self.controller.client.default_channel_id)
        self.assertEqual(["AsyncServiceThread"], self.ran_on)

    def test_reads_return_default_when_not_connected(self):
        self.controller.dtask = None  # ie. client not running

        self.assertEqual([], self.controller.get_text_channels())
        self.assertEqual([], self.controller.get_servers())
        # nothing was dispatched to the loop
        self.assertEqual([], self.ran_on)

    def test_reads_return_default_when_there_is_no_client(self):
        self.controller.client = None

        self.assertEqual([], self.controller.get_text_channels())
        self.assertEqual([], self.controller.get_servers())


class DiscordSendLatencyTest(unittest.TestCase):
    """The outbound relay used to poll the queue every 100ms; it is now pushed."""

    def setUp(self):
        self.async_service = AsyncService()
        self.async_service.start_loop()

        self.controller = DiscordController()
        self.controller.async_service = self.async_service
        self.controller.client = _StubClient([])
        self.controller.dtask = _StubTask()
        self.controller.aoqueue = asyncio.Queue()

    def tearDown(self):
        self.async_service.stop_loop()

    def _consume_one(self):
        """Await one item on the loop, the way DiscordWrapper.relay_message does."""
        return self.async_service.run_coroutine(self.controller.aoqueue.get())

    def test_message_reaches_the_loop_without_polling(self):
        consumer = self._consume_one()

        sent_at = time.time()
        self.controller.send_to_discord("msg", "hello")
        dtype, message = consumer.result(timeout=5)
        elapsed = time.time() - sent_at

        self.assertEqual(("msg", "hello"), (dtype, message))
        # the old poll made this up to 100ms; pushing should be sub-millisecond
        self.assertLess(elapsed, 0.05, f"took {elapsed*1000:.1f}ms - is it still polling?")

    def test_messages_keep_their_order(self):
        for i in range(10):
            self.controller.send_to_discord("msg", f"m{i}")

        received = [self._consume_one().result(timeout=5)[1] for _ in range(10)]
        self.assertEqual([f"m{i}" for i in range(10)], received)

    def test_send_without_a_client_is_reported_not_swallowed(self):
        self.controller.aoqueue = None

        with self.assertLogs(level="WARNING") as logged:
            self.controller.send_to_discord("msg", "dropped")

        self.assertTrue(any("not running" in line for line in logged.output))
