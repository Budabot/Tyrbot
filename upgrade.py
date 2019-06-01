from core.db import DB
from core.logger import Logger
from core.registry import Registry

db = Registry.get_instance("db")
bot = Registry.get_instance("bot")


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
    logger.info("upgrading db to version '%d'" % v)
    db.exec("UPDATE db_version SET version = ? WHERE file = 'db_version'", [v])
    return v


def get_version():
    row = db.query_single("SELECT version FROM db_version WHERE file = 'db_version'")
    if row:
        return int(row.version)
    else:
        return 0


version = get_version()
logger.info("db at version '%d'" % version)

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
        db.exec("CREATE TABLE player ( char_id BIGINT PRIMARY KEY, first_name VARCHAR(30) NOT NULL, name VARCHAR(20) NOT NULL, last_name VARCHAR(30) NOT NULL, level SMALLINT NOT NULL, breed VARCHAR(20) NOT NULL, gender VARCHAR(20) NOT NULL, faction VARCHAR(20) NOT NULL, profession VARCHAR(20) NOT NULL, profession_title VARCHAR(50) NOT NULL, ai_rank VARCHAR(20) NOT NULL, ai_level SMALLINT, org_id INT DEFAULT NULL, org_name VARCHAR(255) NOT NULL, org_rank_name VARCHAR(20) NOT NULL, org_rank_id SMALLINT NOT NULL, dimension SMALLINT NOT NULL, head_id INT NOT NULL, pvp_rating SMALLINT NOT NULL, pvp_title VARCHAR(20) NOT NULL, source VARCHAR(50) NOT NULL, last_updated INT NOT NULL )")
        db.exec("INSERT INTO player (char_id, first_name, name, last_name, level, breed, gender, faction, profession, profession_title, ai_rank, ai_level, org_id, org_name, org_rank_name, org_rank_id, dimension, head_id, pvp_rating, pvp_title, source, last_updated) SELECT char_id, first_name, name, last_name, level, breed, gender, faction, profession, profession_title, ai_rank, ai_level, org_id, org_name, org_rank_name, org_rank_id, dimension, head_id, pvp_rating, pvp_title, source, last_updated FROM player_old")
        db.exec("DROP TABLE player_old")
    version = update_version(version)

if version == 8:
    if table_exists("roll"):
        db.exec("DROP TABLE roll")
    version = update_version(version)

if version == 9:
    if table_exists("event_config"):
        db.exec("ALTER TABLE event_config RENAME TO event_config_old")
        db.exec("CREATE TABLE IF NOT EXISTS event_config (event_type VARCHAR(50) NOT NULL, event_sub_type VARCHAR(50) NOT NULL, handler VARCHAR(255) NOT NULL, description VARCHAR(255) NOT NULL, module VARCHAR(50) NOT NULL, enabled SMALLINT NOT NULL, verified SMALLINT NOT NULL, is_hidden SMALLINT NOT NULL)")
        db.exec("INSERT INTO event_config SELECT event_type, event_sub_type, handler, description, module, enabled, verified, 0 FROM event_config_old")
        db.exec("DROP TABLE event_config_old")
    version = update_version(version)
