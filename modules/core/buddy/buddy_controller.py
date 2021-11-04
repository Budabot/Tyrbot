from core.decorators import instance, command, timerevent
from core.command_param_types import Any, Const, Options, Character, NamedFlagParameters, NamedParameters
from core.chat_blob import ChatBlob
from core.logger import Logger
from core.standard_message import StandardMessage


@instance()
class BuddyController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.character_service = registry.get_instance("character_service")
        self.buddy_service = registry.get_instance("buddy_service")

    @command(command="buddylist", params=[Const("add"), Character("character"), Any("type")], access_level="admin",
             description="Add a character to the buddy list")
    def buddylist_add_cmd(self, request, _, char, buddy_type):
        buddy_type = buddy_type.lower()

        if char.char_id:
            self.buddy_service.add_buddy(char.char_id, buddy_type)
            return f"Character <highlight>{char.name}</highlight> has been added to the buddy list for type <highlight>{buddy_type}</highlight>."
        else:
            return StandardMessage.char_not_found(char.name)

    @command(command="buddylist", params=[Options(["rem", "remove"]), Const("all")], access_level="admin",
             description="Remove all characters from the buddy list")
    def buddylist_remove_all_cmd(self, request, _1, _2):
        buddies = self.buddy_service.get_all_buddies().items()
        for char_id, buddy in buddies:
            self.buddy_service.remove_buddy(char_id, None, True)

        return f"Removed all <highlight>{len(buddies)}</highlight> buddies from the buddy list."

    @command(command="buddylist", params=[Options(["rem", "remove"]), Character("character"), Any("type")], access_level="admin",
             description="Remove a character from the buddy list by type")
    def buddylist_remove_cmd(self, request, _, char, buddy_type):
        buddy_type = buddy_type.lower()

        if char.char_id:
            self.buddy_service.remove_buddy(char.char_id, buddy_type)
            return f"Character <highlight>{char.name}</highlight> has been removed from the buddy list for type <highlight>{buddy_type}</highlight>."
        else:
            return StandardMessage.char_not_found(char.name)

    @command(command="buddylist", params=[Options(["rem", "remove"]), Character("character")], access_level="admin",
             description="Remove a character from the buddy list forcefully")
    def buddylist_remove_force_cmd(self, request, _, char):
        if char.char_id:
            self.buddy_service.remove_buddy(char.char_id, None, force_remove=True)
            return f"Character <highlight>{char.name}</highlight> has been removed from the buddy list forcefully."
        else:
            return StandardMessage.char_not_found(char.name)

    @command(command="buddylist", params=[Const("clean")], access_level="admin",
             description="Remove all orphaned buddies from the buddy list")
    def buddylist_clean_cmd(self, request, _):
        num_removed = self.remove_orphaned_buddies()
        return f"Removed <highlight>{num_removed}</highlight> orphaned buddies from the buddy list."

    @command(command="buddylist", params=[Const("search", is_optional=True), Any("character", allowed_chars="[a-z0-9-]", is_optional=True), NamedParameters(["inactive"])],
             access_level="admin", description="Search for characters on the buddy list",
             extended_description="Use --inactive=include (default), --inactive=exclude, or --inactive=only to control if inactive buddies are shown")
    def buddylist_search_cmd(self, request, _, search, named_params):
        is_search = False
        if search:
            is_search = True
            search = search.lower()

        include_active = True
        include_inactive = True
        if named_params.inactive:
            if named_params.inactive.lower() == "exclude":
                include_inactive = False
            elif named_params.inactive.lower() == "only":
                include_active = False
            elif named_params.inactive.lower() != "include":
                return "Named parameter <highlight>--inactive</highlight> only allows values <highlight>include</highlight>, " \
                       "<highlight>exclude</highlight>, or <highlight>only</highlight>."
            is_search = True

        buddy_list = []
        for char_id, buddy in self.buddy_service.get_all_buddies().items():
            is_active = buddy["online"] is not None
            if not include_active and is_active:
                continue
            elif not include_inactive and not is_active:
                continue

            char_name = self.character_service.resolve_char_to_name(char_id, "Unknown(%d)" % char_id)
            if not search or search in char_name.lower():
                buddy_list.append([char_name, buddy])

        blob = self.format_buddies(buddy_list)

        if is_search:
            return ChatBlob(f"Buddy List Search Results ({len(buddy_list)})", blob)
        else:
            return ChatBlob(f"Buddy list ({len(buddy_list)})", blob)

    @timerevent(budatime="24h", description="Remove orphaned buddies", is_system=True)
    def remove_orphaned_buddies_event(self, event_type, event_data):
        if self.bot.is_ready():
            self.logger.debug("Removing %d orphaned buddies" % self.remove_orphaned_buddies())

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
        for name, buddy in buddy_list:
            pending = "*" if buddy["online"] is None else ""
            blob += "%s%s [%s] - %s\n" % (name, pending, buddy["conn_id"], ",".join(buddy["types"]))

        blob += "\nAsterisk (*) indicates the buddy is pending and may not be active."

        return blob
