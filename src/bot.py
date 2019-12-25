from cogs.utils.db import *
from cogs.utils.config import Config
from cogs.utils.strings import multi_replace

from discord.ext.commands import Bot
from pathlib import Path
from aiohttp import ClientSession
from datetime import datetime
from json import load as json_load

import logging 


class Warden(Bot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = kwargs.pop("config", Config())
        
        self.path = Path(__file__).parent.absolute()
        self.cogs_path = Path(self.config.cogs_path).absolute()
        self.langs_path = Path(self.config.langs_path).absolute()
        
        self.session = ClientSession(loop=self.loop)

        self.db = Db(DbType.MySQL if self.config.use_mysql else DbType.SQLite, \
            database=self.config.database, password=self.config.password, user=self.config.user, host=self.config.host)

        self.uptime = None

        self._load_langs()
        self._load_cogs()

    def __del__(self):
        self.db.conn.close()
        self.session.close()

    def _load_langs(self, reload=False):
        langs = {}

        for path in self.langs_path.glob("*.json"):
            if path.is_file():
                with path.open(encoding='utf-8', mode='r') as f:
                    langs[path.stem] = json_load(f)

        self.langs = langs

    def _load_cogs(self):

        def to_ext(path):
            parent = str(path.parent.absolute())
            path = str(path)

            return multi_replace(path[len(parent):], ['\\', '/'], '.')

        for path in self.cogs_path.glob("*.cog.py"):
            if not path.is_file():
                continue

            try:
                ext_path = to_ext(path)
                self.load_extension(ext_path)

                logging.info(f"Loaded - {ext_path}")
            except Exception as e:
                logging.debug(f"Failed to load extension {ext_name}:", "\n", f"{str(e)} - {e.__traceback__}")
