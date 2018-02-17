import sqlite3
from core.decorators import instance


@instance()
class DB:
    def __init__(self):
        self.conn = None

    def row_factory(self, cursor: sqlite3.Cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return DBRow(d)

    def connect(self, name):
        self.conn = sqlite3.connect("./data/" + name)
        self.conn.row_factory = self.row_factory

    def query_single(self, sql, params):
        sql = self.format_sql(sql)
        cur = self.conn.execute(sql, params)
        return cur.fetchone()

    def query(self, sql, params):
        sql = self.format_sql(sql)
        cur = self.conn.execute(sql, params)
        return cur.fetchall()

    def exec(self, sql, params):
        sql = self.format_sql(sql)
        cur = self.conn.execute(sql, params)
        return cur.rowcount

    def format_sql(self, sql):
        # TODO
        sql = sql.replace("<dim>", "")
        sql = sql.replace("<myname>", "")
        sql = sql.replace("<myguild>", "")
        return sql

    def get_connection(self):
        return self.conn

    def load_sql(self, sql_script):
        self.conn.executescript(sql_script)


class DBRow:
    def __init__(self, row):
        self.row = row

    def get_row_value(self, name):
        return self.row[name]

    def __getitem__(self, name):
        return self.row[name]

    def __getattr__(self, name):
        return self.get_row_value(name)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.row.__str__()