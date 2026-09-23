import asyncio
import threading
import unittest

from core.async_service import AsyncService


class AsyncServiceTest(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.async_service = AsyncService()
        self.async_service.attach(asyncio.get_running_loop())

    async def test_run_coroutine_schedules_onto_the_loop(self):
        async def sample_coro():
            await asyncio.sleep(0.01)
            return "hello_async"

        future = self.async_service.run_coroutine(sample_coro())

        # a concurrent.futures.Future, so it cannot be awaited here - it is for other threads.
        # Yield until the loop has run the coroutine it wraps.
        while not future.done():
            await asyncio.sleep(0.01)

        self.assertEqual("hello_async", future.result())

    async def test_run_until_complete_from_the_loop_is_refused_rather_than_deadlocking(self):
        # blocking the loop on a coroutine that only the loop can run would hang the whole bot.
        # A stack trace is recoverable; a bot that silently stops answering is not
        async def sample_coro():
            return "never reached"

        coro = sample_coro()
        with self.assertRaises(RuntimeError) as ctx:
            self.async_service.run_until_complete(coro)

        self.assertIn("deadlock", str(ctx.exception))

    async def test_run_until_complete_works_from_another_thread(self):
        async def sample_coro():
            await asyncio.sleep(0.01)
            return "from a worker"

        results = []

        def worker():
            results.append(self.async_service.run_until_complete(sample_coro(), timeout=5))

        thread = threading.Thread(target=worker)
        thread.start()
        while thread.is_alive():
            await asyncio.sleep(0.01)
        thread.join()

        self.assertEqual(["from a worker"], results)

    async def test_run_coroutine_without_a_loop_is_an_error(self):
        detached = AsyncService()

        coro = asyncio.sleep(0)
        with self.assertRaises(RuntimeError):
            detached.run_coroutine(coro)
        coro.close()
