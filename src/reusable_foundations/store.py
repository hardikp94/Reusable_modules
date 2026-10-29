"""Small durable JSON repository. Transactions serialize competing writers."""
from contextlib import contextmanager
import json
import sqlite3
import threading


class Store:
    def __init__(self, path=":memory:"):
        self.connection = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.connection.execute("CREATE TABLE IF NOT EXISTS records (namespace TEXT, key TEXT, value TEXT NOT NULL, PRIMARY KEY(namespace,key))")
        self._lock = threading.RLock()

    @contextmanager
    def transaction(self):
        with self._lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield self
                self.connection.execute("COMMIT")
            except BaseException:
                self.connection.execute("ROLLBACK")
                raise

    def get(self, namespace, key):
        with self._lock:
            row = self.connection.execute("SELECT value FROM records WHERE namespace=? AND key=?", (namespace, str(key))).fetchone()
            return json.loads(row[0]) if row else None

    def put(self, namespace, key, value):
        with self._lock:
            self.connection.execute("INSERT INTO records VALUES (?,?,?) ON CONFLICT(namespace,key) DO UPDATE SET value=excluded.value", (namespace, str(key), json.dumps(value)))

    def delete(self, namespace, key):
        with self._lock:
            self.connection.execute("DELETE FROM records WHERE namespace=? AND key=?", (namespace, str(key)))

    def all(self, namespace):
        with self._lock:
            return [json.loads(r[0]) for r in self.connection.execute("SELECT value FROM records WHERE namespace=?", (namespace,))]

    def close(self):
        self.connection.close()
