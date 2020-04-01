import sqlite3
import pymysql
import logging

from asyncio import Lock
from enum import Enum
from typing import Optional, Collection, Any
from random import random
from time import time


def int_timestamp() -> int:
    return int(time())


class DbType(Enum):
    SQLite  = 0
    MySQL   = 1


class DataBase:
    param_lit = '?'
    null = "NULL"

    int_min_bound = -999999999999999999
    int_max_bound = 999999999999999999

    def __init__(self, db_type, **kwargs):
        if db_type is DbType.SQLite:
            database = kwargs.pop("database")
            check_same = kwargs.pop("check_same_thread", True)
            self.conn = sqlite3.connect(database, check_same_thread=check_same)
        elif db_type is DbType.MySQL:
            self.conn = pymysql.connect(**kwargs)
        else:
            raise Exception("Unsupported DbType")

        self.db_type = db_type
        self.cursor = self.conn.cursor()

        self._lock = Lock()
        self._adapt()

    def _make_safe_value(self, number):
        return max(min(number, self.int_max_bound), self.int_min_bound)

    def _make_safe_ints(self, ints):
        result = []

        for value in ints:
            if isinstance(value, int):
                result.append(self._make_safe_value(value))
            else:
                result.append(value)

        return result
        
    def _adapt(self) -> None:
        if self.db_type is DbType.SQLite:
            self.conn.create_function("rand", 0, random)
            self.conn.create_function("unix_timestamp", 0, int_timestamp)

    def _wrap_args(self, seq):
        for row in seq:
            yield (row, )

    async def commit(self) -> None:
        async with self._lock:
            self.conn.commit()

    async def execute(self, query: str, *args, **kwargs):
        if self.db_type is DbType.MySQL:
            query = self.prepare_query(query)

        try:
            self.cursor.execute(query, self._make_safe_ints(args))
        except Exception as e:
            logging.error(f"{str(e)} ({query}) ({args})")
            return

        return await self.fetch(**kwargs)

    async def executemany(self, query: str, args, **kwargs):
        if self.db_type is DbType.MySQL:
            query = self.prepare_query(query)

        if kwargs.pop("wrap_args", False):
            args = self._wrap_args(args)

        try:
            self.cursor.executemany(query, args)
        except Exception as e:
            logging.error(f"{str(e)} ({query}) ({args})")
            return

        return await self.fetch(**kwargs)

    async def fetch(self, *, fetch_all=False, with_commit=False):
        if with_commit:
            count = self.cursor.rowcount

            if count:
                await self.commit()

            return count

        if fetch_all:
            return self.cursor.fetchall()

        fetched = self.cursor.fetchone()

        return fetched[0] if fetched is not None and len(fetched) == 1 \
            else fetched

    def prepare_query(self, query: str) -> str:
        result = ""

        in_param = False

        for s in query:
            if s in "`'\"":
                in_param = not in_param
            
            if not in_param and s == self.param_lit:
                s = r"%s"

            result += s

        return result
