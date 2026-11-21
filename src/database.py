from contextlib import contextmanager
from typing import Generator, Tuple, Any
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from .config import Settings

class DatabaseManager:
    """Thread-safe PostgreSQL connection pool wrapper."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.pool: pool.ThreadedConnectionPool | None = None
        self._init_pool()

    def _init_pool(self) -> None:
        self.pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=self.settings.DB_HOST,
            port=self.settings.DB_PORT,
            dbname=self.settings.DB_NAME,
            user=self.settings.DB_USER,
            password=self.settings.DB_PASSWORD,
            cursor_factory=RealDictCursor
        )

    @contextmanager
    def get_connection(self) -> Generator[Tuple[Any, Any], None, None]:
        if not self.pool or self.pool.closed:
            self._init_pool()
        conn = self.pool.getconn()
        cursor = conn.cursor()
        try:
            yield (conn, cursor)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def close_pool(self) -> None:
        if self.pool and not self.pool.closed:
            self.pool.closeall()
