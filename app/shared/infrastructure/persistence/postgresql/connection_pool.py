import os
from contextlib import contextmanager,nullcontext
from contextvars import ContextVar
from threading import Lock
from psycopg.rows import dict_row,tuple_row
from psycopg_pool import ConnectionPool

_pool=None
_lock=Lock()
_current=ContextVar('analytics_connection',default=None)

def get_pool():
    global _pool
    with _lock:
        if _pool is None:
            _pool=ConnectionPool(os.environ['DATABASE_URL'],min_size=0,max_size=5,timeout=10,
                                 kwargs={'connect_timeout':15},open=False)
            _pool.open()
        return _pool

@contextmanager
def connect(dict_rows=False):
    active=_current.get()
    with (nullcontext(active) if active is not None else get_pool().connection()) as connection:
        previous=connection.row_factory
        connection.row_factory=dict_row if dict_rows else tuple_row
        try:
            yield connection
        finally:
            connection.row_factory=previous

@contextmanager
def transaction():
    if _current.get() is not None:
        yield
        return
    with get_pool().connection() as connection:
        token=_current.set(connection)
        try:
            yield
        finally:
            _current.reset(token)

def close_pool():
    global _pool
    with _lock:
        if _pool is not None:
            _pool.close()
            _pool=None
