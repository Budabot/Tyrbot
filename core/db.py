from core.decorators import instance
from core.map_object import MapObject
import sqlite3
import re
import os


@instance()
class DB:
    def __init__(self):
        self.conn = None
        self.enhanced_like_regex = re.compile("(\s+)(\S+)\s+<ENHANCED_LIKE>\s+\?(\s*)", re.IGNORECASE)

    def row_factory(self, cursor: sqlite3.Cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return MapObject(d)

    def connect(self, name):
        self.conn = sqlite3.connect("./data/" + name)
        self.conn.row_factory = self.row_factory

    def query_single(self, sql, params=None):
        if params is None:
            params = []
        sql, params = self.format_sql(sql, params)
        cur = self.conn.execute(sql, params)
        row = cur.fetchone()
        self.conn.commit()
        return row

    def query(self, sql, params=None):
        if params is None:
            params = []
        sql, params = self.format_sql(sql, params)
        cur = self.conn.execute(sql, params)
        data = cur.fetchall()
        self.conn.commit()
        return data

    def exec(self, sql, params=None):
        if params is None:
            params = []
        sql, params = self.format_sql(sql, params)
        cur = self.conn.execute(sql, params)
        rowcount = cur.rowcount
        self.conn.commit()
        return rowcount

    def format_sql(self, sql, params=None):
        sql = sql.replace("<dim>", "")
        sql = sql.replace("<myname>", "")
        sql = sql.replace("<myguild>", "")
        sql = sql.replace("AUTO_INCREMENT", "AUTOINCREMENT")
        sql = sql.replace(" INT ", " INTEGER ")

        if params:  # not None and not empty
            return self.handle_extended_like(sql, params)
        else:
            return sql, params

    def handle_extended_like(self, sql, params):
        # any <ENHANCED_LIKE>s in a query must correspond with the first parameter(s)
        match = self.enhanced_like_regex.search(sql)
        if match is not None:
            field = match.group(2)
            vals = ["%" + p + "%" for p in params[0].split(" ")]
            extra_sql = [field + " LIKE ?" for _ in vals]
            sql = self.enhanced_like_regex.sub(match.group(1) + "(" + " AND ".join(extra_sql) + ")" + match.group(3), sql, 1)

            # first occurrence has been handled, check for more occurrences with recursive call
            # then merge params from recursive call
            sql, remaining_params = self.handle_extended_like(sql, params[1:])
            return sql, vals + remaining_params
        else:
            return sql, params

    def get_connection(self):
        return self.conn

    def load_sql_file(self, sqlfile, module=None):
        if module:
            filename = module + os.sep + sqlfile
        else:
            filename = sqlfile

        with open(filename, "r") as f:
            c = self.conn.cursor()
            for line in f.readlines():
                sql, _ = self.format_sql(line)
                c.execute(sql)
            self.conn.commit()
