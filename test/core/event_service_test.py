import unittest
import unittest.mock

from core.event_service import EventService


class CallHandlerTest(unittest.IsolatedAsyncioTestCase):
    """
    Handlers are registered the same way whether they are plain functions or coroutine functions,
    so the dispatch has to cope with both. A coroutine that is called but never awaited does
    nothing at all and raises nothing - the event would just silently not happen.
    """

    def setUp(self):
        self.service = EventService()

    async def test_a_synchronous_handler_runs(self):
        calls = []
        self.service.handlers["h"] = lambda event_type, event_data: calls.append(event_type)

        await self.service.call_handler("h", "connect", None)

        self.assertEqual(["connect"], calls)

    async def test_a_coroutine_handler_is_awaited_to_completion(self):
        calls = []

        async def handler(event_type, event_data):
            calls.append("started")
            calls.append("finished")

        self.service.handlers["h"] = handler

        await self.service.call_handler("h", "connect", None)

        self.assertEqual(["started", "finished"], calls)

    async def test_handlers_run_serially_one_after_another(self):
        # serial by design: an event handler finishes before the next one starts, exactly as when
        # everything was synchronous
        import asyncio
        calls = []

        async def slow(event_type, event_data):
            await asyncio.sleep(0.01)
            calls.append("slow")

        def fast(event_type, event_data):
            calls.append("fast")

        self.service.handlers["slow"] = slow
        self.service.handlers["fast"] = fast

        await self.service.call_handler("slow", "e", None)
        await self.service.call_handler("fast", "e", None)

        self.assertEqual(["slow", "fast"], calls)

    async def test_a_failing_coroutine_handler_is_logged_and_does_not_escape(self):
        async def handler(event_type, event_data):
            raise Exception("handler blew up")

        self.service.handlers["h"] = handler

        with unittest.mock.patch.object(self.service, "logger") as logger:
            await self.service.call_handler("h", "connect", None)

        # one bad handler must not stop the event, but it must be loud
        self.assertEqual(1, logger.error.call_count)

    async def test_a_missing_handler_is_reported(self):
        with unittest.mock.patch.object(self.service, "logger") as logger:
            await self.service.call_handler("nope", "connect", None)

        self.assertEqual(1, logger.error.call_count)
