from core.decorators import instance
from core.db import DB


@instance()
class WhereisDao:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")

    def start(self):
        pass

    def search_whereis(self, search):
        return self.db.query("SELECT w.playfield_id, w.name, w.answer, w.xcoord, w.ycoord, p.short_name FROM whereis w "
                             "LEFT JOIN playfields p ON w.playfield_id = p.id "
                             "WHERE name <ENHANCED_LIKE> ? OR keywords <ENHANCED_LIKE> ?",
                             [search, search])
