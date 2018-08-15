from core.db import DB
from core.registry import Registry

db = Registry.get_instance("db")


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


def does_table_exist(table_name):
    try:
        db.query("SELECT * FROM %s LIMIT 1" % table_name)
        return True
    except Exception:
        return False


def does_column_exist(table_name, column_name):
    try:
        db.query("SELECT %s FROM %s LIMIT 1" % (column_name, table_name))
        return True
    except Exception:
        return False
