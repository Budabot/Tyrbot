import time
from functools import partial

from core.aochat.server_packets import BuddyAdded, CharacterName
from core.decorators import instance, command, timerevent
from core.db import DB
from core.dict_object import DictObject
from core.text import Text
from core.command_param_types import Character, Const, Int, NamedFlagParameters
from core.chat_blob import ChatBlob


@instance()
class CharacterInfoController:
    BUDDY_IS_ONLINE_TYPE = "is_online"

    def __init__(self):
        self.name_history = []
        self.waiting_for_update = {}

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.pork_service = registry.get_instance("pork_service")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.util = registry.get_instance("util")
        self.alts_service = registry.get_instance("alts_service")
        self.alts_controller = registry.get_instance("alts_controller")
        self.buddy_service = registry.get_instance("buddy_service")

    def pre_start(self):
        self.bot.register_packet_handler(CharacterName.id, self.character_name_update)

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS name_history (char_id INT NOT NULL, name VARCHAR(20) NOT NULL, created_at INT NOT NULL, PRIMARY KEY (char_id, name))")
        self.command_alias_service.add_alias("w", "whois")
        self.command_alias_service.add_alias("lookup", "whois")
        self.command_alias_service.add_alias("is", "whois")

    @command(command="whois", params=[Character("character"), Int("server_num", is_optional=True), NamedFlagParameters(["force_update", "skip_online_check"])], access_level="member",
             description="Get whois information for a character", extended_description="Use server_num 6 for RK2019 and server_num 5 for live")
    def whois_cmd(self, request, char, dimension, flag_params):
        dimension = dimension or self.bot.dimension
        force_update = flag_params.force_update

        if dimension == self.bot.dimension and char.char_id:
            online_status = self.buddy_service.is_online(char.char_id)
            if online_status is None and not flag_params.skip_online_check:
                self.bot.register_packet_handler(BuddyAdded.id, self.handle_buddy_status)
                self.waiting_for_update[char.char_id] = DictObject({"char_id": char.char_id,
                                                                    "name": char.name,
                                                                    "callback": partial(self.show_output, char, dimension, force_update, reply=request.reply, conn=request.conn)})
                self.buddy_service.add_buddy(char.char_id, self.BUDDY_IS_ONLINE_TYPE)
            else:
                self.show_output(char, dimension, force_update, online_status, request.reply, request.conn)
        else:
            self.show_output(char, dimension, force_update, None, request.reply, request.conn)

    def show_output(self, char, dimension, force_update, online_status, reply, conn):
        max_cache_age = 0 if force_update else 86400

        if dimension != self.bot.dimension:
            char_info = self.pork_service.request_char_info(char.name, dimension)
        else:
            char_info = self.pork_service.get_character_info(char.name, max_cache_age)

        if char_info and char_info.source != "chat_server":
            alts = self.alts_controller.alts_service.get_alts(char.char_id)
            blob = "Name: %s [%s] [%s]\n" % (self.get_full_name(char_info),
                                             self.text.make_tellcmd("History", "history %s %s" % (char.name, char_info.dimension)),
                                             self.text.make_tellcmd("Alts (%s)" % len(alts), f"alts {char.name}"))
            blob += "Char ID: %d\n" % char_info.char_id
            blob += "Profession: %s\n" % char_info.profession
            blob += "Faction: %s\n" % self.text.get_formatted_faction(char_info.faction)
            blob += "Breed: %s\n" % char_info.breed
            blob += "Gender: %s\n" % char_info.gender
            blob += "Level: %d\n" % char_info.level
            blob += "AI Level: <green>%d</green>\n" % char_info.ai_level
            if char_info.org_id:
                orglist_link = self.text.make_tellcmd("Orglist", f"orglist {char_info.org_id}")
                blob += "Org: <highlight>%s</highlight> (%d) [%s]\n" % (char_info.org_name, char_info.org_id, orglist_link)
                blob += "Org Rank: %s (%d)\n" % (char_info.org_rank_name, char_info.org_rank_id)
            else:
                blob += "Org: &lt;None&gt;\n"
                blob += "Org Rank: &lt;None&gt;\n"
            # blob += "Head Id: %d\n" % char_info.head_id
            # blob += "PVP Rating: %d\n" % char_info.pvp_rating
            # blob += "PVP Title: %s\n" % char_info.pvp_title
            blob += "Source: %s [%s]\n" % (self.format_source(char_info, max_cache_age),
                                         self.text.make_tellcmd("Force Update", f"whois {char.name} {dimension} --force_update"))
            blob += "Dimension: %s\n" % char_info.dimension

            if dimension == self.bot.dimension:
                blob += "Status: %s\n" % ("<green>Active</green>" if char.char_id else "<red>Inactive</red>")

                blob += self.get_name_history(char.char_id, char.name)

            more_info = self.text.paginate_single(ChatBlob("More Info", blob), conn)

            msg = self.text.format_char_info(char_info, online_status) + " " + more_info
        elif char.char_id:
            blob = "<notice>Note: Could not retrieve detailed info for character.</notice>\n\n"
            blob += "Name: <highlight>%s</highlight>\n" % char.name
            blob += "Character ID: <highlight>%d</highlight>\n" % char.char_id
            if online_status is not None:
                blob += "Online status: %s\n" % ("<green>Online</green>" if online_status else "<red>Offline</red>")
            blob += self.get_name_history(char.char_id, char.name)
            msg = ChatBlob("Basic Info for %s" % char.name, blob)
        else:
            msg = "Could not find character <highlight>%s</highlight> on RK%d." % (char.name, dimension)

        reply(msg)

    def get_name_history(self, char_id, name):
        blob = "\n<header2>Name History</header2>\n"
        data = self.db.query("SELECT name, char_id, created_at FROM name_history WHERE char_id = ? OR name = ? ORDER BY created_at DESC", [char_id, name])
        for row in data:
            blob += "[%s] %s (%s)\n" % (self.util.format_date(row.created_at), row.name, row.char_id)
        return blob

    @timerevent(budatime="1min", description="Save name history", is_system=True)
    def save_name_history_event(self, event_type, event_data):
        if not self.name_history:
            return

        with self.db.transaction():
            t = int(time.time())
            for entry in self.name_history:
                sql = "INSERT IGNORE INTO name_history (char_id, name, created_at) VALUES (?, ?, ?)"
                self.db.exec(sql, [entry.char_id, entry.name, t])

            self.name_history = []

    def get_full_name(self, char_info):
        name = ""
        if char_info.first_name:
            name += char_info.first_name + " "

        name += "\"<highlight>" + char_info.name + "</highlight>\""

        if char_info.last_name:
            name += " " + char_info.last_name

        return name

    def format_source(self, char_info, max_cache_age):
        if char_info.cache_age == 0:
            return char_info.source
        elif char_info.cache_age < max_cache_age:
            return "%s (cache; %s old)" % (char_info.source, self.util.time_to_readable(char_info.cache_age))
        elif char_info.cache_age > max_cache_age:
            return "%s (old cache; %s old)" % (char_info.source, self.util.time_to_readable(char_info.cache_age))

    def handle_buddy_status(self, conn, packet):
        obj = self.waiting_for_update.get(packet.char_id)
        if obj:
            self.buddy_service.remove_buddy(packet.char_id, self.BUDDY_IS_ONLINE_TYPE)
            del self.waiting_for_update[packet.char_id]
            if not self.waiting_for_update:
                self.bot.remove_packet_handler(BuddyAdded.id, self.handle_buddy_status)

            obj.callback(packet.online == 1)

    def character_name_update(self, conn, packet):
        self.name_history.append(packet)
