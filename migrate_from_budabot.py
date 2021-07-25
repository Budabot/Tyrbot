from core.alts_service import AltsService
from core.db import DB


class BudabotDB(DB):
    def __init__(self, bot_name):
        super().__init__()
        self.bot_name = bot_name

    def format_sql(self, sql, params=None):
        sql = sql.replace("<myname>", self.bot_name)
        return super().format_sql(sql, params)


# IMPORTANT: specify a bot name before running this script		
bot_name = ""
org_id = 0  # if you know the org_id, set it here

old_db = BudabotDB(bot_name)
# IMPORTANT: connect old_db (budabot) using sqlite or mysql (uncomment ONE)
#old_db.connect_sqlite("./data/budabot.db")
#old_db.connect_mysql(host="localhost", username="", password="", database_name="")

new_db = DB()
# IMPORTANT: connect new_db (tyrbot) using sqlite or mysql (uncomment ONE)
#new_db.connect_sqlite("./data/database.db")
#new_db.connect_mysql(host="localhost", username="", password="", database_name="")

if not old_db.bot_name:
    print("Error! Specify bot name")
    exit(1)

if not old_db.get_type():
    print("Error! Specify connection method for old_db")
    exit(1)

if not new_db.get_type():
    print("Error! Specify connection method for new_db")
    exit(1)

# org_city_<myname>
print("migrating data to cloak_status table")
data = old_db.query("SELECT p.charid AS char_id, action, time AS created_at FROM org_city_<myname> o JOIN players p ON o.player = p.name WHERE p.charid > 0")
with new_db.transaction():
    new_db.exec("DELETE FROM cloak_status WHERE org_id = ?", [org_id])
    for row in data:
        new_db.exec("INSERT INTO cloak_status (char_id, action, created_at, org_id) VALUES (?, ?, ?, ?)", [row.char_id, row.action, row.created_at, org_id])
print("migrated %d records" % len(data))

# org_history
print("migrating data to org_activity table")
data = old_db.query("SELECT p1.charid AS actor_char_id, p2.charid AS actee_char_id, action, time AS created_at FROM org_history o JOIN players p1 ON o.actor = p1.name JOIN players p2 ON o.actee = p2.name WHERE p1.charid > 0 AND p2.charid > 0")
with new_db.transaction():
    new_db.exec("DELETE FROM org_activity WHERE org_id = ?", [org_id])
    for row in data:
        new_db.exec("INSERT INTO org_activity (actor_char_id, actee_char_id, action, created_at, org_id) VALUES (?, ?, ?, ?, ?)", [row.actor_char_id, row.actee_char_id, row.action, row.created_at, org_id])
print("migrated %d records" % len(data))

# players
print("migrating data to player table")
data = old_db.query("SELECT * FROM players WHERE charid > 0")
with new_db.transaction():
    for row in data:
        new_db.exec("DELETE FROM player WHERE char_id = ?", [row.charid])
        new_db.exec("INSERT INTO player (ai_level, ai_rank, breed, char_id, dimension, faction, first_name, gender, head_id, last_name, last_updated, level, name, org_id, org_name, org_rank_id, org_rank_name, profession, profession_title, pvp_rating, pvp_title, source) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [row.ai_level, row.ai_rank, row.breed, row.charid, row.dimension, row.faction, row.firstname, row.gender, row.head_id if row.head_id else 0, row.lastname, row.last_update, row.level,
                     row.name, row.guild_id, row.guild, row.guild_rank_id, row.guild_rank, row.profession, row.prof_title, row.pvp_rating if row.pvp_rating else 0, row.pvp_title if row.pvp_title else "", row.source])
print("migrated %d records" % len(data))
# maybe this is needed also? new_db_exec("DELETE FROM player WHERE char_id = 4294967295")


# Ignore: bank, broadcast_<myname>, cmd_alias_<myname>, cmdcfg_<myname>, eventcfg_<myname>, events, hlpcfg_<myname>, implant_design, kos, links, preferences_<myname>,
# reputation, roll, scout_info, settings_<myname>, tracked_users_<myname>, tracking_<myname>, usage_<myname>, vote_<myname>, whitelist
