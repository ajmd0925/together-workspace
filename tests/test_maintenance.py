import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
import maintenance
import server


class BackupTests(unittest.TestCase):
    def test_round_trip_restore_keeps_safety_snapshot_and_invalidates_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = server.DATA
            server.DATA = Path(directory)
            try:
                server.init_db()
                with server.db() as con:
                    con.execute('INSERT INTO users VALUES(?,?,?,?)', ('a', 'Before', 'a@example.test', 'hash'))
                    con.execute('INSERT INTO sessions VALUES(?,?,?)', ('old-session', 'a', 9999999999))
                snapshot = maintenance.backup(directory)
                with server.db() as con:
                    con.execute("UPDATE users SET name='After' WHERE id='a'")
                safety = maintenance.restore(directory, snapshot)
                self.assertTrue(safety.is_file())
                with server.db() as con:
                    self.assertEqual(con.execute("SELECT name FROM users WHERE id='a'").fetchone()[0], 'Before')
                    self.assertEqual(con.execute('SELECT count(*) FROM sessions').fetchone()[0], 0)
                with closing(sqlite3.connect(safety)) as con:
                    self.assertEqual(con.execute("SELECT name FROM users WHERE id='a'").fetchone()[0], 'After')
                with maintenance.server_lock(directory):
                    with self.assertRaises(RuntimeError):
                        maintenance.restore(directory, snapshot)
                bad = Path(directory) / 'invalid.db'
                bad.write_bytes(b'not a database')
                with self.assertRaises(sqlite3.DatabaseError):
                    maintenance.restore(directory, bad)
                with server.db() as con:
                    self.assertEqual(con.execute("SELECT name FROM users WHERE id='a'").fetchone()[0], 'Before')
            finally:
                server.DATA = previous
