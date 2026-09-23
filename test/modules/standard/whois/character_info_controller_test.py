import unittest
import unittest.mock
from functools import partial

from core.dict_object import DictObject
from modules.standard.whois.character_info_controller import CharacterInfoController


class _StubPacket:
    def __init__(self, char_id, online):
        self.char_id = char_id
        self.online = online


def make_controller():
    controller = CharacterInfoController()
    controller.bot = unittest.mock.Mock()
    controller.buddy_service = unittest.mock.Mock()
    controller.waiting_for_update = {}
    return controller


class BuddyStatusCallbackTest(unittest.IsolatedAsyncioTestCase):
    """
    !whois parks a callback here when the character's online status is not already known, and
    the BuddyAdded packet runs it. The callback is partial(show_output, ...) - a coroutine
    function - so the handler has to await it. Calling it without awaiting built a coroutine,
    dropped it, and answered the user nothing at all.
    """

    async def test_the_parked_callback_actually_runs(self):
        controller = make_controller()
        ran = []

        async def show_output(online_status):
            ran.append(online_status)

        controller.waiting_for_update[42] = DictObject({"char_id": 42, "name": "Danielka",
                                                        "callback": show_output})

        await controller.handle_buddy_status(None, _StubPacket(42, 1))

        self.assertEqual([True], ran)

    async def test_it_works_through_partial_the_way_whois_builds_it(self):
        # the real call site is partial(self.show_output, char, dimension, force_update,
        # reply=..., conn=...), so the awaited object is a partial, not a bare coroutine function
        controller = make_controller()
        seen = []

        async def show_output(char, dimension, online_status, reply):
            seen.append((char, dimension, online_status, reply))

        controller.waiting_for_update[42] = DictObject({
            "char_id": 42, "name": "Danielka",
            "callback": partial(show_output, "Danielka", 5, reply="reply-fn")})

        await controller.handle_buddy_status(None, _StubPacket(42, 0))

        self.assertEqual([("Danielka", 5, False, "reply-fn")], seen)

    async def test_the_buddy_slot_is_released_and_the_handler_unregistered(self):
        # the slot is finite, and the handler is registered per-!whois
        controller = make_controller()

        async def show_output(online_status):
            pass

        controller.waiting_for_update[42] = DictObject({"char_id": 42, "name": "Danielka",
                                                        "callback": show_output})

        await controller.handle_buddy_status(None, _StubPacket(42, 1))

        controller.buddy_service.remove_buddy.assert_called_once_with(
            42, CharacterInfoController.BUDDY_IS_ONLINE_TYPE)
        self.assertEqual({}, controller.waiting_for_update)
        self.assertEqual(1, controller.bot.remove_packet_handler.call_count)

    async def test_a_packet_for_a_character_nobody_asked_about_is_ignored(self):
        controller = make_controller()

        await controller.handle_buddy_status(None, _StubPacket(999, 1))

        self.assertEqual(0, controller.buddy_service.remove_buddy.call_count)
        self.assertEqual(0, controller.bot.remove_packet_handler.call_count)
