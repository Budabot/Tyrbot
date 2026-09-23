import unittest

from core.buddy_service import BuddyService


class _StubConn:
    def __init__(self, conn_id, char_id=1):
        self.id = conn_id
        self.char_id = char_id
        self.buddy_list = {}
        self.sent = []

    def send_packet(self, packet):
        self.sent.append(packet)


class _StubBot:
    def __init__(self, *conns):
        self.conns = {conn.id: conn for conn in conns}

    def get_conns(self):
        return list(self.conns.items())


def make_service(*conns):
    service = BuddyService()
    service.bot = _StubBot(*conns)
    return service


class RemoveAllBuddiesByTypeTest(unittest.TestCase):

    def test_removes_the_type_and_sends_buddy_remove(self):
        conn = _StubConn("conn1")
        conn.buddy_list[100] = {"online": 1, "types": ["orglist"], "conn_id": "conn1"}
        service = make_service(conn)

        service.remove_all_buddies_by_type("orglist")

        self.assertEqual([], conn.buddy_list[100]["types"])
        self.assertEqual(1, len(conn.sent))
        self.assertEqual(100, conn.sent[0].char_id)

    def test_buddy_with_another_type_is_kept(self):
        conn = _StubConn("conn1")
        conn.buddy_list[100] = {"online": 1, "types": ["orglist", "member"], "conn_id": "conn1"}
        service = make_service(conn)

        service.remove_all_buddies_by_type("orglist")

        # still wanted for another reason, so the buddy stays on the chat server
        self.assertEqual(["member"], conn.buddy_list[100]["types"])
        self.assertEqual([], conn.sent)

    def test_buddies_of_other_types_are_untouched(self):
        conn = _StubConn("conn1")
        conn.buddy_list[100] = {"online": 1, "types": ["member"], "conn_id": "conn1"}
        service = make_service(conn)

        service.remove_all_buddies_by_type("orglist")

        self.assertEqual(["member"], conn.buddy_list[100]["types"])
        self.assertEqual([], conn.sent)

    def test_spans_multiple_conns(self):
        conn1 = _StubConn("conn1", char_id=1)
        conn2 = _StubConn("conn2", char_id=2)
        conn1.buddy_list[100] = {"online": 1, "types": ["orglist"], "conn_id": "conn1"}
        conn2.buddy_list[200] = {"online": 1, "types": ["orglist"], "conn_id": "conn2"}
        service = make_service(conn1, conn2)

        service.remove_all_buddies_by_type("orglist")

        self.assertEqual(100, conn1.sent[0].char_id)
        self.assertEqual(200, conn2.sent[0].char_id)

    def test_removes_every_matching_buddy(self):
        # the original raised TypeError on the first entry, so a timed-out orglist leaked every
        # one of its buddies and permanently consumed those slots
        conn = _StubConn("conn1")
        for char_id in range(100, 150):
            conn.buddy_list[char_id] = {"online": 1, "types": ["orglist"], "conn_id": "conn1"}
        service = make_service(conn)

        service.remove_all_buddies_by_type("orglist")

        self.assertEqual(50, len(conn.sent))
        self.assertTrue(all(b["types"] == [] for b in conn.buddy_list.values()))

    def test_empty_buddy_list_is_a_noop(self):
        conn = _StubConn("conn1")
        service = make_service(conn)

        service.remove_all_buddies_by_type("orglist")

        self.assertEqual([], conn.sent)
