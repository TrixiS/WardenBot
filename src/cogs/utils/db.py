import sqlite3
import pymysql
import logging

from asyncio import Lock
from enum import Enum
from typing import Optional, Collection, Any
from string import whitespace


class DbType(Enum):
    SQLite  = 0
    MySQL   = 1


class Db:
    param_lit = '?'
    arg_lits = "`'"
    semicolon = ';'
    special_symbols = "`';-"
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

    async def commit(self) -> None:
        async with self._lock:
            self.conn.commit()

    async def execute(self, query: str, *args: Collection, fetch_all=False, with_commit=False) -> Optional[Any]:
        sql = self.prepare_query(query, list(args))

        if not self.prevent_injection(sql):
            logging.warn(f"SQL injection detected")
            return None

        try:
            self.cursor.execute(sql)

            if with_commit:
                await self.commit()

            if fetch_all:
                return self.cursor.fetchall()

            return self.cursor.fetchone()                
        except Exception as e:
            logging.warn(f"{str(e)} ({sql})")
            return None

    def prevent_injection(self, query: str) -> bool:
        in_param = False

        for s in query:
            if s in self.arg_lits:
                in_param = not in_param

            if s == self.semicolon and not in_param:
                return False

        return True

    def prepare_query(self, query: str, to_substit: list) -> str:
        params_count = query.count(self.param_lit)
        args_len = len(to_substit)

        if params_count != args_len:
            raise Exception(f"Params count must be equal to args length ({params_count}:{args_len})")

        if params_count == 0:
            return query

        sql = ""

        for s in query:
            if s == self.param_lit:
                arg = to_substit.pop(0)

                if isinstance(arg, str):
                    arg = arg.rstrip(self.special_symbols + whitespace)
                elif isinstance(arg, int) or isinstance(arg, float):
                    if arg < self.int_min_bound:
                        arg = self.int_min_bound
                    elif arg > self.int_max_bound:
                        arg = self.int_max_bound
                elif arg is None:
                    arg = self.null
            
                if isinstance(arg, str) and arg != self.null:
                    sql += f"'{arg}'"
                else:
                    sql += str(arg)
            else:
                sql += s
                
        return sql