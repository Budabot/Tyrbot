from core.db import DB
from core.registry import Registry

db = Registry.get_instance("db")
bot = Registry.get_instance("bot")


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
    db.exec("UPDATE db_version SET version = ? WHERE file = 'db_version'", [v])
    return v


def get_version():
    row = db.query_single("SELECT version FROM db_version WHERE file = 'db_version'")
    if row:
        return int(row.version)
    else:
        return 0


version = get_version()
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
