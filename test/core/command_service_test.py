import re
import unittest
import unittest.mock

from core.command_service import CommandService
from core.dict_object import DictObject


class _AlwaysMatches:
    """A stand-in param-free command registration: matches anything, consumes nothing."""

    regex = re.compile("^(.*)$", re.IGNORECASE | re.DOTALL)


def make_service(callback):
    service = CommandService()
    service.db = unittest.mock.Mock()
    service.util = unittest.mock.Mock()
    service.usage_service = unittest.mock.Mock()
    service.access_service = unittest.mock.Mock()
    service.access_service.get_access_level.return_value = "member"
    service.character_service = unittest.mock.Mock()
    service.character_service.resolve_char_to_name.return_value = "Tester"
    service.command_alias_service = unittest.mock.Mock()
    service.command_alias_service.get_alias_command_str.return_value = None

    cmd_config = DictObject({"command": "test", "sub_command": "", "access_level": "member",
                             "channel": "msg", "enabled": 1})
    service.db.query.return_value = [cmd_config]
    service.handlers["test"] = [{"callback": callback, "params": [], "regex": _AlwaysMatches.regex,
                                 "check_access": lambda char_id, access_level: True,
                                 "description": "", "help": None, "extended_description": None}]
    return service


class CommandDispatchTest(unittest.IsolatedAsyncioTestCase):
    """
    Command handlers may be plain functions or coroutine functions. A coroutine that is called but
    never awaited returns a coroutine object instead of a reply: the user would get the repr of a
    coroutine, or nothing at all, and no error would be raised anywhere.
    """

    async def test_a_synchronous_handler_replies(self):
        service = make_service(lambda request: "sync reply")
        replies = []

        await service.process_command("test", "msg", 1, replies.append, None)

        self.assertEqual(["sync reply"], replies)

    async def test_a_coroutine_handler_is_awaited_before_its_reply_is_sent(self):
        async def handler(request):
            return "async reply"

        service = make_service(handler)
        replies = []

        await service.process_command("test", "msg", 1, replies.append, None)

        self.assertEqual(["async reply"], replies)

    async def test_a_coroutine_handler_that_replies_itself_sends_nothing_extra(self):
        async def handler(request):
            request.reply("from inside")
            return None

        service = make_service(handler)
        replies = []

        await service.process_command("test", "msg", 1, replies.append, None)

        self.assertEqual(["from inside"], replies)

    async def test_a_failing_coroutine_handler_is_reported_to_the_user(self):
        async def handler(request):
            raise Exception("handler blew up")

        service = make_service(handler)
        replies = []

        with unittest.mock.patch.object(service, "logger") as logger:
            await service.process_command("test", "msg", 1, replies.append, None)

        self.assertEqual(1, logger.error.call_count)
        self.assertEqual(["There was an error processing your request."], replies)


class FormatHelpTextTest(unittest.TestCase):

    def test_filters_by_access_level_and_resolves_it_once(self):
        levels = {"admin": {"level": 20}, "member": {"level": 60}, "all": {"level": 100}}
        service = CommandService()
        service.access_service = unittest.mock.Mock()
        service.access_service.get_access_level.return_value = levels["member"]
        service.access_service.get_access_level_by_label.side_effect = lambda label: levels[label]
        for command in ["a", "b", "c"]:
            service.handlers[command] = [{"help": f"help {command}", "params": []}]
        data = [DictObject({"command": "a", "sub_command": "", "access_level": "admin"}),
                DictObject({"command": "b", "sub_command": "", "access_level": "member"}),
                DictObject({"command": "c", "sub_command": "", "access_level": "all"})]

        help_text = service.format_help_text(data, 1)

        self.assertEqual("help b\n\nhelp c", help_text)
        # resolving an access level costs several queries, so it must not be repeated per row
        service.access_service.get_access_level.assert_called_once_with(1)
