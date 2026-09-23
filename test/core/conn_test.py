import asyncio
import unittest
import unittest.mock

from core.bot_status import BotStatus
from core.conn import Conn
from core.fifo_queue import FifoQueue


def run_packet_loop(read_packet):
    """
    Drives one pass of the packet loop with a stubbed reader, and reports whether
    failure_callback fired. Every path under test raises, so the loop always exits.
    """

    failures = []
    conn = Conn("conn1", lambda: failures.append(True), async_service=None)
    conn._async_read_packet = read_packet
    conn.check_outgoing_message_queue = lambda: None

    with unittest.mock.patch.object(conn, "logger"):
        asyncio.run(conn._async_packet_loop(FifoQueue(), None, lambda: BotStatus.RUN))

    return failures


class PacketLoopExceptionTest(unittest.TestCase):

    def test_cancellation_breaks_without_reporting_a_failure(self):
        # the `except asyncio.CancelledError` handler is reachable: CancelledError derives from
        # BaseException in 3.8+, so the `except Exception` beside it never catches it. If this
        # stops holding, shutdown would be reported as a connection failure and trigger a reconnect
        async def read_packet(timeout=1):
            raise asyncio.CancelledError()

        self.assertEqual([], run_packet_loop(read_packet))

    def test_connection_error_reports_a_failure(self):
        async def read_packet(timeout=1):
            raise ConnectionResetError("connection reset")

        self.assertEqual([True], run_packet_loop(read_packet))

    def test_eof_reports_a_failure(self):
        async def read_packet(timeout=1):
            raise EOFError()

        self.assertEqual([True], run_packet_loop(read_packet))

    def test_unexpected_error_reports_a_failure_and_breaks(self):
        # the deleted fourth handler would have slept and continued here instead of breaking;
        # breaking and reporting is the fail-closed choice, so pin it
        async def read_packet(timeout=1):
            raise ValueError("something unexpected")

        self.assertEqual([True], run_packet_loop(read_packet))
