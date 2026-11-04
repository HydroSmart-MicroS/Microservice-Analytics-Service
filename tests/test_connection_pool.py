import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
from psycopg.rows import dict_row,tuple_row
from app.shared.infrastructure.persistence.postgresql.connection_pool import connect,transaction

MODULE='app.shared.infrastructure.persistence.postgresql.connection_pool'
class Pool:
    def __init__(self):self.connection_value=SimpleNamespace(row_factory=tuple_row);self.failure=None;self.checkouts=0
    @contextmanager
    def connection(self):
        self.checkouts+=1
        try:yield self.connection_value
        except Exception as error:self.failure=error;raise
class ConnectionPoolTests(unittest.TestCase):
    def test_dictionary_rows_do_not_leak_into_the_next_tuple_query(self):
        pool=Pool()
        with patch(MODULE+'.get_pool',return_value=pool):
            with connect(dict_rows=True) as conn:self.assertIs(conn.row_factory,dict_row)
            with connect() as conn:self.assertIs(conn.row_factory,tuple_row)
    def test_failure_reaches_the_pool_transaction_context(self):
        pool=Pool();failure=ValueError('rollback')
        with patch(MODULE+'.get_pool',return_value=pool):
            with self.assertRaises(ValueError):
                with connect(dict_rows=True):raise failure
        self.assertIs(pool.failure,failure)
        self.assertIs(pool.connection_value.row_factory,tuple_row)
    def test_one_event_shares_one_transaction_and_restores_row_formats(self):
        pool=Pool()
        with patch(MODULE+'.get_pool',return_value=pool):
            with transaction():
                with connect(dict_rows=True) as first:
                    with connect() as second:self.assertIs(first,second);self.assertIs(second.row_factory,tuple_row)
                    self.assertIs(first.row_factory,dict_row)
            with connect():pass
        self.assertEqual(pool.checkouts,2)
