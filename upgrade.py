from core.db import DB
from core.logger import Logger
from core.registry import Registry

db = Registry.get_instance("db")
logger = Logger("core.upgrade")


def table_info(table_name):
    if db.type == DB.MYSQL:
        data = db.query("DESCRIBE %s" % table_name)

        def normalize_table_info(row):
            row.name = row.Field
            row.type = row.Type.upper()
            return row

        return list(map(normalize_table_info, data))
    elif db.type == DB.SQLITE:
        return db.query("PRAGMA table_info(%s)" % table_name)
    else:
        raise Exception("Unknown database type '%s'" % db.type)


def table_exists(table_name):
    try:
        db.query("SELECT * FROM %s LIMIT 1" % table_name)
        return True
    except Exception:
        return False


def column_exists(table_name, column_name):
    try:
        db.query("SELECT %s FROM %s LIMIT 1" % (column_name, table_name))
        return True
    except Exception:
        return False


def update_version(v):
    v += 1
    logger.info("Upgrading db to version '%d'" % v)
    db.exec("UPDATE db_version SET version = ? WHERE file = 'db_version'", [v])
    return v


def get_version():
    row = db.query_single("SELECT version FROM db_version WHERE file = 'db_version'")
    if row:
        return int(row.version)
    else:
        return 0


