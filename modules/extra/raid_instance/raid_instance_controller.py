from core.chat_blob import ChatBlob
from core.command_param_types import Const, Character, Any
from core.decorators import instance, command
from core.dict_object import DictObject
from core.logger import Logger
from core.setting_types import TextSettingType
from core.translation_service import TranslationService


@instance()
class RaidInstanceController:
    UNASSIGNED_RAID_INSTANCE_ID = 0

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.setting_service = registry.get_instance("setting_service")
        self.util = registry.get_instance("util")
        self.character_service = registry.get_instance("character_service")
        self.private_channel_service = registry.get_instance("private_channel_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS raid_instance (id INT PRIMARY KEY AUTOINCREMENT, name VARCHAR(255) NOT NULL, conn_id VARCHAR(50) NOT NULL)")

        self.db.exec("DROP TABLE IF EXISTS raid_instance_char")
        self.db.exec("CREATE TABLE raid_instance_char (raid_instance_id INT NOT NULL, char_id INT PRIMARY KEY, is_leader TINYINT NOT NULL)")

        self.setting_service.register(self.module_name, "raid_instance_relay_symbol", "@",
                                      TextSettingType(["!", "#", "*", "@", "$", "+", "-"]),
                                      "Symbol for external relay")

    @command(command="raidinstance", params=[], access_level="guest",
             description="Show the current raid instances")
    def raid_instance_cmd(self, request):
        blob = self.text.make_tellcmd("Refresh", "raidinstance")
        blob += "     "
        blob += self.text.make_tellcmd("Apply", "raidinstance apply")
        blob += "\n\n"
        num_assigned = 0
        num_unassigned = 0

        raid_instances = self.get_raid_instances()

        data = self.get_raid_instance_chars()
        current_raid_instance_id = None
        for row in data:
            if row.raid_instance_id != current_raid_instance_id:
                conn = self.bot.conns.get(row.conn_id)
                bot_name = "(" + conn.char_name + ")" if conn else ""
                blob += f"\n<header2>{row.raid_instance_name} {bot_name}</header2>\n"
                current_raid_instance_id = row.raid_instance_id

            if not row.char_id:
                continue

            if row.raid_instance_id == self.UNASSIGNED_RAID_INSTANCE_ID:
                num_unassigned += 1
            else:
                num_assigned += 1
            blob += self.compact_char_display(row)
            add_leader_link = (row.raid_instance_id != self.UNASSIGNED_RAID_INSTANCE_ID and not row.is_leader)
            blob += " " + self.get_assignment_links(raid_instances, row.name, add_leader_link)
            blob += "\n"
            blob += "\n"

        blob += "\n" + self.text.make_tellcmd("Clear All", "raidinstance clear")
        symbol = self.setting_service.get("raid_instance_relay_symbol").get_value()
        blob += f"\n\nTip: You can use <highlight>{symbol}</highlight> at the start of your message to send it to all bot channels."
        blob += "\n\nInspired by the <highlight>RIS</highlight> module written for Bebot by <highlight>Bitnykk</highlight>"

        return ChatBlob("Raid Instance (%d, %d)" % (num_assigned, num_unassigned), blob)

    @command(command="raidinstance", params=[Const("assign"), Any("raid_instance"), Character("char")], access_level="guest",
             description="Add a character to a raid instance", sub_command="leader")
    def raid_instance_assign_cmd(self, request, _, raid_instance_name, char):
        if not char.char_id:
            return self.getresp("global", "char_not_found", {"char": char.name})

        raid_instance = self.get_raid_instance(raid_instance_name)
        if not raid_instance:
            return f"Raid instance <highlight>{raid_instance_name}</highlight> does not exist."

        self.refresh_raid_instance_chars()

        row = self.db.query_single("SELECT raid_instance_id FROM raid_instance_char WHERE char_id = ?", [char.char_id])
        if row:
            if raid_instance.id == row.raid_instance_id:
                return f"Character <highlight>{char.name}</highlight> is already assigned to raid instance <highlight>{raid_instance.name}</highlight>."
            else:
                self.update_char_raid_instance(char.char_id, raid_instance.id)
                return f"Character <highlight>{char.name}</highlight> has been assigned to raid instance <highlight>{raid_instance.name}</highlight>."
        else:
            return f"Character <highlight>{char.name}</highlight> is not in the private channel."

    @command(command="raidinstance", params=[Const("clear")], access_level="guest",
             description="Remove all characters from all raid instances", sub_command="leader")
    def raid_instance_clear_cmd(self, request, _):
        self.db.exec("DELETE FROM raid_instance_char")

        return f"All characters have been removed from raid instances."

    @command(command="raidinstance", params=[Const("unassign"), Character("char")], access_level="guest",
             description="Remove a character from all raid instances", sub_command="leader")
    def raid_instance_unassign_cmd(self, request, _, char):
        if not char.char_id:
            return self.getresp("global", "char_not_found", {"char": char.name})

        self.refresh_raid_instance_chars()

        row = self.db.query_single("SELECT r2.name FROM raid_instance_char r1 JOIN raid_instance r2 ON r1.raid_instance_id = r2.id WHERE r1.char_id = ?", [char.char_id])
        if row:
            self.update_char_raid_instance(char.char_id, self.UNASSIGNED_RAID_INSTANCE_ID)
            return f"Character <highlight>{char.name}</highlight> has been removed from raid instance <highlight>{row.name}</highlight>."
        else:
            return f"Character <highlight>{char.name}</highlight> is not assigned to any raid instances."

    @command(command="raidinstance", params=[Const("leader"), Character("char")], access_level="guest",
             description="Set the leader for a raid instance", sub_command="leader")
    def raid_instance_leader_cmd(self, request, _, char):
        if not char.char_id:
            return self.getresp("global", "char_not_found", {"char": char.name})

        raid_instance = self.get_raid_instance_by_char(char.char_id)
        if not raid_instance:
            return f"Character <highlight>{char.name}</highlight> does not belong to a raid instance."

        self.set_leader(char.char_id, raid_instance.id)

        return f"Character <highlight>{char.name}</highlight> has been set as the leader for raid instance <highlight>{raid_instance.name}</highlight>."

    @command(command="raidinstance", params=[Const("apply")], access_level="guest",
             description="Apply the current raid instance configuration", sub_command="leader")
    def raid_instance_apply_cmd(self, request, _):
        for raid_instance in self.get_raid_instances():
            conn = self.bot.conns.get(raid_instance.conn_id)
            if not conn:
                self.logger.warning(f"Could not find conn with id '{raid_instance.conn_id}'")
                continue

            private_channel = set()
            private_channel.update(conn.private_channel.keys())

            data = self.db.query("SELECT char_id FROM raid_instance_char WHERE raid_instance_id = ?", [raid_instance.id])
            for row in data:
                if row.char_id not in private_channel:
                    self.private_channel_service.invite(row.char_id, conn)

                private_channel.discard(row.char_id)

            for char_id in private_channel:
                self.private_channel_service.kick(char_id, conn)

        return "Raid instance configuration has been applied."

    @command(command="raidinstance", params=[Const("create"), Any("raid_instance_name"), Any("conn_id")], access_level="admin",
             description="Create or update a raid instance", sub_command="manage")
    def raid_instance_create_cmd(self, request, _, raid_instance_name, conn_id):
        conn = self.get_conn_by_id(conn_id)
        if not conn:
            return f"Could not find bot connection with ID <highlight>{conn_id}</highlight>."

        conn_display = f"{conn.char_name} ({conn.id})"

        if not conn.is_main:
            return f"Bot connection <highlight>{conn_display}</highlight> cannot be assigned to a raid instance because it is not a main bot."

        raid_instance = self.get_raid_instance(raid_instance_name)
        if raid_instance:
            if raid_instance.name == raid_instance_name and raid_instance.conn_id == conn.id:
                return f"Raid instance <highlight>{raid_instance_name}</highlight> already exists."
            else:
                self.db.exec("UPDATE raid_instance SET name = ?, conn_id = ? WHERE id = ?", [raid_instance_name, conn.id, raid_instance.id])
                return f"Raid instance <highlight>{raid_instance_name}</highlight> has been updated."
        else:
            self.db.exec("INSERT INTO raid_instance (name, conn_id) VALUES (?, ?)", [raid_instance_name, conn.id])
            return f"Raid instance <highlight>{raid_instance_name}</highlight> has been created and assigned to bot connection <highlight>{conn_display}</highlight>."

    @command(command="raidinstance", params=[Const("delete"), Any("raid_instance_name")], access_level="admin",
             description="Remove a raid instance", sub_command="manage")
    def raid_instance_delete_cmd(self, request, _, raid_instance_name):
        raid_instance = self.get_raid_instance(raid_instance_name)
        if not raid_instance:
            return f"Raid instance <highlight>{raid_instance_name}</highlight> does not exist."

        self.db.exec("DELETE FROM raid_instance_char WHERE raid_instance_id = ?", [raid_instance.id])
        self.db.exec("DELETE FROM raid_instance WHERE id = ?", [raid_instance.id])

        return f"Raid instance <highlight>{raid_instance_name}</highlight> has been deleted."

    def get_raid_instance_chars(self):
        self.refresh_raid_instance_chars()

        data = self.db.query("SELECT * FROM ("
                             "SELECT p.*, COALESCE(p.name, r1.char_id) AS name, r2.id AS raid_instance_id, "
                             "r1.is_leader, r2.name AS raid_instance_name, r2.conn_id "
                             "FROM raid_instance r2 "
                             "LEFT JOIN raid_instance_char r1 ON r1.raid_instance_id = r2.id "
                             "LEFT JOIN player p ON r1.char_id = p.char_id "
                             "UNION "
                             "SELECT p.*, COALESCE(p.name, r3.char_id) AS name, r3.raid_instance_id, "
                             "r3.is_leader, 'Unassigned' AS raid_instance_name, '' AS conn_id "
                             "FROM raid_instance_char r3 "
                             "LEFT JOIN player p ON r3.char_id = p.char_id "
                             "WHERE r3.raid_instance_id = ?) "
                             "ORDER BY raid_instance_id != ? DESC, raid_instance_name, is_leader, profession",
                             [self.UNASSIGNED_RAID_INSTANCE_ID, self.UNASSIGNED_RAID_INSTANCE_ID])

        return data

    def refresh_raid_instance_chars(self):
        current_raid_instances = set(map(lambda x: x.char_id, self.db.query("SELECT char_id FROM raid_instance_char")))

        current_private_channel = set()
        for _id, conn in self.bot.get_conns(lambda x: x.is_main):
            current_private_channel.update(conn.private_channel.keys())

        for char_id in current_private_channel.difference(current_raid_instances):
            self.db.exec("INSERT INTO raid_instance_char (char_id, raid_instance_id, is_leader) VALUES (?, ?, 0)", [char_id, self.UNASSIGNED_RAID_INSTANCE_ID])

        for char_id in current_raid_instances.difference(current_private_channel):
            self.db.exec("DELETE FROM raid_instance_char WHERE char_id = ? AND raid_instance_id = ?", [char_id, self.UNASSIGNED_RAID_INSTANCE_ID])

    def update_char_raid_instance(self, char_id, raid_instance_id):
        return self.db.exec("UPDATE raid_instance_char SET raid_instance_id = ?, is_leader = 0 WHERE char_id = ?", [raid_instance_id, char_id])

    def set_leader(self, char_id, raid_instance_id):
        self.db.exec("UPDATE raid_instance_char SET is_leader = 0 WHERE raid_instance_id = ?", [raid_instance_id])
        self.db.exec("UPDATE raid_instance_char SET is_leader = 1 WHERE raid_instance_id = ? AND char_id = ?", [raid_instance_id, char_id])

    def compact_char_display(self, char_info):
        if char_info.level:
            msg = "<highlight>%s</highlight> (%d/<green>%d</green>) %s" % (char_info.name, char_info.level, char_info.ai_level, char_info.profession)
        elif char_info.name:
            msg = "<highlight>%s</highlight>" % char_info.name
        else:
            msg = "<highlight>Unknown(%d)</highlight>" % char_info.char_id

        if char_info.is_leader:
            msg += " [Leader]"

        return msg

    def get_assignment_links(self, raid_instances, char_name, add_leader_link):
        links = list(map(lambda x: self.text.make_tellcmd(x.name, f"raidinstance assign {x.name} {char_name}"), raid_instances))
        if add_leader_link:
            links.insert(0, self.text.make_tellcmd("MakeLeader", f"raidinstance leader {char_name}"))
        return " ".join(links)

    def get_raid_instances(self):
        data = self.db.query("SELECT id, name, conn_id FROM raid_instance ORDER BY name")
        data.append(DictObject({"id": self.UNASSIGNED_RAID_INSTANCE_ID, "name": "Unassigned", "conn_id": None}))
        return data

    def get_raid_instance(self, raid_instance_name):
        return self.db.query_single("SELECT id, name, conn_id FROM raid_instance WHERE name LIKE ?", [raid_instance_name])

    def get_raid_instance_by_char(self, char_id):
        return self.db.query_single("SELECT id, name, conn_id "
                                    "FROM raid_instance r1 JOIN raid_instance_char r2 ON r1.id = r2.raid_instance_id "
                                    "WHERE r2.char_id = ?", [char_id])

    def get_conn_by_id(self, conn_id):
        conn = self.bot.conns.get(conn_id)
        if conn:
            return conn

        conns = self.bot.get_conns(lambda x: x.char_name.lower() == conn_id.lower())
        if conns:
            return conns[0][1]

        return None
