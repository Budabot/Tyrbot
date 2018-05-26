from core.decorators import instance, command
from core.command_param_types import Any, Const, Options
from core.chat_blob import ChatBlob


@instance()
class BuddyController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.character_manager = registry.get_instance("character_manager")
        self.command_manager = registry.get_instance("command_manager")
        self.buddy_manager = registry.get_instance("buddy_manager")

    def start(self):
        pass

    @command(command="buddylist", params=[], access_level="superadmin",
             description="Show characters on the buddy list")
    def buddylist_cmd(self, channel, sender, reply, args):
        buddy_list = []
        for char_id, buddy in self.buddy_manager.get_all_buddies().items():
            char_name = self.character_manager.resolve_char_to_name(char_id)
            char_name = char_name if char_name else "Unknown(%d)" % char_id
            buddy_list.append([char_name, buddy["online"], ",".join(buddy["types"])])

        blob = self.format_buddies(buddy_list)

        reply(ChatBlob("Buddy List (%d)" % len(buddy_list), blob))

    @command(command="buddylist", params=[Const("add"), Any("character"), Any("type")], access_level="superadmin",
             description="Add a character to the buddy list")
    def buddylist_add_cmd(self, channel, sender, reply, args):
        char_name = args[1].capitalize()
        _type = args[2].lower()

        char_id = self.character_manager.resolve_char_to_id(char_name)
        if char_id:
            self.buddy_manager.add_buddy(char_id, _type)
            reply("Character <highlight>%s<end> has been added to the buddy list for type <highlight>%s<end>." % (char_name, _type))
        else:
            reply("Could not find character <highlight>%s<end>." % char_name)

    @command(command="buddylist", params=[Options(["rem", "remove"]), Any("character"), Any("type")], access_level="superadmin",
             description="Remove a character from the buddy list")
    def buddylist_remove_cmd(self, channel, sender, reply, args):
        char_name = args[1].capitalize()
        _type = args[2].lower()

        char_id = self.character_manager.resolve_char_to_id(char_name)
        if char_id:
            self.buddy_manager.remove_buddy(char_id, _type)
            reply("Character <highlight>%s<end> has been removed from the buddy list for type <highlight>%s<end>." % (char_name, _type))
        else:
            reply("Could not find character <highlight>%s<end>." % char_name)

    @command(command="buddylist", params=[Options(["remall", "removeall"])], access_level="superadmin",
             description="Remove all characters from the buddy list")
    def buddylist_remove_cmd(self, channel, sender, reply, args):
        count = 0
        for char_id, buddy in self.buddy_manager.get_all_buddies().items():
            self.buddy_manager.remove_buddy(char_id, None, True)
            count += 1

        reply("Removed all <highlight>%d<end> buddies from the buddy list." % count)

    @command(command="buddylist", params=[Const("clean")], access_level="superadmin",
             description="Remove all orphaned buddies from the buddy list")
    def buddylist_clean_cmd(self, channel, sender, reply, args):
        count = 0
        for char_id, buddy in self.buddy_manager.get_all_buddies().items():
            if len(buddy["types"]) == 0:
                self.buddy_manager.remove_buddy(char_id, None, True)
                count += 1

        reply("Removed <highlight>%d<end> orphaned buddies from the buddy list." % count)

    @command(command="buddylist", params=[Const("search"), Any("character")], access_level="superadmin",
             description="Remove all characters from the buddy list")
    def buddylist_search_cmd(self, channel, sender, reply, args):
        search = args[1].lower()

        buddy_list = []
        for char_id, buddy in self.buddy_manager.get_all_buddies().items():
            char_name = self.character_manager.resolve_char_to_name(char_id)
            char_name = char_name if char_name else "Unknown(%d)" % char_id
            if search in char_name.lower():
                buddy_list.append([char_name, buddy["online"], ",".join(buddy["types"])])

        blob = self.format_buddies(buddy_list)

        reply(ChatBlob("Buddy List Search Results (%d)" % len(buddy_list), blob))

    def format_buddies(self, buddy_list):
        buddy_list = sorted(buddy_list, key=lambda x: x[0])

        blob = ""
        for name, online, types in buddy_list:
            blob += "%s - %s\n" % (name, types)

        return blob
