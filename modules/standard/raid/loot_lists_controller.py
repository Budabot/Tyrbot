from core.chat_blob import ChatBlob
from core.command_param_types import Options
from core.db import DB
from core.decorators import instance, command
from core.setting_service import SettingService
from core.text import Text


@instance()
class LootListsController:
    def __init__(self):
        self.categories = {
            "s7": "Sector 7",
            "s13": "Sector 13",
            "s28": "Sector 28",
            "s35": "Sector 35",
            "s42west": "Sector 42 - West",
            "s42north": "Sector 42 - North",
            "s42east": "Sector 42 - East",
            "s42ac": "Sector 42 - Artillery Commander",
            "db": "DustBrigade",
            "aquarius": "Aquarius",
            "sagittarius": "Sagittarius",
            "taurus": "Taurus",
            "libra": "Libra",
            "capricorn": "Capricorn",
            "gemini": "Gemini",
            "virgo": "Virgo",
            "cancer": "Cancer",
            "pisces": "Pisces",
            "scorpio": "Scorpio",
            "aries": "Aries",
            "leo": "Leo",
            "tnh": "The Night Heart",
            "barmor": "Beast Armor",
            "bweapons": "Beast Weapons",
            "bstars": "Stars",
            "sb": "Shadowbreeds",
            "alba": "Albtraum",
            "samples": "Samples",
            "ancients": "Ancients",
            "c&cm": "Crystals & Crystalised Memories",
            "pbc": "Pocket Boss Crystals",
            "r&pu": "Rings and Preservation Units",
            "symbs": "Symbiants",
            "spirits": "Spirits",
            "pgems": "Profession Gems",
            "gen": "General",
            "db1": "DB1",
            "db2": "DB2",
            "db3": "DB3",
            "ncu": "HUD/NCU",
            "gaunt": "Bastion",
            "mitaar": "Mitaar",
            "12m": "12Man",
            "vortexx": "Vortexx",
            "dbarmor": "DB Armor",
            "util": "Util",
            "poh": "Pyramid of Home",
            "totwh": "Temple of Three Winds (HL)",
            "binyacht": "Binyacht the Faithful",
            "guardian": "Guardian of the Three",
            "summoner": "The Immortal Summoner",
            "lien": "Lien the Memory-Devourer",
            "loremaster": "The Loremaster",
            "nematet": "Nematet the Subjugator of Time",
            "aegis": "Aegis of Tomorrow",
            "gartua": "Gartua the Gate Guardian",
            "aztur": "Aztur the Immortal",
            "khalum": "Khalum the Weaver of Flesh",
            "uklesh": "Uklesh the Beguiling",

            "subh": "Condemned Subway (HL)",
            "shiro": "Eliminator Shiro",
            "eumen": "Eumenides",
            "qets": "Queen of the Slums",
            "psion": "The Psion",
            "primal": "Primal Bloodcreeper",
            "aneid": "Vergil Aeneid",
            "abmouth": "Abmouth Supremus",
            "albtraum": "Albtraum",
            "pande": "Pande",
            "apf": "APF",

        }

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("aries", "pande aries")
        self.command_alias_service.add_alias("aquarius", "pande aquarius")
        self.command_alias_service.add_alias("leo", "pande leo")
        self.command_alias_service.add_alias("virgo", "pande virgo")
        self.command_alias_service.add_alias("cancer", "pande cancer")
        self.command_alias_service.add_alias("gemini", "pande gemini")
        self.command_alias_service.add_alias("libra", "pande libra")
        self.command_alias_service.add_alias("pisces", "pande pisces")
        self.command_alias_service.add_alias("capricorn", "pande capricorn")
        self.command_alias_service.add_alias("scorpio", "pande scorpio")
        self.command_alias_service.add_alias("taurus", "pande taurus")
        self.command_alias_service.add_alias("sagittarius", "pande sagittarius")
        self.command_alias_service.add_alias("tnh", "pande tnh")

        self.command_alias_service.add_alias("s7", "apf s7")
        self.command_alias_service.add_alias("s13", "apf s13")
        self.command_alias_service.add_alias("s28", "apf s28")
        self.command_alias_service.add_alias("s35", "apf s35")
        self.command_alias_service.add_alias("s42east", "apf s42east")
        self.command_alias_service.add_alias("s42west", "apf s42west")
        self.command_alias_service.add_alias("s42north", "apf s42north")
        self.command_alias_service.add_alias("s42ac", "apf s42ac")

        self.command_alias_service.add_alias("mitaar", "xan mitaar")
        self.command_alias_service.add_alias("12m", "xan 12m")
        self.command_alias_service.add_alias("vortexx", "xan vortexx")

        self.command_alias_service.add_alias("alba", "albtraum")

    #                   #
    #       APF         #
    #                   #
    @command(command="apf",
             params=[Options(["7", "13", "28", "35", "42west", "42north", "42east", "42ac", "s7", "s13", "s28", "s35", "s42west", "s42north", "s42east", "s42ac",])],
             description="Get list of items from APF", access_level="all")
    def apf_loot_cmd(self, _, category_name):
        category_name = category_name.lower()
        if not category_name.startswith("s"):
            category_name = "s" + category_name

        add_all = True if category_name != "s7" else False
        category = self.get_category_name(category_name)

        items = self.get_items("APF", category)

        if items:
            return ChatBlob("%s loot table" % category, self.build_list(items, "APF", category, add_all))
        else:
            return "No loot registered for <highlight>%s</highlight>." % category_name

    @command(command="apf", params=[], description="Get list of items from APF", access_level="all")
    def apf_tables_cmd(self, _):
        return self.get_raid_categories("apf")

    #               #
    #   Albtraum    #
    #               #
    @command(command="albtraum", params=[],
             description="Get list of items from Albtraum", access_level="all")
    def albtraum_loot_cmd(self, _):
        return self.get_raid_categories("albtraum")

    @command(command="albtraum", params=[Options(["c&cm", "pbc", "r&pu", "ancients", "samples"])],
             description="Get list of items from Albtraum", access_level="all")
    def albtraum_tables_cmd(self, _, category_name):
        category_name = category_name.lower()
        category = self.get_category_name(category_name)

        items = self.get_items("Albtraum", category)

        if items:
            return ChatBlob("%s loot table" % category, self.build_list(items, "Albtraum", category))
        else:
            return "No loot registered for <highlight>%s</highlight>." % category_name

    #               #
    #  Pandemonium  #
    #               #
    @command(command="pande",
             params=[Options(["bweapons", "barmor", "bstars", "aries", "aquarius", "leo",
                              "virgo", "cancer", "gemini", "libra", "pisces", "capricorn",
                              "scorpio", "taurus", "sagittarius", "tnh", "gaunt", "sb"])],
             description="Get list of items from Pandemonium", access_level="all")
    def pande_loot_cmd(self, _, category_name):
        category_name = category_name.lower()
        category = self.get_category_name(category_name)

        items = self.get_items("Pande", category)

        if items:
            return ChatBlob("%s loot table" % category, self.build_list(items, "Pande", category))
        else:
            return "No loot registered for <highlight>%s</highlight>." % category_name

    @command(command="pande", params=[], description="Get list of items from Pandemonium", access_level="all")
    def pande_tables_cmd(self, _):
        return self.get_raid_categories("pande")

    #               #
    # Dust Brigade  #
    #               #
    @command(command="db", params=[Options(["db1", "db2", "db3", "dbarmor", "util"])],
             description="Get list of items from DustBrigade", access_level="all")
    def db_loot_cmd(self, _, category_name):
        category_name = category_name.lower()
        category = self.get_category_name(category_name)
        items = self.get_items("DustBrigade", category)
        if items:
            return ChatBlob("%s loot table" % category, self.build_list(items, "DustBrigade", category))
        else:
            return "No loot registered for <highlight>%s</highlight>." % category_name

    @command(command="db", params=[], description="Get list of items from DustBrigade", access_level="all")
    def db_tables_cmd(self, _):
        return self.get_raid_categories("db")

    #               #
    #      Xan      #
    #               #
    @command(command="xan", params=[Options(["mitaar", "12m", "vortexx"])],
             description="Get list of items from Xan", access_level="all")
    def xan_loot_cmd(self, _, category_name):
        category_name = category_name.lower()
        category = self.get_category_name(category_name)

        if not category:
            return "No loot registered for <highlight>%s</highlight>." % category_name

        blob = ""
        blob += self.build_list(self.get_items(category, "General"), category, "General")
        blob += self.build_list(self.get_items(category, "Symbiants"), category, "Symbiants")
        blob += self.build_list(self.get_items(category, "Spirits"), category, "Spirits")

        if category == "12Man":
            blob += self.build_list(self.get_items(category, "Profession Gems"), category, "Profession Gems")

        return ChatBlob("%s loot table" % category, blob)

    @command(command="xan", params=[], description="Get list of items from Xan", access_level="all")
    def xan_tables_cmd(self, _):
        blob = ""
        raids = ["Mitaar", "Vortexx", "12Man"]

        for raid in raids:
            show_loot = self.text.make_tellcmd("Loot table", "xan %s" % self.get_category_abbrev(raid))

            sql = "SELECT COUNT(*) AS count FROM raid_loot WHERE raid = ?"
            count = self.db.query_single(sql, [raid]).count

            blob += "%s - %s items\n" % (raid, count)
            blob += "[%s]\n\n" % show_loot

        return ChatBlob("Xan loot tables", blob)

    #               #
    # Pyramid of Home#
    #               #
    @command(command="poh", params=[Options(["gen", "ncu"])],
             description="Get list of items from Pyramid of Home", access_level="all")
    def poh_loot_cmd(self, _, category_name):
        category_name = category_name.lower()
        category = self.get_category_name(category_name)
        items = self.get_items("Pyramid of Home", category)
        if items:
            return ChatBlob("%s loot table" % category, self.build_list(items, "poh", category))
        else:
            return "No loot registered for <highlight>%s</highlight>." % category_name

    @command(command="poh", params=[], description="Get list of items from Pyramid of Home", access_level="all")
    def poh_tables_cmd(self, _):
        return self.get_raid_categories("poh")

    #########################################
    #   Temple of Three Winds (Highlevel)   #
    #########################################

    @command(command="totwh", params=[Options(
        ["binyacht", "guardian", "summoner", "loremaster", "nematet", "aegis", "lien", "gartua", "aztur", "khalum",
         "uklesh", "gen", "armor"])],
             description="Get list of items from Temple of Three Winds", access_level="all")
    def totwh_loot_cmd(self, _, category_name):
        category_name = category_name.lower()
        category = self.get_category_name(category_name)
        items = self.get_items("Temple of Three Winds (HL)", category)
        if items:
            return ChatBlob("%s loot table" % category, self.build_list(items, "totwh", category))
        else:
            return "No loot registered for <highlight>%s</highlight>." % category_name

    @command(command="totwh", params=[], description="Get list of items from Temple of Three Winds", access_level="all")
    def totwh_tables_cmd(self, _):
        return self.get_raid_categories("totwh")

    ###############################
    #   Condemned Subway (raid)   #
    ###############################

    @command(command="subh", params=[Options(["shiro", "eumen", "qets", "psion", "primal", "aneid", "abmouth", "gen"])],
             description="Get list of items from Condemned Subway (HL)", access_level="all")
    def subh_loot_cmd(self, _, category_name):
        category_name = category_name.lower()
        category = self.get_category_name(category_name)
        items = self.get_items("Condemned Subway (HL)", category)
        if items:
            return ChatBlob("%s loot table" % category, self.build_list(items, "subh", category))
        else:
            return "No loot registered for <highlight>%s</highlight>." % category_name

    @command(command="subh", params=[], description="Get list of items from Condemned Subway (HL)", access_level="all")
    def subh_tables_cmd(self, _):
        return self.get_raid_categories("subh")

    def build_list(self, items, raid=None, category=None, add_all=False):
        blob = ""

        if add_all:
            blob += "%s items to loot list\n\n" % self.text.make_tellcmd(
                "Add all", "loot addraid %s %s" % (raid, category))

        blob += "<header2>%s</header2>\n" % category if category is not None else ""
        for item in items:

            if item.multiloot > 1:
                single_link = self.text.make_tellcmd("Add x1", "loot addraiditem %s 1" % item.id)
                multi_link = self.text.make_tellcmd(
                    "Add x%d" % item.multiloot, "loot addraiditem %s %d" % (item.id, item.multiloot))
                add_links = "[%s] [%s]" % (single_link, multi_link)
            else:
                add_links = "[%s]" % self.text.make_tellcmd("Add x1", "loot addraiditem %s 1" % item.id)

            comment = " (%s)" % item.comment if item.comment != "" else ""

            item_link = self.text.make_item(item.low_id, item.high_id, item.ql, self.text.make_image(item.icon))
            blob += "%s\n%s%s\n%s\n\n" % (item_link, item.name, comment, add_links)

        return blob

    def get_items(self, raid, category):
        return self.db.query(
            "SELECT r.raid, r.category, r.id, r.ql, a.name, r.comment, "
            "r.multiloot, a.lowid AS low_id, a.highid AS high_id, a.icon "
            "FROM raid_loot r "
            "LEFT JOIN aodb a "
            "ON (r.high_id = a.highid) "
            "WHERE r.raid = ? AND r.category = ? "
            "ORDER BY r.name",
            [raid, category]
        )

    def get_category_abbrev(self, category_name):
        for abbrev, name in self.categories.items():
            if name == category_name:
                return abbrev

        return None

    def get_category_name(self, category):
        return self.categories.get(category, None)

    def get_raid_categories(self, raid_command):
        raid_name = self.categories.get(raid_command, raid_command)

        blob = ""
        sql = "SELECT category FROM raid_loot WHERE raid = ? GROUP BY category"
        raids = self.db.query(sql, [raid_name])
        for raid in raids:
            show_loot = self.text.make_tellcmd("Loot table", "%s %s" % (raid_command, self.get_category_abbrev(raid.category)))

            sql = "SELECT COUNT(*) AS count FROM raid_loot WHERE category = ? and raid = ?"
            count = self.db.query_single(sql, [raid.category, raid_name]).count

            blob += "%s - %s items\n" % (raid.category, count)
            blob += "[%s]\n\n" % show_loot
        return ChatBlob(f"{raid_name} loot tables", blob)