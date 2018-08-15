from core.db import DB
from core.registry import Registry

db = Registry.get_instance("db")


def table_info(table_name):
    if db.type == DB.MYSQL:
        data = db.query("DESCRIBE %s" % table_name)

        def normalize_table_info(row):
            row.name = row.Field
            row.type = row.Type

        return list(map(normalize_table_info, data))
    elif db.type == DB.SQLITE:
        return db.query("PRAGMA table_info(%s)" % table_name)
    else:
        raise Exception("Unknown database type '%s'" % db.type)


print(table_info("db_version"))
# db.exec("DELETE FROM command_alias WHERE alias = ?", ["timer"])
