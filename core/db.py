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
        self.enhanced_like_regex = re.compile(r"(\s+)(\S+)\s+<EXTENDED_LIKE=(\d+)>\s+\?(\s*)", re.IGNORECASE)
        self.lastrowid = None
        self.logger = Logger(__name__)
        self.type = None
        self.transaction_level = 0

    def sqlite_row_factory(self, cursor: sqlite3.Cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def connect_mysql(self, host, port, username, password, database_name):
        self.type = self.MYSQL
        self.conn = mysql.connector.connect(user=username, password=password, host=host, port=port, database=database_name, charset="utf8", autocommit=True)
        self.exec("SET collation_connection = 'utf8_general_ci'")
        self.exec("SET sql_mode = 'TRADITIONAL,ANSI'")
        self.create_db_version_table()

    def connect_sqlite(self, filename):
        self.type = self.SQLITE
        self.conn = sqlite3.connect(filename, isolation_level=None, check_same_thread=False)
        self.conn.row_factory = self.sqlite_row_factory
        self.create_db_version_table()

    def create_db_version_table(self):
        self.exec("CREATE TABLE IF NOT EXISTS db_version (file VARCHAR(255) NOT NULL, version VARCHAR(255) NOT NULL, verified SMALLINT NOT NULL)")

    def get_cursor(self):
        if self.type == self.MYSQL:
            # buffered=True - https://stackoverflow.com/a/33632767/280574
            return self.conn.cursor(dictionary=True, buffered=True)
        else:
            return self.conn.cursor()

    def _execute_wrapper(self, sql, params, callback, log_query):
        cur = self.get_cursor()
        start_time = time.time()
        try:
            cur.execute(sql if self.type == self.SQLITE else sql.replace("?", "%s"), params)
            if log_query:
                self.logger.info("'%s' [%s]" % (sql, ", ".join(map(lambda x: str(x), params))))
        except Exception as e:
            raise SqlException("SQL Error: '%s' for '%s' [%s]" % (str(e), sql, ", ".join(map(lambda x: str(x), params)))) from e

        elapsed = time.time() - start_time

        if elapsed > 0.5:
            self.logger.warning("slow query (%fs) '%s' for params: %s" % (elapsed, sql, str(params)))

        result = callback(cur)
        cur.close()
        return result

    def query_single(self, sql, params=None, extended_like=False, log_query=False):
        if params is None:
            params = []

        if extended_like:
            sql, params = self.handle_extended_like(sql, params)

        sql, params = self.format_sql(sql, params)

        def map_result(cur):
            row = cur.fetchone()
            return DictObject(row) if row else None

        return self._execute_wrapper(sql, params, map_result, log_query)

    def query(self, sql, params=None, extended_like=False, log_query=False):
        if params is None:
            params = []

        if extended_like:
            sql, params = self.handle_extended_like(sql, params)

        sql, params = self.format_sql(sql, params)

        def map_result(cur):
            return list(map(lambda row: DictObject(row), cur.fetchall()))

        return self._execute_wrapper(sql, params, map_result, log_query)

    def exec(self, sql, params=None, extended_like=False, log_query=False):
        if params is None:
            params = []

        if extended_like:
            sql, params = self.handle_extended_like(sql, params)

        sql, params = self.format_sql(sql, params)

        def map_result(cur):
            return [cur.rowcount, cur.lastrowid]

        row_count, lastrowid = self._execute_wrapper(sql, params, map_result, log_query)
        self.lastrowid = lastrowid
        return row_count

    def last_insert_id(self):
        return self.lastrowid

    def format_sql(self, sql, params=None):
        if self.type == self.SQLITE:
            sql = sql.replace("AUTO_INCREMENT", "AUTOINCREMENT")
            sql = sql.replace(" INT ", " INTEGER ")
            sql = sql.replace("INSERT IGNORE", "INSERT OR IGNORE")

        return sql, params

    def handle_extended_like(self, sql, params):
        original_params = params.copy()
        params = list(map(lambda x: [x], params))

        for match in self.enhanced_like_regex.finditer(sql):
            field = match.group(2)
            index = int(match.group(3))

            extra_sql, vals = self._get_extended_params(field, original_params[index].split(" "))

            sql = self.enhanced_like_regex.sub(match.group(1) + "(" + " AND ".join(extra_sql) + ")" + match.group(4), sql, 1)

            # remove current param and add generated params in its place
            del params[index]
            params.insert(index, vals)

        return sql, [item for sublist in params for item in sublist]

    def _get_extended_params(self, field, params):
        extra_sql = []
        vals = []
        for p in params:
            if p.startswith("-") and p != "-":
                vals.append("%" + p[1:] + "%")
                extra_sql.append(field + " NOT LIKE ?")
            else:
                vals.append("%" + p + "%")
                extra_sql.append(field + " LIKE ?")
        return extra_sql, vals

    def get_connection(self):
        return self.conn

    def load_sql_file(self, sqlfile, force_update=False):
        filename = sqlfile.replace("/", os.sep)

        db_version = self.get_db_version(filename)
        file_version = self.get_file_version(filename)

        if db_version:
            if parse_version(file_version) > parse_version(db_version) or force_update:
                self.logger.info(f"Updating sql file '{filename}' to version '{file_version}'")
                self._load_file(filename)
            self.exec("UPDATE db_version SET version = ?, verified = 1 WHERE file = ?", [int(file_version), filename])
        else:
            self.logger.info(f"Adding sql file '{filename}' with version '{file_version}'")
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
        if self.type == self.MYSQL:
            self._load_file_mysql(filename)
        else:
            self._load_file_sqlite(filename)

    def _load_file_sqlite(self, filename):
        with open(filename, mode="r", encoding="UTF-8") as f:
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
                        raise Exception("sql error in file '%s' on line %d: %s" % (filename, line_num, str(e)))
                    line_num += 1
                cur.close()

    def _load_file_mysql(self, filename):
        insert_regexp = re.compile(r"^(INSERT INTO [^ ]+( \(.*?\))? VALUES\s*)(\(.*?\));?$")
        max_batch_size = 500

        def execute(sql):
            try:
                # taken from: https://stackoverflow.com/a/32257894
                cur.execute(sql)
            except Exception as e:
                raise Exception("sql error in file '%s': %s" % (filename, str(e)), e)

        with open(filename, mode="r", encoding="UTF-8") as f:
            with self.conn.cursor() as cur:
                lines = f.readlines()
                batches = []
                current_table = None
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("--"):
                        continue

                    match = insert_regexp.match(line)
                    if match:
                        if match.group(1) != current_table or len(batches) > max_batch_size:
                            if batches:
                                execute(current_table + ", ".join(batches))
                                batches = []
                            current_table = match.group(1)

                        batches.append(match.group(3))
                    else:
                        if batches:
                            execute(current_table + ", ".join(batches))
                            batches = []

                        execute(line)

                if batches:
                    execute(current_table + ", ".join(batches))

    def get_type(self):
        return self.type

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
        if self.transaction_level == 0:
            self.exec("BEGIN;")
        self.transaction_level += 1

    def commit_transaction(self):
        if self.transaction_level == 1:
            self.exec("COMMIT;")
        self.transaction_level -= 1

    def rollback_transaction(self):
        if self.transaction_level == 1:
            self.exec("ROLLBACK;")
        self.transaction_level -= 1


class SqlException(Exception):
    def __init__(self, message):
        super().__init__(message)
