from core.decorators import instance
from core.map_object import MapObject
from core.logger import Logger
from pkg_resources import parse_version
import mysql.connector
import sqlite3
import re
import os


@instance()
class DB:
    SQLITE = "sqlite"
    MYSQL = "mysql"

    def __init__(self):
        self.conn = None
        self.enhanced_like_regex = re.compile("(\s+)(\S+)\s+<ENHANCED_LIKE>\s+\?(\s*)", re.IGNORECASE)
        self.lastrowid = None
        self.logger = Logger("db")

    def row_factory(self, cursor: sqlite3.Cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def connect_mysql(self, host, username, password, database_name):
        self.type = self.MYSQL
        self.conn = mysql.connector.connect(user=username, password=password, host=host, database=database_name, charset='utf8')
        self.exec("SET collation_connection = 'utf8_general_ci'")
        self.create_db_version_table()

    def connect_sqlite(self, name):
        self.type = self.SQLITE
        self.conn = sqlite3.connect("./data/" + name)
        self.conn.row_factory = self.row_factory
        self.create_db_version_table()

    def create_db_version_table(self):
        self.exec("CREATE TABLE IF NOT EXISTS db_version (file VARCHAR(255) NOT NULL, version VARCHAR(255) NOT NULL)")

    def _execute_wrapper(self, sql, params, callback):
        if self.type == self.MYSQL:
            # buffered=True - https://stackoverflow.com/a/33632767/280574
            cur = self.conn.cursor(dictionary=True, buffered=True)
        else:
            cur = self.conn.cursor()

        cur.execute(sql if self.type == self.SQLITE else sql.replace("?", "%s"), params)
        result = callback(cur)
        cur.close()
        self.conn.commit()
        return result

    def query_single(self, sql, params=None):
        if params is None:
            params = []
        sql, params = self.format_sql(sql, params)

        def map_result(cur):
            row = cur.fetchone()
            return row if row is None else MapObject(row)

        return self._execute_wrapper(sql, params, map_result)

    def query(self, sql, params=None):
        if params is None:
            params = []
        sql, params = self.format_sql(sql, params)

        def map_result(cur):
            return list(map(lambda row: MapObject(row), cur.fetchall()))

        return self._execute_wrapper(sql, params, map_result)

    def exec(self, sql, params=None):
        if params is None:
            params = []
        sql, params = self.format_sql(sql, params)

        def map_result(cur):
            return [cur.rowcount, cur.lastrowid]

        row_count, lastrowid = self._execute_wrapper(sql, params, map_result)
        self.lastrowid = lastrowid
        return row_count

    def last_insert_id(self):
        return self.lastrowid

    def format_sql(self, sql, params=None):
        sql = sql.replace("<dim>", "")
        sql = sql.replace("<myname>", "")
        sql = sql.replace("<myguild>", "")

        # TODO check for AUTOINCREMENT in sql and log warning

        if self.type == self.SQLITE:
            sql = sql.replace("AUTO_INCREMENT", "AUTOINCREMENT")
            sql = sql.replace(" INT ", " INTEGER ")

        if params:
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

    def load_sql_file(self, sqlfile, base_path):
        filename = base_path + os.sep + sqlfile

        db_version = self.get_db_version(filename)
        file_version = self.get_file_version(filename)

        if db_version:
            if parse_version(file_version) > parse_version(db_version):
                self.logger.debug("loading sql file '%s'" % sqlfile)
                self._load_file(filename)
                self.exec("UPDATE db_version SET version = ? WHERE file = ?", [int(file_version), filename])
        else:
            self.logger.debug("loading sql file '%s'" % sqlfile)
            self._load_file(filename)
            self.exec("INSERT INTO db_version (file, version) VALUES (?, ?)", [filename, int(file_version)])

    def get_file_version(self, filename):
        return str(int(os.path.getmtime(filename)))

    def get_db_version(self, filename):
        row = self.query_single("SELECT version FROM db_version WHERE file = ?", [filename])
        if row:
            return row.version
        else:
            return None

    def _load_file(self, filename):
        with open(filename, "r") as f:
            cur = self.conn.cursor()
            for line in f.readlines():
                sql, _ = self.format_sql(line)
                sql = sql.strip()
                if sql and not sql.startswith("--"):
                    cur.execute(sql)
            cur.close()
            self.conn.commit()
