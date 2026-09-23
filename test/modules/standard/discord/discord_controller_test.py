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


class DiscordStateReadTest(unittest.IsolatedAsyncioTestCase):
    """
    discord.py's state belongs to the loop its client runs on, which is now the bot's own loop.
    These reads used to block the main thread on a second loop's future; they are awaited instead,
    which is what keeps them from deadlocking now that there is only one loop.
    """

    async def asyncSetUp(self):
        self.async_service = AsyncService()
        self.async_service.attach(asyncio.get_running_loop())

        self.ran_on = []
        self.controller = DiscordController()
        self.controller.async_service = self.async_service
        self.controller.client = _StubClient(self.ran_on)
        self.controller.dtask = _StubTask()

    async def test_channel_read_returns_data_from_the_loop(self):
        channels = await self.controller.get_text_channels()

        self.assertEqual(["general"], [c.name for c in channels])
        self.assertEqual("Guild", channels[0].guild_name)
        self.assertEqual([threading.current_thread().name], self.ran_on)

    async def test_server_read_returns_data_from_the_loop(self):
        servers = await self.controller.get_servers()

        self.assertEqual([3], [s.id for s in servers])
        self.assertEqual(2, servers[0].member_count)

    async def test_set_channel_runs_on_the_loop(self):
        # a setting change listener, which cannot await - so it schedules the update
        self.controller.update_discord_channel("discord_channel_id", None, "7")
        for _ in range(20):
            if self.controller.client.default_channel_id is not None:
                break
            await asyncio.sleep(0.01)

        self.assertEqual("7", self.controller.client.default_channel_id)

    async def test_reads_return_default_when_not_connected(self):
        self.controller.dtask = None  # ie. client not running

        self.assertEqual([], await self.controller.get_text_channels())
        self.assertEqual([], await self.controller.get_servers())
        # nothing was dispatched to the client
        self.assertEqual([], self.ran_on)

    async def test_reads_return_default_when_there_is_no_client(self):
        self.controller.client = None

        self.assertEqual([], await self.controller.get_text_channels())
        self.assertEqual([], await self.controller.get_servers())


class DiscordSendLatencyTest(unittest.IsolatedAsyncioTestCase):
    """The outbound relay used to poll the queue every 100ms; it is now pushed."""

    async def asyncSetUp(self):
        self.async_service = AsyncService()
        self.async_service.attach(asyncio.get_running_loop())

        self.controller = DiscordController()
        self.controller.async_service = self.async_service
        self.controller.client = _StubClient([])
        self.controller.dtask = _StubTask()
        self.controller.aoqueue = asyncio.Queue()

    async def test_message_reaches_the_queue_without_polling(self):
        sent_at = time.time()
        self.controller.send_to_discord("msg", "hello")

        dtype, message = await asyncio.wait_for(self.controller.aoqueue.get(), timeout=5)
        elapsed = time.time() - sent_at

        self.assertEqual(("msg", "hello"), (dtype, message))
        # the old poll made this up to 100ms; pushing should be sub-millisecond
        self.assertLess(elapsed, 0.05, f"took {elapsed*1000:.1f}ms - is it still polling?")

    async def test_messages_keep_their_order(self):
        for i in range(10):
            self.controller.send_to_discord("msg", f"m{i}")

        received = [(await asyncio.wait_for(self.controller.aoqueue.get(), timeout=5))[1] for _ in range(10)]
        self.assertEqual([f"m{i}" for i in range(10)], received)

    async def test_send_without_a_client_is_reported_not_swallowed(self):
        self.controller.aoqueue = None

        with self.assertLogs(level="WARNING") as logged:
            self.controller.send_to_discord("msg", "dropped")

        self.assertTrue(any("not running" in line for line in logged.output))
