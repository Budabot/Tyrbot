import asyncio

from core.decorators import instance
from core.logger import Logger


@instance("async_service")
class AsyncService:
    """
    Access to the bot's event loop.

    There is exactly one loop and the bot runs on it. The AO connections, the Discord client and
    the MCP server all share it, which is what makes bot state safe to touch from a coroutine
    without any locking: only one of them runs at a time.

    This used to own a second loop on a daemon thread, with the bot's main loop running beside it
    and the two handing work across via blocking futures. Those hand-offs are what this class
    exists to prevent now.
    """

    def __init__(self):
        self.logger = Logger(__name__)
        self.loop = None

    def attach(self, loop):
        """
        Called once by the bot when its loop starts running.
        """

        self.loop = loop

    def is_running(self):
        return self.loop is not None and self.loop.is_running()

    def is_on_loop_thread(self):
        try:
            return asyncio.get_running_loop() is self.loop
        except RuntimeError:
            # no loop running on this thread at all
            return False

    def run_coroutine(self, coro):
        """
        Call from any thread. Never blocks.

        Schedules `coro` on the bot's loop and returns a concurrent.futures.Future. Callers that
        ignore the future never learn that the coroutine failed, so anything fire-and-forget
        should log its own errors.
        """

        if not self.loop:
            raise RuntimeError("the bot's event loop is not running yet - it starts in Tyrbot.run()")

        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def run_until_complete(self, coro, timeout=None):
        """
        Call only from a thread that is NOT the bot's event loop. Blocks that thread until the
        coroutine finishes.

        Code already running on the loop must `await` instead. Blocking the loop on a coroutine
        that only the loop can run is a deadlock, so that case is refused rather than hung: a
        bot that stops answering is far harder to diagnose than a stack trace.
        """

        if self.is_on_loop_thread():
            coro.close()
            raise RuntimeError(
                "run_until_complete() was called from the bot's event loop, which would deadlock. "
                "Await the coroutine instead, or hand it to run_coroutine() if nothing needs the "
                "result.")

        return self.run_coroutine(coro).result(timeout)
