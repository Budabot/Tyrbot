from core.aochat.server_packets import BuddyAdded
from core.decorators import instance, command
from core.dict_object import DictObject
from core.command_param_types import Character


@instance()
class IsOnlineController:
    BUDDY_IS_ONLINE_TYPE = "is"

    def __init__(self):
        self.waiting_for_update = {}

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.buddy_service = registry.get_instance("buddy_service")

    @command(command="is", params=[Character("character")], access_level="all",
             description="Show online status for a character")
    def is_cmd(self, request, char):
        if not char.char_id:
            return "Could not find <highlight>%s<end>." % char.name
        else:
            online_status = self.buddy_service.is_online(char.char_id)
            if online_status is None:
                self.bot.add_packet_handler(BuddyAdded.id, self.handle_buddy_status)
                self.waiting_for_update[char.char_id] = DictObject({"char_id": char.char_id, "name": char.name, "reply": request.reply})
                self.buddy_service.add_buddy(char.char_id, self.BUDDY_IS_ONLINE_TYPE)
            else:
                return self.format_message(char.name, online_status)

    def handle_buddy_status(self, packet):
        char = self.waiting_for_update.get(packet.char_id)
        if char:
            char.reply(self.format_message(char.name, packet.online))
            self.buddy_service.remove_buddy(packet.char_id, self.BUDDY_IS_ONLINE_TYPE)
            del self.waiting_for_update[packet.char_id]
            if not self.waiting_for_update:
                self.bot.remove_packet_handler(BuddyAdded.id, self.handle_buddy_status)

    def format_message(self, char_name, online_status):
        return "%s is %s." % (char_name, "<green>online<end>" if online_status else "<red>offline<end>")
