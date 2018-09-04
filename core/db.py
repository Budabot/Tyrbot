from core.decorators import instance
from core.dict_object import DictObject
from core.logger import Logger
from pkg_resources import parse_version
import mysql.connector
import sqlite3
import re
import os
import time


@instance()
class DB:
    SQLITE = "sqlite"
    MYSQL = "mysql"

    def __init__(self):
        self.conn = None
        self.enhanced_like_regex = re.compile("(\s+)(\S+)\s+<EXTENDED_LIKE=(\d+)>\s+\?(\s*)", re.IGNORECASE)
        self.lastrowid = None
        self.logger = Logger(__name__)
        self.type = None

    def row_factory(self, cursor: sqlite3.Cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def connect_mysql(self, host, username, password, database_name):
        self.type = self.MYSQL
        self.conn = mysql.connector.connect(user=username, password=password, host=host, database=database_name, charset='utf8', autocommit=True)
        self.exec("SET collation_connection = 'utf8_general_ci'")
        self.exec("SET sql_mode = 'TRADITIONAL,ANSI'")
        self.create_db_version_table()

    def connect_sqlite(self, filename):
        self.type = self.SQLITE
        self.conn = sqlite3.connect(filename, isolation_level=None)
        self.conn.row_factory = self.row_factory
        self.create_db_version_table()

    def create_db_version_table(self):
        self.exec("CREATE TABLE IF NOT EXISTS db_version (file VARCHAR(255) NOT NULL, version VARCHAR(255) NOT NULL, verified TINYINT NOT NULL)")

    def _execute_wrapper(self, sql, params, callback):
        if self.type == self.MYSQL:
            # buffered=True - https://stackoverflow.com/a/33632767/280574
            cur = self.conn.cursor(dictionary=True, buffered=True)
        else:
            cur = self.conn.cursor()

        start_time = time.time()
        try:
            cur.execute(sql if self.type == self.SQLITE else sql.replace("?", "%s"), params)
        except Exception as e:
            raise SqlException("SQL Error: '%s' for '%s' [%s]" % (str(e), sql, ", ".join(map(lambda x: str(x), params)))) from e

        elapsed = time.time() - start_time

        if elapsed > 0.5:
            self.logger.warning("slow query (%fs) '%s' for params: %s" % (elapsed, sql, str(params)))

        result = callback(cur)
        cur.close()
        return result

    def query_single(self, sql, params=None):
        if params is None:
            params = []
        sql, params = self.format_sql(sql, params)

        def map_result(cur):
            row = cur.fetchone()
            return row if row is None else DictObject(row)

        return self._execute_wrapper(sql, params, map_result)

    def query(self, sql, params=None):
        if params is None:
            params = []
        sql, params = self.format_sql(sql, params)

        def map_result(cur):
            return list(map(lambda row: DictObject(row), cur.fetchall()))

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
        # TODO check for AUTOINCREMENT in sql and log warning

        if self.type == self.SQLITE:
            sql = sql.replace("AUTO_INCREMENT", "AUTOINCREMENT")
            sql = sql.replace(" INT ", " INTEGER ")

        return sql, params

    def handle_extended_like(self, sql, params):
        original_params = params.copy()
        params = list(map(lambda x: [x], params))

        for match in self.enhanced_like_regex.finditer(sql):
            field = match.group(2)
            index = int(match.group(3))
            vals = ["%" + p + "%" for p in original_params[index].split(" ")]
            extra_sql = [field + " LIKE ?" for _ in vals]
            sql = self.enhanced_like_regex.sub(match.group(1) + "(" + " AND ".join(extra_sql) + ")" + match.group(4), sql, 1)

            # remove current param and add generated params in its place
            del params[index]
            params.insert(index, vals)

        return sql, [item for sublist in params for item in sublist]

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
            self.exec("UPDATE db_version SET version = ?, verified = 1 WHERE file = ?", [int(file_version), filename])
        else:
            self.logger.debug("loading sql file '%s'" % sqlfile)
            self._load_file(filename)
            self.exec("INSERT INTO db_version (file, version, verified) VALUES (?, ?, 1)", [filename, int(file_version)])

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
            with self.transaction():
                cur = self.conn.cursor()
                line_num = 1
                for line in f.readlines():
                    try:
                        sql, _ = self.format_sql(line)
                        sql = sql.strip()
                        if sql and not sql.startswith("--"):
                            cur.execute(sql)
                    except Exception as e:
                        raise Exception("sql error in file '%s' on line %d: %s" % (filename, line_num, sql))
                    line_num += 1
                cur.close()

    # transaction support
    def transaction(self):
        return self

    def __enter__(self):
        # called when entering `with` code block
        self.begin_transaction()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # called when exiting `with` code block
        # if exc_type, exc_val or exc_tb is not None, there was an exception
        # otherwise the code block exited normally
        if exc_type is None:
            self.commit_transaction()
        else:
            self.rollback_transaction()

        # False here indicates that if there was an exception, it should not be suppressed but instead propagated
        return False

    def begin_transaction(self):
        self.exec("BEGIN;")

    def commit_transaction(self):
        self.exec("COMMIT;")

    def rollback_transaction(self):
        self.exec("ROLLBACK;")


class SqlException(Exception):
    def __init__(self, message):
        super().__init__(message)
