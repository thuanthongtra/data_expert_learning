from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from support_tickets.config import build_connection_string


@contextmanager
def connection():
    conn = psycopg.connect(build_connection_string(), row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
