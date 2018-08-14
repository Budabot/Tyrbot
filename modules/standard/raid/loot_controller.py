from core.chat_blob import ChatBlob
from core.command_param_types import Const, Options
from core.db import DB
from core.decorators import instance, command, setting
from core.setting_service import SettingService
from core.setting_types import BooleanSettingType
from core.text import Text


@instance()
class LootController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.settings_service: SettingService = registry.get_instance("setting_service")
        self.text: Text = registry.get_instance("text")

    @setting(name="use_item_icons", value="True", description="Use icons when building loot list")
    def use_item_icons(self):
        return BooleanSettingType()

    @command(command="apf",
             params=[Options(["s7", "s13", "s28", "s35"], is_optional=True)],
             description="Get list of items from APF", access_level="all")
    def apf_cmd(self, request, category):
        if category is None:
            blob = ""
            sql = "SELECT category FROM raid_loot WHERE raid = 'APF' GROUP BY category"
            raids = self.db.query(sql)

            for raid in raids:
                add_loot = self.text.make_chatcmd("Add loot", "/tell <myname> loot addraid APF %s" % raid.category)
                show_loot = self.text.make_chatcmd("Loot table", "/tell <myname> apf %s" % self.get_real_category_name(raid.category, True))

                sql = "SELECT COUNT(*) AS count FROM raid_loot WHERE category = ?"
                count = self.db.query_single(sql, [raid.category]).count

                blob += "%s - %s items\n" % (raid.category, count)
                blob += " | [%s] [%s]\n\n" % (show_loot, add_loot)

            return ChatBlob("APF loot tables", blob)

        add_all = True if category != "s7" else False
        category = self.get_real_category_name(category)

        items = self.get_items("APF", category)

        if items:
            return ChatBlob("%s loot table" % category, self.build_list(items, "APF", category, add_all))
        else:
            return "No loot registered for <highlight>%s<end>." % category

    @command(command="pande",
             params=[
                 Options([
                 "bweapons", "barmor", "bstars", "aries", "aqua", "leo",
                 "virgo", "cancer", "gemini", "libra", "pisces", "capri",
                 "scorpio", "taurus", "sagi"
                 ], is_optional=True)
             ],
             description="Get list of items from Pandemonium", access_level="all")
    def pande_cmd(self, request, category):
        if category is None:
            blob = ""
            sql = "SELECT category FROM raid_loot WHERE raid = 'Pande' GROUP BY category"
            raids = self.db.query(sql)

            for raid in raids:
                show_loot = self.text.make_chatcmd("Loot table", "/tell <myname> pande %s" % self.get_real_category_name(raid.category, True))

                sql = "SELECT COUNT(*) AS count FROM raid_loot WHERE category = ?"
                count = self.db.query_single(sql, [raid.category]).count

                blob += "%s - %s items\n" % (raid.category, count)
                blob += " | [%s]\n\n" % show_loot

            return ChatBlob("Pandemonium loot tables", blob)

        category = self.get_real_category_name(category)

        items = self.get_items("Pande", category)

        if items:
            return ChatBlob("%s loot table" % category, self.build_list(items, "Pande", category))
        else:
            return "No loot registered for <highlight>%s<end>." % category


    @command(command="db", params=[Options(["db1", "db2", "db3", "dbarmor", "util"], is_optional=True)], description="Get list of items from DustBrigade", access_level="all")
    def db_cmd(self, request, category):
        if category is None:
            blob = ""
            sql = "SELECT category FROM raid_loot WHERE raid = 'DustBrigade' GROUP BY category"
            raids = self.db.query(sql)

            for raid in raids:
                show_loot = self.text.make_chatcmd("Loot table", "/tell <myname> db %s" % self.get_real_category_name(raid.category, True))

                sql = "SELECT COUNT(*) AS count FROM raid_loot WHERE category = ?"
                count = self.db.query_single(sql, [raid.category]).count

                blob += "%s - %s items\n" % (raid.category, count)
                blob += " | [%s]\n\n" % show_loot

            return ChatBlob("DustBrigade loot tables", blob)

        category = self.get_real_category_name(category)

        items = self.get_items("DustBrigade", category)

        if items:
            return ChatBlob("%s loot table" % category, self.build_list(items, "DustBrigade", category))
        else:
            return "No loot registered for <highlight>%s<end>." % category

    @command(command="xan", params=[Options(["mitaar", "12m", "vortexx"], is_optional=True)], description="Get list of items from Xan", access_level="all")
    def xan_cmd(self, request, category):
        if category is None:
            blob = ""
            raids = ["Mitaar", "Vortexx", "12Man"]

            for raid in raids:
                show_loot = self.text.make_chatcmd("Loot table", "/tell <myname> xan %s" % self.get_real_category_name(category, True))

                sql = "SELECT COUNT(*) AS count FROM raid_loot WHERE raid = ?"
                count = self.db.query_single(sql, [raid]).count

                blob += "%s - %s items\n" % (raid, count)
                blob += " | [%s]\n\n" % show_loot

            return ChatBlob("Xan loot tables", blob)

        category = self.get_real_category_name(category)

        blob = ""

        blob += self.build_list(self.get_items(category, "General"), category, "General")

        blob += self.build_list(self.get_items(category, "Symbiants"), category, "Symbiants")

        blob += self.build_list(self.get_items(category, "Spirits"), category, "Spirits")

        if category == "12Man":
            blob += self.build_list(self.get_items(category, "Profession Gems"), category, "Profession Gems")

        return ChatBlob("%s loot table" % category, blob)

    # Raids available in AO:
    # s7, s10, s13, s28, s35, s42, aquarius, virgo, sagittarius, beastweapons, beastarmor,
    # beaststars, tnh, aries, leo, cancer, gemini, libra, pisces, taurus,
    # capricorn, scorpio, tara, vortexx, mitaar, 12m, db1, db2, db3, poh,
    # biodome, manex (collector), hollow islands, mercenaries

    def build_list(self, items, raid=None, category=None, add_all=False):
        blob = ""

        if add_all:
            blob += "%s items to loot list\n\n" % self.text.make_chatcmd("Add all", "/tell <myname> loot addraid %s %s" % (raid, category))

        blob += "<header2>%s<end>\n" % category if category is not None else ""

        for item in items:
            item_ref = "raid %d" % item.id

            if item.multiloot > 1:
                single_link = self.text.make_chatcmd("Add x1", "/tell <myname> loot additem %s 1" % item_ref)
                multi_link = self.text.make_chatcmd("Add x%d" % item.multiloot, "/tell <myname> loot additem %s %d" % (item_ref, item.multiloot))
                add_links = "[%s] [%s]" % (single_link, multi_link)
            else:
                add_links = "[%s]" % self.text.make_chatcmd("Add x1", "/tell <myname> loot additem %s 1" % item_ref)

            comment = " (%s)" % item.comment if item.comment != "" else ""

            if self.settings_service.get("use_item_icons").get_value():
                item_link = self.text.make_item(item.lowid, item.highid, item.ql, "<img src=rdb://%s>" % item.icon)
                blob += "%s\n%s%s\n | %s\n\n" % (item_link, item.name, comment, add_links)
            else:
                item_link = self.text.make_item(item.lowid, item.highid, item.ql, item.name)
                blob += "%s%s\n | %s\n\n" % (item_link, comment, add_links)

        return blob

    def get_items(self, raid, category):
        return self.db.query(
            "SELECT r.raid, r.category, r.id, r.ql, r.name, r.comment, r.multiloot, a.lowid, a.highid, a.icon "
            "FROM raid_loot r "
            "LEFT JOIN aodb a "
            "ON (r.name = a.name AND r.ql <= a.highql) "
            "WHERE r.raid = ? AND r.category = ? "
            "ORDER BY r.name",
            [raid, category]
        )

    def get_real_category_name(self, category, reverse=False):
        real_names = {
            "s7": "Sector 7", "s13": "Sector 13", "s28": "Sector 28", "s35": "Sector 35",
            "s42": "Sector 42", "db": "DustBrigade", "aqua": "Aquarius", "sagi": "Sagittarius",
            "saggi": "Sagittarius", "taurus": "Taurus", "libra": "Libra", "capri": "Capricorn",
            "gemini": "Gemini", "virgo": "Virgo", "cancer": "Cancer", "pisces": "Pisces",
            "scorpio": "Scorpio", "aries": "Aries", "leo": "Leo", "tnh": "The Night Heart",
            "barmor": "Beast Armor", "beastweapons": "Beast Weapons", "bstars": "Stars",
            "alba": "Albtraum", "symbs": "Symbiants", "spirits": "Spirits",
            "pgems": "Profession Gems", "gen": "General", "db1": "DB1", "db2": "DB2",
            "db3": "DB3", "ncu": "HUD/NCU", "gaunt": "Bastion", "mitaar": "Mitaar",
            "12m": "12Man", "vortexx": "Vortexx", "dbarmor": "DB Armor", "util": "Util"
        }

        if reverse:
            return next((name for name, real_name in real_names.items() if real_name == category), None)

        return real_names[category] if category in list(real_names.keys()) else None
