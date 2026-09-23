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

    async def drain():
        return None

    conn.drain_outgoing_packets = drain

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


class _StubWriter:
    """Records what reached the socket, in order."""

    def __init__(self):
        self.writes = []

    def write(self, data):
        self.writes.append(data)

    async def drain(self):
        return None


class _StubPacket:
    id = 99

    def __init__(self, body):
        self.body = body

    def to_bytes(self):
        return self.body.encode("utf-8")


def make_conn():
    conn = Conn("conn1", None, async_service=None)
    conn.writer = _StubWriter()
    return conn


def sent(conn):
    # strip the 4-byte header each packet is framed with
    return [w[4:].decode("utf-8") for w in conn.writer.writes]


class OutgoingQueueTest(unittest.IsolatedAsyncioTestCase):

    async def test_send_packet_only_queues(self):
        # it used to block the caller on async_service.run_until_complete() until the write
        # finished. Nothing may reach the socket on the caller's thread: on a single event loop
        # that is a self-deadlock, since the loop would be waiting on a coroutine only it can run
        conn = make_conn()

        conn.send_packet(_StubPacket("a"))

        self.assertEqual([], sent(conn))

        await conn.drain_outgoing_packets()
        self.assertEqual(["a"], sent(conn))

    async def test_add_packets_to_queue_only_queues(self):
        conn = make_conn()

        conn.add_packets_to_queue([_StubPacket("a")])

        self.assertEqual([], sent(conn))

    async def test_immediate_packets_bypass_the_rate_limited_queue(self):
        conn = make_conn()

        conn.add_packets_to_queue([_StubPacket("rate-limited")])
        conn.send_packet(_StubPacket("immediate"))

        await conn.drain_outgoing_packets()

        # the DelayQueue releases one packet per drain, so both go out here - but the immediate
        # one must be first, which is the ordering the old direct-to-socket send gave it
        self.assertEqual(["immediate", "rate-limited"], sent(conn))

    async def test_immediate_packets_keep_their_order(self):
        conn = make_conn()

        for body in ["a", "b", "c"]:
            conn.send_packet(_StubPacket(body))

        await conn.drain_outgoing_packets()

        self.assertEqual(["a", "b", "c"], sent(conn))

    async def test_send_while_disconnected_is_logged_and_does_not_stop_the_drain(self):
        # the window between a disconnect and the packet loop noticing. The old fire-and-forget
        # send dropped these silently - nothing ever read the future it returned
        conn = make_conn()
        conn.writer = None
        conn.send_packet(_StubPacket("lost"))

        with unittest.mock.patch.object(conn, "logger") as logger:
            await conn.drain_outgoing_packets()

        self.assertEqual(1, logger.error.call_count)

    async def test_connection_error_propagates_so_the_loop_can_fail_the_conn_over(self):
        # distinct from "not connected": a dead socket must reach the packet loop's handler,
        # which reports the failure and triggers a reconnect, rather than being logged and dropped
        conn = make_conn()

        def write(data):
            raise ConnectionResetError("connection reset")

        conn.writer.write = write
        conn.send_packet(_StubPacket("a"))

        with self.assertRaises(ConnectionResetError):
            await conn.drain_outgoing_packets()
