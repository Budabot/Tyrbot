from core.registry import Registry

db = Registry.get_instance("db")

db.exec("DELETE FROM command_alias WHERE alias = ?", ["timer"])
