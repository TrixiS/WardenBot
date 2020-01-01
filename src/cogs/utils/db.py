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

    async def commit(self) -> None:
        async with self._lock:
            self.conn.commit()

    async def execute(self, query: str, *args: Collection, fetch_all=False, with_commit=False) -> Optional[Any]:
        try:
            if self.db_type is DbType.MySQL:
                self.cursor.execute(self.prepare_query(query, list(args)))
            elif self.db_type is DbType.SQLite:
                self.cursor.execute(query, args)

            if with_commit:
                await self.commit()

            if fetch_all:
                return self.cursor.fetchall()

            fetched = self.cursor.fetchone()

            if fetched is not None and len(fetched) == 1:
                return fetched[0]

            return fetched
        except Exception as e:
            logging.warn(f"{str(e)} ({query}) ({args})")
            return None

    def prevent_injection(self, arg: Any) -> Any:
        if isinstance(arg, int) or isinstance(arg, float):
            if arg > self.int_max_bound:
                arg = self.int_max_bound
            elif arg < self.int_min_bound:
                arg = self.int_min_bound

            arg = str(arg)
        elif isinstance(arg, str):
            if len(arg) == 0:
                return self.null

            new_arg = ""
            
            for s in arg:
                if s in "'\"":
                    new_arg += ('\\' + s)
                else:
                    new_arg += s

            arg = f"'{new_arg}'"
        elif isinstance(arg, bool):
            arg = str(int(arg))
        else:
            arg = self.null

        return arg

    def prepare_query(self, query: str, to_substit: list) -> str:
        params_count = query.count(self.param_lit)
        args_len = len(to_substit)

        if params_count != args_len:
            raise Exception(f"Params count must be equal to args length ({params_count}:{args_len}) ({query})")

        if params_count == 0:
            return query

        sql = ""

        for s in query:
            if s == self.param_lit:
                arg = to_substit.pop(0)

                sql += self.prevent_injection(arg)
            else:
                sql += s
                
        return sql