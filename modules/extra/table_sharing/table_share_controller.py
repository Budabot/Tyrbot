from core.db import DB
from core.decorators import instance, timerevent
from core.dict_object import DictObject
from core.registry import Registry


@instance()
class TableShareController:
    def inject(self, registry):
        self.db = registry.get_instance("db")

    def pre_start(self):
        database = DictObject({"type": "sqlite",
                               "file": "database.db",
                               "path": "../Tyrbot2/data/"})

        # database = DictObject({"type": "mysql",
        #                        "name": "my-database",
        #                        "username": "username",
        #                        "password": "password",
        #                        "host": "localhost"})

        self.db2 = DB()
        if database.type == "sqlite":
            self.db2.connect_sqlite(database.path + database.file)
        elif database.type == "mysql":
            self.db2.connect_mysql(database.host, database.username, database.password, database.name)
        else:
            raise Exception("Unknown database type '%s'" % database.type)

        self.share_notes()
        self.share_news()
        self.share_quotes()
        self.share_timers()
        self.share_alts()

    @timerevent(budatime="30m", description="Copy alts from master bot", run_at_startup=True)
    def connect_event(self, event_type, event_data):
        self.sync_alts()

    def sync_alts(self):
        self.db.exec("DELETE FROM alts")
        for alt in self.db2.query("SELECT * FROM alts"):
            self.db.exec("INSERT INTO alts (char_id, group_id, status) VALUES (?, ?, ?)", [alt.char_id, alt.group_id, alt.status])

    def share_notes(self):
        self.add_db_to_instances(["notes_controller"])

    def share_news(self):
        self.add_db_to_instances(["news_controller"])

    def share_quotes(self):
        self.add_db_to_instances(["quote_controller"])

    def share_timers(self):
        self.add_db_to_instances(["timer_controller"])

    def share_alts(self):
        self.add_db_to_instances(["alts_service"])

    def add_db_to_instances(self, instances):
        for name in instances:
            inst = Registry.get_instance(name)
            inst.db = self.db2