def run_upgrades():
    version = get_version()
    logger.info("Database at version '%d'" % version)

    if version == 0:
        db.exec("INSERT INTO db_version (file, version, verified) VALUES ('db_version', ?, 1)", [0])
        version = update_version(version)

    if version == 1:
        if table_exists("org_member"):
            db.exec("ALTER TABLE org_member ADD COLUMN last_seen INT NOT NULL DEFAULT 0")
        version = update_version(version)

    if version == 2:
        if table_exists("org_member"):
            if db.type == DB.MYSQL:
                db.exec("ALTER TABLE org_member MODIFY mode VARCHAR(20) NOT NULL")
            db.exec("UPDATE org_member SET mode = ? WHERE mode = ?", ["add_manual", "manual"])
            db.exec("UPDATE org_member SET mode = ? WHERE mode = ?", ["rem_manual", "ignore"])
            db.exec("UPDATE org_member SET mode = ? WHERE mode = ?", ["add_auto", "auto"])
        version = update_version(version)

    if version == 3:
        if table_exists("news"):
            db.exec("ALTER TABLE news RENAME TO news_old")
            db.exec("CREATE TABLE news (id INT PRIMARY KEY AUTO_INCREMENT, time INT NOT NULL, char_id INT NOT NULL, news TEXT, sticky SMALLINT NOT NULL, deleted SMALLINT NOT NULL)")
            db.exec("INSERT INTO news SELECT news_id, time, p.char_id, news, sticky, deleted FROM news_old n LEFT JOIN player p ON n.author = p.name")
            db.exec("DROP TABLE news_old")
        version = update_version(version)

    if version == 4:
        if table_exists("news"):
            db.exec("ALTER TABLE news RENAME TO news_old")
            db.exec("CREATE TABLE news (id INT PRIMARY KEY AUTO_INCREMENT, char_id INT NOT NULL, news TEXT, sticky SMALLINT NOT NULL, created_at INT NOT NULL, deleted_at INT NOT NULL)")
            db.exec("INSERT INTO news (id, char_id, news, sticky, created_at, deleted_at) SELECT id, char_id, news, sticky, time, deleted FROM news_old")
            db.exec("DROP TABLE news_old")
        version = update_version(version)

    if version == 5:
        if table_exists("command_config"):
            db.exec("UPDATE command_config SET access_level = 'org_member' WHERE access_level = 'superadmin' AND command = 'member'")
        version = update_version(version)

    if version == 6:
        if table_exists("command_alias"):
            db.exec("DELETE FROM command_alias WHERE command = 'loud'")
        version = update_version(version)

    if version == 7:
        if table_exists("player"):
            db.exec("ALTER TABLE player RENAME TO player_old")
            db.exec("CREATE TABLE player ( char_id BIGINT PRIMARY KEY, first_name VARCHAR(30) NOT NULL, name VARCHAR(20) NOT NULL, last_name VARCHAR(30) NOT NULL, "
                    "level SMALLINT NOT NULL, breed VARCHAR(20) NOT NULL, gender VARCHAR(20) NOT NULL, faction VARCHAR(20) NOT NULL, profession VARCHAR(20) NOT NULL, "
                    "profession_title VARCHAR(50) NOT NULL, ai_rank VARCHAR(20) NOT NULL, ai_level SMALLINT, org_id INT DEFAULT NULL, org_name VARCHAR(255) NOT NULL, "
                    "org_rank_name VARCHAR(20) NOT NULL, org_rank_id SMALLINT NOT NULL, dimension SMALLINT NOT NULL, head_id INT NOT NULL, pvp_rating SMALLINT NOT NULL, "
                    "pvp_title VARCHAR(20) NOT NULL, source VARCHAR(50) NOT NULL, last_updated INT NOT NULL )")
            db.exec("INSERT INTO player (char_id, first_name, name, last_name, level, breed, gender, faction, profession, profession_title, ai_rank, ai_level, org_id, "
                    "org_name, org_rank_name, org_rank_id, dimension, head_id, pvp_rating, pvp_title, source, last_updated) SELECT char_id, first_name, name, last_name, "
                    "level, breed, gender, faction, profession, profession_title, ai_rank, ai_level, org_id, org_name, org_rank_name, org_rank_id, dimension, head_id, "
                    "pvp_rating, pvp_title, source, last_updated FROM player_old")
            db.exec("DROP TABLE player_old")
        version = update_version(version)

    if version == 8:
        if table_exists("roll"):
            db.exec("DROP TABLE roll")
        version = update_version(version)

    if version == 9:
        if table_exists("event_config"):
            db.exec("ALTER TABLE event_config RENAME TO event_config_old")
            db.exec("CREATE TABLE IF NOT EXISTS event_config (event_type VARCHAR(50) NOT NULL, event_sub_type VARCHAR(50) NOT NULL, handler VARCHAR(255) NOT NULL, "
                    "description VARCHAR(255) NOT NULL, module VARCHAR(50) NOT NULL, enabled SMALLINT NOT NULL, verified SMALLINT NOT NULL, is_hidden SMALLINT NOT NULL)")
            db.exec("INSERT INTO event_config SELECT event_type, event_sub_type, handler, description, module, enabled, verified, 0 FROM event_config_old")
            db.exec("DROP TABLE event_config_old")
        version = update_version(version)

    if version == 10:
        if table_exists("discord"):
            db.exec("ALTER TABLE discord RENAME TO discord_old")
            db.exec("CREATE TABLE IF NOT EXISTS discord (channel_id INTEGER(64) NOT NULL UNIQUE, server_name VARCHAR(256) NOT NULL, channel_name VARCHAR(256) NOT NULL, "
                    "relay_ao SMALLINT NOT NULL DEFAULT 0, relay_dc SMALLINT NOT NULL DEFAULT 0)")
            db.exec("INSERT INTO discord SELECT channel_id, server_name, channel_name, relay_ao, relay_dc FROM discord_old")
            db.exec("DROP TABLE discord_old")
        version = update_version(version)

    if version == 11:
        if table_exists("discord"):
            db.exec("DROP TABLE discord")
        version = update_version(version)

    if version == 12:
        if table_exists("broadcast"):
            db.exec("ALTER TABLE broadcast RENAME TO broadcast_old")
            db.exec("CREATE TABLE broadcast (char_id INT NOT NULL PRIMARY KEY, alias VARCHAR(50), created_at INT NOT NULL)")
            db.exec("INSERT INTO broadcast SELECT char_id, NULL, created_at FROM broadcast_old")
            db.exec("DROP TABLE broadcast_old")
        version = update_version(version)

    if version == 13:
        if table_exists("org_member"):
            db.exec("ALTER TABLE org_member RENAME TO org_member_old")

            db.exec("CREATE TABLE org_member (char_id INT NOT NULL PRIMARY KEY, mode VARCHAR(20) NOT NULL)")
            db.exec("INSERT INTO org_member SELECT char_id, mode FROM org_member_old")

            db.exec("CREATE TABLE last_seen (char_id INT NOT NULL PRIMARY KEY, dt INT NOT NULL DEFAULT 0)")
            db.exec("INSERT INTO last_seen SELECT char_id, last_seen FROM org_member_old")

            db.exec("DROP TABLE org_member_old")
        version = update_version(version)

    if version == 14:
        if table_exists("auction_log"):
            db.exec("ALTER TABLE auction_log RENAME TO auction_log_old")
            db.exec("CREATE TABLE auction_log (auction_id INT PRIMARY KEY AUTO_INCREMENT, item_ref VARCHAR(255) NOT NULL, item_name VARCHAR(255) NOT NULL, "
                    "winner_id BIGINT NOT NULL, auctioneer_id BIGINT NOT NULL, created_at INT NOT NULL, winning_bid INT NOT NULL)")
            db.exec("INSERT INTO auction_log SELECT auction_id, item_ref, item_name, winner_id, auctioneer_id, time, winning_bid FROM auction_log_old")
            db.exec("DROP TABLE auction_log_old")

        if table_exists("points_log"):
            db.exec("ALTER TABLE points_log RENAME TO points_log_old")
            db.exec("CREATE TABLE points_log (log_id INT PRIMARY KEY, char_id BIGINT NOT NULL, audit INT NOT NULL, "
                    "leader_id BIGINT NOT NULL, reason VARCHAR(255), created_at INT NOT NULL)")
            db.exec("INSERT INTO points_log SELECT log_id, char_id, audit, leader_id, reason, time FROM points_log_old")
            db.exec("DROP TABLE points_log_old")

        if table_exists("points"):
            db.exec("ALTER TABLE points RENAME TO points_old")
            db.exec("CREATE TABLE points (char_id BIGINT PRIMARY KEY, points INT DEFAULT 0, created_at INT NOT NULL, "
                    "disabled SMALLINT DEFAULT 0)")
            db.exec("INSERT INTO points SELECT char_id, points, created, disabled FROM points_old")
            db.exec("DROP TABLE points_old")
        version = update_version(version)

    if version == 15:
        if table_exists("members"):
            db.exec("ALTER TABLE members RENAME TO member")
        version = update_version(version)

    if version == 16:
        if table_exists("cloak_status"):
            db.exec("ALTER TABLE cloak_status RENAME TO cloak_status_old")
            db.exec("CREATE TABLE IF NOT EXISTS cloak_status (char_id INT NOT NULL, action VARCHAR(10) NOT NULL, created_at INT NOT NULL, org_id INT NOT NULL)")
            db.exec("INSERT INTO cloak_status SELECT char_id, action, created_at, 0 FROM cloak_status_old")
            db.exec("DROP TABLE cloak_status_old")
        version = update_version(version)

    if version == 17:
        if table_exists("org_member"):
            db.exec("DROP TABLE org_member")
        version = update_version(version)

    if version == 18:
        if table_exists("org_activity"):
            db.exec("ALTER TABLE org_activity RENAME TO org_activity_old")
            db.exec("CREATE TABLE org_activity (id INT PRIMARY KEY AUTO_INCREMENT, actor_char_id INT NOT NULL, actee_char_id INT NOT NULL, action VARCHAR(20) NOT NULL, created_at INT NOT NULL, org_id INT NOT NULL)")
            db.exec("INSERT INTO org_activity SELECT id, actor_char_id, actee_char_id, action, created_at, 0 FROM org_activity_old")
            db.exec("DROP TABLE org_activity_old")
        version = update_version(version)

    if version == 19:
        if table_exists("setting"):
            db.exec("UPDATE setting SET name = 'arelay_bot' WHERE name = 'arelaybot'")
        version = update_version(version)

    if version == 20:
        if table_exists("recipe"):
            db.exec("DROP TABLE recipe")
        version = update_version(version)

    if version == 21:
        if table_exists("message_hub_subscriptions"):
            db.exec("DELETE FROM message_hub_subscriptions WHERE source = ?", ["timers"])
            db.exec("INSERT INTO message_hub_subscriptions (source, destination) VALUES (?, ?)", ["timers", "org_channel"])
            db.exec("INSERT INTO message_hub_subscriptions (source, destination) VALUES (?, ?)", ["timers", "private_channel"])
        version = update_version(version)

    if version == 22:
        if table_exists("setting"):
            db.exec("UPDATE setting SET name = 'autoinvite_auto_access_level' WHERE name = 'autoinvite_auto_al'")
        version = update_version(version)
