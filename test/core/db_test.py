from core.db import DB, SqlException
import shutil
import sqlite3
import tempfile
import unittest
import unittest.mock
import os


class DbTest(unittest.TestCase):
    """Uses a throwaway file so a test run can never reach the live bot database."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="tyrbot_db_test_")
        self.DB_FILE = os.path.join(self.temp_dir, "test.db")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_handle_extended_like(self):
        sql = "SELECT * FROM table WHERE param1 = ?"
        params = ["param1"]

        db = DB()
        new_sql, new_params = db.handle_extended_like(sql, params)
        self.assertEqual(1, len(new_params))
        self.assertEqual("param1", new_params[0])
        self.assertEqual("SELECT * FROM table WHERE param1 = ?", new_sql)

    def test_handle_extended_like2(self):
        sql = "SELECT * FROM table WHERE param0 = ? AND param1 <EXTENDED_LIKE=1> ? AND param2 = ? AND param3 <EXTENDED_LIKE=3> ? AND param4 = ?"
        params = ["param0", "search1 -search2 search3", "param2", "param31 -param32", "param4"]

        db = DB()
        new_sql, new_params = db.handle_extended_like(sql, params)
        self.assertEqual(8, len(new_params))
        self.assertEqual("param0", new_params[0])
        self.assertEqual("%search1%", new_params[1])
        self.assertEqual("%search2%", new_params[2])
        self.assertEqual("%search3%", new_params[3])
        self.assertEqual("param2", new_params[4])
        self.assertEqual("%param31%", new_params[5])
        self.assertEqual("%param32%", new_params[6])
        self.assertEqual("param4", new_params[7])
        self.assertEqual("SELECT * FROM table WHERE param0 = ? "
                         "AND (param1 LIKE ? AND param1 NOT LIKE ? AND param1 LIKE ?) "
                         "AND param2 = ? "
                         "AND (param3 LIKE ? AND param3 NOT LIKE ?) "
                         "AND param4 = ?", new_sql)

    def test_sqlite_simple_ddl(self):
        self.delete_db_file()

        db = DB()
        db.connect_sqlite(self.DB_FILE)
        db.exec("CREATE TABLE test1 (name VARCHAR, value VARCHAR)")
        db.exec("INSERT INTO test1 (name, value) VALUES (?, ?)", ["tyrbot", "1"])
        db.get_connection().close()

        db.connect_sqlite(self.DB_FILE)
        self.assertEqual([{'name': 'tyrbot', 'value': '1'}], db.query("SELECT * FROM test1"))

        db.get_connection().close()
        self.delete_db_file()

    def test_sqlite_transaction_commit(self):
        self.delete_db_file()

        db = DB()
        db.connect_sqlite(self.DB_FILE)

        db.exec("CREATE TABLE test1 (name VARCHAR, value VARCHAR)")

        db.begin_transaction()
        db.exec("INSERT INTO test1 (name, value) VALUES (?, ?)", ["tyrbot", "1"])
        db.commit_transaction()
        db.get_connection().close()

        db.connect_sqlite(self.DB_FILE)
        self.assertEqual([{'name': 'tyrbot', 'value': '1'}], db.query("SELECT * FROM test1"))

        db.get_connection().close()
        self.delete_db_file()

    def test_sqlite_transaction_commit_using_with(self):
        self.delete_db_file()

        db = DB()
        db.connect_sqlite(self.DB_FILE)

        db.exec("CREATE TABLE test1 (name VARCHAR, value VARCHAR)")

        with db.transaction():
            db.exec("INSERT INTO test1 (name, value) VALUES (?, ?)", ["tyrbot", "1"])

        db.get_connection().close()

        db.connect_sqlite(self.DB_FILE)
        self.assertEqual([{'name': 'tyrbot', 'value': '1'}], db.query("SELECT * FROM test1"))

        db.get_connection().close()
        self.delete_db_file()

    def test_sqlite_transaction_rollback(self):
        self.delete_db_file()

        db = DB()
        db.connect_sqlite(self.DB_FILE)

        db.exec("CREATE TABLE test1 (name VARCHAR, value VARCHAR)")

        db.begin_transaction()
        db.exec("INSERT INTO test1 (name, value) VALUES (?, ?)", ["tyrbot", "1"])
        db.rollback_transaction()
        db.get_connection().close()

        db.connect_sqlite(self.DB_FILE)
        self.assertEqual([], db.query("SELECT * FROM test1"))

        db.get_connection().close()
        self.delete_db_file()

    def test_sqlite_transaction_rollback_using_with(self):
        self.delete_db_file()

        db = DB()
        db.connect_sqlite(self.DB_FILE)

        db.exec("CREATE TABLE test1 (name VARCHAR, value VARCHAR)")

        try:
            with db.transaction():
                db.exec("INSERT INTO test1 (name, value) VALUES (?, ?)", ["tyrbot", "1"])
                raise Exception("Testing")
        except Exception:
            pass

        db.get_connection().close()

        db.connect_sqlite(self.DB_FILE)
        self.assertEqual([], db.query("SELECT * FROM test1"))

        db.get_connection().close()
        self.delete_db_file()

    def test_connect_sqlite_enables_wal(self):
        db = DB()
        db.connect_sqlite(self.DB_FILE)

        # persisted in the file, so a second connection sees it too
        self.assertEqual("wal", db.conn.execute("PRAGMA journal_mode").fetchone()["journal_mode"])
        db.get_connection().close()

        plain = sqlite3.connect(self.DB_FILE)
        self.assertEqual("wal", plain.execute("PRAGMA journal_mode").fetchone()[0])
        plain.close()

    def test_busy_timeout_is_set(self):
        db = DB()
        db.connect_sqlite(self.DB_FILE)

        # 5000ms comes from sqlite3.connect()'s default timeout=5.0, not from a PRAGMA. Pinned
        # here because passing timeout=0 to connect() would silently drop it to 0 and nothing else
        # would say so
        self.assertEqual(5000, db.conn.execute("PRAGMA busy_timeout").fetchone()["timeout"])
        db.get_connection().close()

    def test_synchronous_is_left_at_full(self):
        db = DB()
        db.connect_sqlite(self.DB_FILE)

        # 2 == FULL. NORMAL (1) can lose recent commits on a crash, so it is not the default here
        self.assertEqual(2, db.conn.execute("PRAGMA synchronous").fetchone()["synchronous"])
        db.get_connection().close()

    def test_warns_when_wal_cannot_be_enabled(self):
        db = DB()
        db.logger = unittest.mock.Mock()

        class _Cursor:
            def __init__(self, row):
                self.row = row

            def fetchone(self):
                return self.row

        class _RefusesWal:
            def execute(self, sql):
                # what a filesystem without shared-memory locking does: reports the old mode
                # rather than raising
                return _Cursor(("delete",) if "journal_mode" in sql else None)

        db.conn = _RefusesWal()
        db._apply_sqlite_pragmas()

        self.assertEqual(1, db.logger.warning.call_count)

    def test_writes_survive_a_reconnect_under_wal(self):
        db = DB()
        db.connect_sqlite(self.DB_FILE)
        db.exec("CREATE TABLE test1 (name VARCHAR)")
        db.exec("INSERT INTO test1 (name) VALUES (?)", ["tyrbot"])
        db.get_connection().close()

        # the point of checking: under WAL a commit lands in the -wal file, and a reader that does
        # not understand that would see an empty table
        db2 = DB()
        db2.connect_sqlite(self.DB_FILE)
        self.assertEqual([{"name": "tyrbot"}], db2.query("SELECT * FROM test1"))
        db2.get_connection().close()

    def _tracking_cursors(self, db):
        """Records every cursor _execute_wrapper opens, so a test can check it was closed."""

        cursors = []
        original = db.get_cursor

        def get_cursor():
            cur = original()
            cursors.append(cur)
            return cur

        db.get_cursor = get_cursor
        return cursors

    def assert_closed(self, cur):
        # sqlite has no "is closed" flag; using a closed cursor is how you find out
        with self.assertRaises(sqlite3.ProgrammingError):
            cur.execute("SELECT 1")

    def test_cursor_is_closed_when_the_callback_raises(self):
        db = DB()
        db.connect_sqlite(self.DB_FILE)
        db.exec("CREATE TABLE test1 (name VARCHAR, value VARCHAR)")
        cursors = self._tracking_cursors(db)

        def boom(cur):
            raise Exception("callback blew up")

        with self.assertRaises(Exception):
            db._execute_wrapper("SELECT * FROM test1", [], boom, False)

        self.assertEqual(1, len(cursors))
        self.assert_closed(cursors[0])
        db.get_connection().close()

    def test_cursor_is_closed_when_the_query_fails(self):
        db = DB()
        db.connect_sqlite(self.DB_FILE)
        cursors = self._tracking_cursors(db)

        # the more commonly hit leak: execute() raises, so the close was skipped entirely
        with self.assertRaises(SqlException):
            db.query("SELECT * FROM no_such_table")

        self.assertEqual(1, len(cursors))
        self.assert_closed(cursors[0])
        db.get_connection().close()

    def test_cursor_is_closed_on_success(self):
        db = DB()
        db.connect_sqlite(self.DB_FILE)
        db.exec("CREATE TABLE test1 (name VARCHAR, value VARCHAR)")
        cursors = self._tracking_cursors(db)

        db.exec("INSERT INTO test1 (name, value) VALUES (?, ?)", ["tyrbot", "1"])
        self.assertEqual([{"name": "tyrbot", "value": "1"}], db.query("SELECT * FROM test1"))

        for cur in cursors:
            self.assert_closed(cur)
        db.get_connection().close()

    def test_exec_still_reports_rowcount_and_lastrowid(self):
        db = DB()
        db.connect_sqlite(self.DB_FILE)
        db.exec("CREATE TABLE test1 (id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR)")

        # both are read from the cursor by the callback, so they must be captured before the close
        self.assertEqual(1, db.exec("INSERT INTO test1 (name) VALUES (?)", ["tyrbot"]))
        self.assertEqual(1, db.last_insert_id())
        db.get_connection().close()

    def delete_db_file(self):
        try:
            os.remove(self.DB_FILE)
        except OSError:
            pass
