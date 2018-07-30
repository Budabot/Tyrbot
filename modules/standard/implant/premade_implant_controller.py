from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Any


@instance()
class PremadeImplantController:
    def __init__(self):
        self.slots = ["head", "eye", "ear", "rarm", "chest", "larm", "rwrist", "waist", "lwrist", "rhand", "legs", "lhand", "feet"]

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")

    @command(command="premade", params=[Any("search")], access_level="all",
             description="Search for implants in the premade implant booths", extended_description="Search can be a profession, implant slot, or ability/skill")
    def premade_cmd(self, channel, sender, reply, args):
        search = args[0].lower()

        prof = self.util.get_profession(search)
        if prof:
            blob = "Search by profession: <highlight>%s<end>\n\n" % prof
            results = self.search_by_profession(prof)
        elif search in self.slots:
            blob = "Search by slot: <highlight>%s<end>\n\n" % search
            results = self.search_by_slot(search)
        else:
            blob = "Search by modifier: <highlight>%s<end>\n\n" % search
            results = self.search_by_modifier(search)

        for row in results:
            blob += "<header2>%s<end> %s <highlight>%s<end> %s, %s, %s\n" % (row.profession, row.slot, row.ability, row.shiny, row.bright, row.faded)

        reply(ChatBlob("Premade Implant Search Results (%d)" % len(results), blob))

    def search_by_profession(self, profession):
        sql = """SELECT
                i.Name AS slot,
                p2.Name AS profession,
                a.Name AS ability,
                CASE WHEN c1.ClusterID = 0 THEN 'N/A' ELSE c1.LongName END AS shiny,
                CASE WHEN c2.ClusterID = 0 THEN 'N/A' ELSE c2.LongName END AS bright,
                CASE WHEN c3.ClusterID = 0 THEN 'N/A' ELSE c3.LongName END AS faded
            FROM premade_implant p
            JOIN ImplantType i ON p.ImplantTypeID = i.ImplantTypeID
            JOIN Profession p2 ON p.ProfessionID = p2.ID
            JOIN Ability a ON p.AbilityID = a.AbilityID
            JOIN Cluster c1 ON p.ShinyClusterID = c1.ClusterID
            JOIN Cluster c2 ON p.BrightClusterID = c2.ClusterID
            JOIN Cluster c3 ON p.FadedClusterID = c3.ClusterID
            WHERE p2.Name = ?
            ORDER BY slot"""

        return self.db.query(sql, [profession])

    def search_by_slot(self, slot):
        sql = """SELECT
                i.Name AS slot,
                p2.Name AS profession,
                a.Name AS ability,
                CASE WHEN c1.ClusterID = 0 THEN 'N/A' ELSE c1.LongName END AS shiny,
                CASE WHEN c2.ClusterID = 0 THEN 'N/A' ELSE c2.LongName END AS bright,
                CASE WHEN c3.ClusterID = 0 THEN 'N/A' ELSE c3.LongName END AS faded
            FROM premade_implant p
            JOIN ImplantType i ON p.ImplantTypeID = i.ImplantTypeID
            JOIN Profession p2 ON p.ProfessionID = p2.ID
            JOIN Ability a ON p.AbilityID = a.AbilityID
            JOIN Cluster c1 ON p.ShinyClusterID = c1.ClusterID
            JOIN Cluster c2 ON p.BrightClusterID = c2.ClusterID
            JOIN Cluster c3 ON p.FadedClusterID = c3.ClusterID
            WHERE i.ShortName = ?
            ORDER BY shiny, bright, faded"""

        return self.db.query(sql, [slot])

    def search_by_modifier(self, modifier):
        sql = """SELECT
                i.Name AS slot,
                p2.Name AS profession,
                a.Name AS ability,
                CASE WHEN c1.ClusterID = 0 THEN 'N/A' ELSE c1.LongName END AS shiny,
                CASE WHEN c2.ClusterID = 0 THEN 'N/A' ELSE c2.LongName END AS bright,
                CASE WHEN c3.ClusterID = 0 THEN 'N/A' ELSE c3.LongName END AS faded
            FROM premade_implant p
            JOIN ImplantType i ON p.ImplantTypeID = i.ImplantTypeID
            JOIN Profession p2 ON p.ProfessionID = p2.ID
            JOIN Ability a ON p.AbilityID = a.AbilityID
            JOIN Cluster c1 ON p.ShinyClusterID = c1.ClusterID
            JOIN Cluster c2 ON p.BrightClusterID = c2.ClusterID
            JOIN Cluster c3 ON p.FadedClusterID = c3.ClusterID
            WHERE c1.LongName <EXTENDED_LIKE=0> ? OR c2.LongName <EXTENDED_LIKE=1> ? OR c3.LongName <EXTENDED_LIKE=2> ?"""

        return self.db.query(*self.db.handle_extended_like(sql, [modifier, modifier, modifier]))
