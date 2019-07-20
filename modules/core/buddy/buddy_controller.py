import hjson

from core.decorators import instance, command, timerevent
from core.command_param_types import Any, Const, Options, Character
from core.chat_blob import ChatBlob
from core.logger import Logger
from core.translation_service import TranslationService


@instance()
class BuddyController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.character_service = registry.get_instance("character_service")
        self.buddy_service = registry.get_instance("buddy_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    def start(self):
        self.ts.register_translation("module/buddy", self.load_buddy_msg)

    def load_buddy_msg(self):
        with open("modules/core/buddy/buddy.msg", mode="r", encoding="UTF-8") as f:
            return hjson.load(f)

    @command(command="buddylist", params=[], access_level="admin",
             description="Show characters on the buddy list")
    def buddylist_cmd(self, request):
        buddy_list = []
        for char_id, buddy in self.buddy_service.get_all_buddies().items():
            char_name = self.character_service.resolve_char_to_name(char_id, "Unknown(%d)" % char_id)
            buddy_list.append([char_name, buddy["online"], ",".join(buddy["types"])])

        blob = self.format_buddies(buddy_list)

        return ChatBlob(self.getresp("module/buddy", "blob_title", {"amount": len(buddy_list)}), blob)

    @command(command="buddylist", params=[Const("add"), Character("character"), Any("type")], access_level="admin",
             description="Add a character to the buddy list")
    def buddylist_add_cmd(self, request, _, char, buddy_type):
        buddy_type = buddy_type.lower()

        if char.char_id:
            self.buddy_service.add_buddy(char.char_id, buddy_type)
            return self.getresp("module/buddy", "add_success", {"char": char.name, "type": buddy_type})
        else:
            return self.getresp("global", "char_not_found", {"char": char.name})

    @command(command="buddylist", params=[Options(["rem", "remove"]), Const("all")], access_level="admin",
             description="Remove all characters from the buddy list")
    def buddylist_remove_all_cmd(self, request, _1, _2):
        count = 0
        for char_id, buddy in self.buddy_service.get_all_buddies().items():
            self.buddy_service.remove_buddy(char_id, None, True)
            count += 1

            return self.getresp("module/buddy", "rem_all", {"count": count})

    @command(command="buddylist", params=[Options(["rem", "remove"]), Character("character"), Any("type")], access_level="admin",
             description="Remove a character from the buddy list")
    def buddylist_remove_cmd(self, request, _, char, buddy_type):
        buddy_type = buddy_type.lower()

        if char.char_id:
            self.buddy_service.remove_buddy(char.char_id, buddy_type)
            return self.getresp("module/buddy", "rem_single", {"char": char.name, "type": buddy_type})
        else:
            return self.getresp("global", "char_not_found", {"char": char.name})

    @command(command="buddylist", params=[Const("clean")], access_level="admin",
             description="Remove all orphaned buddies from the buddy list")
    def buddylist_clean_cmd(self, request, _):
        return self.getresp("module/buddy", "rem_orphaned", {"count":self.remove_orphaned_buddies()})

    @command(command="buddylist", params=[Const("search"), Any("character")], access_level="admin",
             description="Search for characters on the buddy list")
    def buddylist_search_cmd(self, request, _, search):
        search = search.lower()

        buddy_list = []
        for char_id, buddy in self.buddy_service.get_all_buddies().items():
            char_name = self.character_service.resolve_char_to_name(char_id, "Unknown(%d)" % char_id)
            if search in char_name.lower():
                buddy_list.append([char_name, buddy["online"], ",".join(buddy["types"])])

        blob = self.format_buddies(buddy_list)
        return ChatBlob(self.getresp("module/buddy", "search_title", {"amount": len(buddy_list)}), blob)

    @timerevent(budatime="24h", description="Remove orphaned buddies")
    def remove_orphaned_buddies_event(self, event_type, event_data):
        self.logger.debug("removing %d orphaned buddies" % self.remove_orphaned_buddies())

    def remove_orphaned_buddies(self):
        count = 0
        for char_id, buddy in self.buddy_service.get_all_buddies().items():
            if len(buddy["types"]) == 0:
                self.buddy_service.remove_buddy(char_id, None, True)
                count += 1
        return count

    def format_buddies(self, buddy_list):
        buddy_list = sorted(buddy_list, key=lambda x: x[0])

        blob = ""
        for name, online, types in buddy_list:
            blob += "%s - %s\n" % (name, types)

        return blob
