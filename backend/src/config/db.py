# SQLite via Python's built-in sqlite3 module - no pip install needed,
# and unlike Node's node:sqlite this one isn't even experimental; it's
# been in the standard library for years.
import os
import pathlib
import sqlite3
import threading

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

_db_path_env = os.environ.get('DB_PATH')
if _db_path_env:
    DB_PATH = pathlib.Path(_db_path_env)
    if not DB_PATH.is_absolute():
        DB_PATH = pathlib.Path.cwd() / DB_PATH
else:
    DB_PATH = DATA_DIR / 'planner.db'

_connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
_connection.row_factory = sqlite3.Row
_connection.isolation_level = None  # autocommit; we open transactions explicitly when we need one
_connection.execute('PRAGMA journal_mode = WAL')
_connection.execute('PRAGMA foreign_keys = ON')

_schema_path = BASE_DIR / 'db' / 'schema.sql'
_connection.executescript(_schema_path.read_text())


class Database:
    """A thin wrapper so controllers read like `db.get(sql, params)` /
    `db.all(...)` / `db.run(...)` - close to the shape used in the
    JavaScript version of this backend, just idiomatic Python underneath.

    Every call goes through `self.lock`. The server now handles requests
    on multiple threads (see http_kit.py's ThreadingHTTPServer), but this
    is a single shared sqlite3.Connection - Python's sqlite3 module
    doesn't promise it's safe for two threads to call execute() on it at
    the exact same moment, so this lock serializes access instead of
    hoping for the best. SQLite operations are fast, so in practice this
    is not a meaningful bottleneck at the scale this app runs at.
    Anything that needs a multi-statement transaction (see
    planner_service.py) should hold `db.lock` for the whole transaction,
    not just call db.run() repeatedly, so a request from a different
    user can't run its own statements in between.
    """

    def __init__(self, connection):
        self.connection = connection
        self.lock = threading.RLock()

    def get(self, sql, params=()):
        with self.lock:
            row = self.connection.execute(sql, params).fetchone()
            return dict(row) if row is not None else None

    def all(self, sql, params=()):
        with self.lock:
            return [dict(row) for row in self.connection.execute(sql, params).fetchall()]

    def run(self, sql, params=()):
        with self.lock:
            cursor = self.connection.execute(sql, params)
            return {'changes': cursor.rowcount, 'lastrowid': cursor.lastrowid}


db = Database(_connection)
