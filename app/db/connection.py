import os
import psycopg2
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()

_pool = None


def _make_pool():
    return psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=5,
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        sslmode="require",
        options="-c TimeZone=America/Mexico_City",
    )


def _get_pool():
    global _pool
    if _pool is None or _pool.closed:
        _pool = _make_pool()
    return _pool


class _PooledConn:
    """Wraps a real connection; close() returns it to the pool instead of closing it."""
    def __init__(self, conn, pool):
        self._conn = conn
        self._pool = pool

    def close(self):
        try:
            if not self._conn.closed:
                self._conn.rollback()
            self._pool.putconn(self._conn)
        except Exception:
            pass

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_conn():
    try:
        pool = _get_pool()
        conn = pool.getconn()
        return _PooledConn(conn, pool)
    except Exception as e:
        print(f"Error obteniendo conexión del pool: {e}")
        return None
