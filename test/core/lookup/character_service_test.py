import time
import unittest

from core.lookup.character_service import CharacterService


class _StubConn:
    def __init__(self):
        self.sent = []

    def send_packet(self, packet):
        self.sent.append(packet)


class _StubBot:
    """
    Stands in for the main loop. `resolves_after` makes a name appear in the service's cache once
    iterate() has been called that many times, which is how a real lookup response arrives.
    """

    def __init__(self, service, resolves_after=None, name=None, char_id=None, packet_gap_after=None):
        self.service = service
        self.resolves_after = resolves_after
        self.name = name
        self.char_id = char_id
        self.packet_gap_after = packet_gap_after
        self.iterate_calls = 0
        self.conn = _StubConn()

    def get_primary_conn(self):
        return self.conn

    def iterate(self, timeout=0.1):
        self.iterate_calls += 1
        if self.resolves_after is not None and self.iterate_calls >= self.resolves_after:
            self.service.name_to_id[self.name] = self.char_id
        if self.packet_gap_after is not None and self.iterate_calls >= self.packet_gap_after:
            return None
        # a truthy packet, so the wait loop keeps going
        return object()


def make_service(**kwargs):
    service = CharacterService()
    service.bot = _StubBot(service, **kwargs)
    return service


class CharacterServiceDeadlineTest(unittest.TestCase):

    def test_expired_shared_deadline_does_not_wait_at_all(self):
        service = make_service()

        result = service.resolve_char_to_id("Litigator", deadline=time.time() - 1)

        self.assertIsNone(result)
        # the whole point of a shared budget: once spent, later names cost nothing
        self.assertEqual(0, service.bot.iterate_calls)

    def test_request_still_goes_out_after_the_deadline(self):
        service = make_service()

        service.resolve_char_to_id("Litigator", deadline=time.time() - 1)

        # responses arrive in bulk minutes later, so sending is still worthwhile - it is only the
        # waiting that is skipped
        self.assertEqual(1, len(service.bot.conn.sent))

    def test_shared_deadline_is_not_reset_per_name(self):
        service = make_service(packet_gap_after=2)
        deadline = time.time() + 0.20

        service.resolve_char_to_id("Aaa", deadline=deadline)
        time.sleep(0.25)
        before = service.bot.iterate_calls
        service.resolve_char_to_id("Bbb", deadline=deadline)

        # the second name inherits the spent budget rather than starting a fresh one
        self.assertEqual(before, service.bot.iterate_calls)

    def test_resolved_name_is_returned(self):
        service = make_service(resolves_after=3, name="Litigator", char_id=428852287)

        result = service.resolve_char_to_id("Litigator", deadline=time.time() + 30)

        self.assertEqual(428852287, result)

    def test_cached_name_skips_the_lookup(self):
        service = make_service()
        service.name_to_id["Litigator"] = 428852287

        result = service.resolve_char_to_id("Litigator", deadline=time.time() - 1)

        self.assertEqual(428852287, result)
        self.assertEqual([], service.bot.conn.sent)

    def test_without_a_deadline_each_name_gets_its_own_budget(self):
        service = make_service(packet_gap_after=2)
        service.CHAR_LOOKUP_TIMEOUT = 30

        service.resolve_char_to_id("Aaa")
        first = service.bot.iterate_calls
        service.resolve_char_to_id("Bbb")

        # unlike the shared case above, the second name waits again
        self.assertGreater(service.bot.iterate_calls, first)

    def test_numeric_input_is_passed_through(self):
        service = make_service()

        self.assertEqual(42, service.resolve_char_to_id(42))
        self.assertEqual(42, service.resolve_char_to_id("42"))
        self.assertEqual([], service.bot.conn.sent)
