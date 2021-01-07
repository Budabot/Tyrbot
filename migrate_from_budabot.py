from core.alts.alts_service import AltsService
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

# TODO check python version

# admin
print("migrating data to admin table")
data = old_db.query("SELECT p.charid AS char_id, CASE WHEN adminlevel = 4 THEN 'admin' WHEN adminlevel = 3 THEN 'moderator' END AS access_level FROM admin_<myname> a JOIN players p ON a.name = p.name WHERE p.charid > 0")
with new_db.transaction():
    for row in data:
        new_db.exec("DELETE FROM admin WHERE char_id = ?", [row.char_id])
        new_db.exec("INSERT INTO admin (char_id, access_level) VALUES (?, ?)", [row.char_id, row.access_level])
print("migrated %d records" % len(data))

# banlist_<myname>
print("migrating data to ban_list table")
data = old_db.query("SELECT b.charid AS char_id, p.charid AS sender_char_id, time AS created_at, banend AS finished_at, reason FROM banlist_<myname> b JOIN players p ON b.admin = p.name WHERE p.charid > 0")
with new_db.transaction():
    for row in data:
        new_db.exec("DELETE FROM ban_list WHERE char_id = ?", [row.char_id])
        new_db.exec("INSERT INTO ban_list (char_id, sender_char_id, created_at, finished_at, reason, ended_early) VALUES (?, ?, ?, ?, ?, ?)",
                    [row.char_id, row.sender_char_id, row.created_at, row.finished_at, row.reason, 0])
print("migrated %d records" % len(data))

# alts
print("migrating data to alts table")
data = old_db.query("SELECT p1.charid AS main_char_id, p2.charid AS alt_char_id FROM alts a JOIN players p1 ON p1.name = a.main JOIN players p2 ON p2.name = a.alt WHERE validated = 1 AND p1.charid > 0 AND p2.charid > 0 ORDER BY a.main ASC ")
with new_db.transaction():
    current_main = 0
    group_id = 0
    for row in data:
        if row.main_char_id != current_main:
            current_main = row.main_char_id
            group_id = new_db.query_single("SELECT (COALESCE(MAX(group_id), 0) + 1) AS next_group_id FROM alts").next_group_id
            new_db.exec("DELETE FROM alts WHERE char_id = ?", [row.main_char_id])
            new_db.exec("INSERT INTO alts (char_id, group_id, status) VALUES (?, ?, ?)", [row.main_char_id, group_id, AltsService.MAIN])

        new_db.exec("DELETE FROM alts WHERE char_id = ?", [row.alt_char_id])
        new_db.exec("INSERT INTO alts (char_id, group_id, status) VALUES (?, ?, ?)", [row.alt_char_id, group_id, AltsService.CONFIRMED])
print("migrated %d records" % len(data))

# members_<myname>
print("migrating data to members table")
data = old_db.query("SELECT p.charid AS char_id, m.autoinv AS auto_invite FROM members_<myname> m JOIN players p ON m.name = p.name WHERE p.charid > 0")
with new_db.transaction():
    for row in data:
        new_db.exec("DELETE FROM members WHERE char_id = ?", [row.char_id])
        new_db.exec("INSERT INTO members (char_id, auto_invite) VALUES (?, ?)", [row.char_id, row.auto_invite])
print("migrated %d records" % len(data))

# name_history
print("migrating data to name_history table")
data = old_db.query("SELECT charid AS char_id, name, dt AS created_at FROM name_history")
with new_db.transaction():
    for row in data:
        new_db.exec("DELETE FROM name_history WHERE char_id = ? AND name = ?", [row.char_id, row.name])
        new_db.exec("INSERT INTO name_history (char_id, name, created_at) VALUES (?, ?, ?)", [row.char_id, row.name, row.created_at])
print("migrated %d records" % len(data))

# news
print("migrating data to news table")
data = old_db.query("SELECT p.charid AS char_id, news, sticky, time AS created_at, deleted AS deleted_at FROM news n JOIN players p ON n.name = p.name WHERE p.charid > 0")
with new_db.transaction():
    for row in data:
        new_db.exec("DELETE FROM news WHERE char_id = ? AND news = ?", [row.char_id, row.news])
        new_db.exec("INSERT INTO news (char_id, news, sticky, created_at, deleted_at) VALUES (?, ?, ?, ?, ?)", [row.char_id, row.news, row.sticky, row.created_at, row.deleted_at])
print("migrated %d records" % len(data))

# notes
print("migrating data to notes table")
data = old_db.query("SELECT p.charid AS char_id, n.note, n.dt AS created_at FROM notes n JOIN players p ON p.name = n.added_by WHERE p.charid > 0")
with new_db.transaction():
    for row in data:
        new_db.exec("DELETE FROM notes WHERE char_id = ? AND note = ?", [row.char_id, row.note])
        new_db.exec("INSERT INTO notes (char_id, note, created_at) VALUES (?, ?, ?)", [row.char_id, row.note, row.created_at])
print("migrated %d records" % len(data))

# org_city_<myname>
print("migrating data to cloak_status table")
data = old_db.query("SELECT p.charid AS char_id, action, time AS created_at FROM org_city_<myname> o JOIN players p ON o.player = p.name WHERE p.charid > 0")
with new_db.transaction():
    for row in data:
        new_db.exec("INSERT INTO cloak_status (char_id, action, created_at) VALUES (?, ?, ?)", [row.char_id, row.action, row.created_at])
print("migrated %d records" % len(data))

# org_history
print("migrating data to org_activity table")
data = old_db.query("SELECT p1.charid AS actor_char_id, p2.charid AS actee_char_id, action, time AS created_at FROM org_history o JOIN players p1 ON o.actor = p1.name JOIN players p2 ON o.actee = p2.name WHERE p1.charid > 0 AND p2.charid > 0")
with new_db.transaction():
    for row in data:
        new_db.exec("INSERT INTO org_activity (actor_char_id, actee_char_id, action, created_at) VALUES (?, ?, ?, ?)", [row.actor_char_id, row.actee_char_id, row.action, row.created_at])
print("migrated %d records" % len(data))

# org_members_<myname>
print("migrating data to org_member table")
data = old_db.query("SELECT p.charid AS char_id, CASE WHEN mode = 'org' THEN 'add_auto' WHEN mode = 'add' THEN 'add_manual' WHEN mode = 'del' THEN 'rem_manual' END AS mode, logged_off AS last_seen FROM org_members_<myname> o JOIN players p ON o.name = p.name WHERE p.charid > 0")
with new_db.transaction():
    for row in data:
        new_db.exec("DELETE FROM org_member WHERE char_id = ?", [row.char_id])
        new_db.exec("INSERT INTO org_member (char_id, mode, last_seen) VALUES (?, ?, ?)", [row.char_id, row.mode, row.last_seen])
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

# quote
print("migrating data to quote table")
data = old_db.query("SELECT p.charid AS char_id, q.msg AS content, q.dt AS created_at FROM quote q JOIN players p ON q.poster = p.name WHERE p.charid > 0")
with new_db.transaction():
    for row in data:
        new_db.exec("INSERT INTO quote (char_id, created_at, content) VALUES (?, ?, ?)", [row.char_id, row.created_at, row.content])
print("migrated %d records" % len(data))


# Ignore: bank, broadcast_<myname>, cmd_alias_<myname>, cmdcfg_<myname>, eventcfg_<myname>, events, hlpcfg_<myname>, implant_design, kos, links, preferences_<myname>,
# reputation, roll, scout_info, settings_<myname>, tracked_users_<myname>, tracking_<myname>, usage_<myname>, vote_<myname>, whitelist
