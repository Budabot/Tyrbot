from core.decorators import instance, command
from core.command_param_types import Any, Const, Options
from core.chat_blob import ChatBlob


@instance()
class BuddyController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.character_service = registry.get_instance("character_service")
        self.buddy_service = registry.get_instance("buddy_service")

    @command(command="buddylist", params=[], access_level="superadmin",
             description="Show characters on the buddy list")
    def buddylist_cmd(self, channel, sender, reply):
        buddy_list = []
        for char_id, buddy in self.buddy_service.get_all_buddies().items():
            char_name = self.character_service.resolve_char_to_name(char_id, "Unknown(%d)" % char_id)
            buddy_list.append([char_name, buddy["online"], ",".join(buddy["types"])])

        blob = self.format_buddies(buddy_list)

        return ChatBlob("Buddy List (%d)" % len(buddy_list), blob)

    @command(command="buddylist", params=[Const("add"), Any("character"), Any("type")], access_level="superadmin",
             description="Add a character to the buddy list")
    def buddylist_add_cmd(self, channel, sender, reply, _, char_name, buddy_type):
        char_name = char_name.capitalize()
        buddy_type = buddy_type.lower()

        char_id = self.character_service.resolve_char_to_id(char_name)
        if char_id:
            self.buddy_service.add_buddy(char_id, buddy_type)
            return "Character <highlight>%s<end> has been added to the buddy list for type <highlight>%s<end>." % (char_name, buddy_type)
        else:
            return "Could not find character <highlight>%s<end>." % char_name

    @command(command="buddylist", params=[Options(["rem", "remove"]), Any("character"), Any("type")], access_level="superadmin",
             description="Remove a character from the buddy list")
    def buddylist_remove_cmd(self, channel, sender, reply, _, char_name, buddy_type):
        char_name = char_name.capitalize()
        buddy_type = buddy_type.lower()

        char_id = self.character_service.resolve_char_to_id(char_name)
        if char_id:
            self.buddy_service.remove_buddy(char_id, buddy_type)
            return "Character <highlight>%s<end> has been removed from the buddy list for type <highlight>%s<end>." % (char_name, buddy_type)
        else:
            return "Could not find character <highlight>%s<end>." % char_name

    @command(command="buddylist", params=[Options(["remall", "removeall"])], access_level="superadmin",
             description="Remove all characters from the buddy list")
    def buddylist_remove_cmd(self, channel, sender, reply, _):
        count = 0
        for char_id, buddy in self.buddy_service.get_all_buddies().items():
            self.buddy_service.remove_buddy(char_id, None, True)
            count += 1

        return "Removed all <highlight>%d<end> buddies from the buddy list." % count

    @command(command="buddylist", params=[Const("clean")], access_level="superadmin",
             description="Remove all orphaned buddies from the buddy list")
    def buddylist_clean_cmd(self, channel, sender, reply, _):
        count = 0
        for char_id, buddy in self.buddy_service.get_all_buddies().items():
            if len(buddy["types"]) == 0:
                self.buddy_service.remove_buddy(char_id, None, True)
                count += 1

        return "Removed <highlight>%d<end> orphaned buddies from the buddy list." % count

    @command(command="buddylist", params=[Const("search"), Any("character")], access_level="superadmin",
             description="Remove all characters from the buddy list")
    def buddylist_search_cmd(self, channel, sender, reply, _, search):
        search = search.lower()

        buddy_list = []
        for char_id, buddy in self.buddy_service.get_all_buddies().items():
            char_name = self.character_service.resolve_char_to_name(char_id, "Unknown(%d)" % char_id)
            if search in char_name.lower():
                buddy_list.append([char_name, buddy["online"], ",".join(buddy["types"])])

        blob = self.format_buddies(buddy_list)

        return ChatBlob("Buddy List Search Results (%d)" % len(buddy_list), blob)

    def format_buddies(self, buddy_list):
        buddy_list = sorted(buddy_list, key=lambda x: x[0])

        blob = ""
        for name, online, types in buddy_list:
            blob += "%s - %s\n" % (name, types)

        return blob
