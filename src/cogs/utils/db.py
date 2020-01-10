import sqlite3
import pymysql
import logging

from asyncio import Lock
from enum import Enum
from typing import Optional, Collection, Any
from random import random
from time import time


class DbType(Enum):
    SQLite  = 0
    MySQL   = 1


class Db:
    param_lit = '?'
    null = "NULL"

    int_min_bound = -9223372036854775808
    int_max_bound = 9223372036854775807

    def __init__(self, db_type, **kwargs):
        if db_type is DbType.SQLite:
            database = kwargs.pop("database")
            self.conn = sqlite3.connect(database)
        elif db_type is DbType.MySQL:
            self.conn = pymysql.connect(**kwargs)
        else:
            raise Exception("Unsupported DbType")

        self.db_type = db_type
        self.cursor = self.conn.cursor()

        self._lock = Lock()
        self._adapt()

    def _adapt(self) -> None:
        if self.db_type is DbType.SQLite:
            self.conn.create_function("rand", 0, random)
            self.conn.create_function("unix_timestamp", 0, time)

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
            self.cursor.execute(query, args)
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
            elif s == self.param_lit:
                s = r"%s"

            result += s

        return result
