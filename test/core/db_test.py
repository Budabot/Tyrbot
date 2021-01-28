from core.db import DB
import unittest
import os


class DbTest(unittest.TestCase):
    DB_FILE = "./test.db"

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

    def delete_db_file(self):
        try:
            os.remove(self.DB_FILE)
        except OSError:
            pass
