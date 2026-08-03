import asyncio
import threading

from core.decorators import instance
from core.logger import Logger


@instance("async_service")
class AsyncService:
    def __init__(self):
        self.logger = Logger(__name__)
        self.loop = None
        self.thread = None
        self._running = False

    def start_loop(self):
        """
        Initializes and starts the dedicated background asyncio event loop thread if not already running.
        Spawns a daemon thread ('AsyncServiceThread') that runs loop.run_forever().
        """
        if self._running:
            return

        self._running = True
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_event_loop, name="AsyncServiceThread", daemon=True)
        self.thread.start()
        self.logger.info("AsyncService background asyncio event loop started.")

    def _run_event_loop(self):
        """
        Target function for AsyncServiceThread. Sets the thread's event loop and runs it forever.
        """
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        finally:
            try:
                pending = asyncio.all_tasks(self.loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            self.loop.close()

    def stop_loop(self):
        """
        Gracefully signals the background asyncio event loop to stop and waits for the thread to exit.
        """
        if not self._running:
            return

        self._running = False
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("AsyncService background asyncio event loop stopped.")

    def is_running(self):
        """
        Returns True if the background event loop is running and active.
        """
        return self._running and self.loop is not None and self.loop.is_running()

    def run_coroutine(self, coro):
        """
        Schedules a coroutine to run asynchronously on the background asyncio event loop thread.

        Non-blocking: returns a concurrent.futures.Future immediately without waiting for
        the coroutine to complete. Use for background tasks (e.g. packet loops, fire-and-forget sends).
        """
        if not self._running or not self.loop:
            self.start_loop()
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def run_until_complete(self, coro, timeout=None):
        """
        Submits a coroutine to the background asyncio event loop and blocks the calling thread
        until execution completes or the optional timeout expires.

        Synchronous / Blocking: returns the direct result of the coroutine. Re-raises any
        exceptions thrown by the coroutine to the caller. Use when synchronous code requires
        an immediate result from an async operation (e.g. connect, login, synchronous send_packet).
        """
        future = self.run_coroutine(coro)
        return future.result(timeout=timeout)
