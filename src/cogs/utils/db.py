import sqlite3
import pymysql

from asyncio import Lock
from enum import Enum
from typing import Optional, Collection, Any


class DbType(Enum):
    SQLite  = 0
    MySQL   = 1


class Db:

    def __init__(self, *args):
        if args[0] is DbType.SQLite:
            self.conn = sqlite3.connect(args[4])
        elif args[0] is DbType.MySQL:
            self.conn = pymysql.connect(args[1], args[2], args[3], args[4])
        else:
            raise Exception(f"Unsupported DbType - {type(args[0]).__name__}")

        self.cursor = self.conn.cursor()
        self.db_type = args[0]
        self._lock = Lock()

    async def commit(self) -> None:
        async with self._lock:
            self.conn.commit()

    async def select() -> Collection[Any]:
        pass

    async def update() -> None:
        pass

    async def delete() -> None:
        pass
        