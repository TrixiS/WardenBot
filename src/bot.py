from cogs.utils.db import Db
from cogs.utils.config import Config
from cogs.utils.strings import multi_replace

from discord.ext.commands import AutoShardedBot
from pathlib import Path
from aiohttp import ClientSession
from datetime import datetime
from json import load as json_load
from context import WardenContext

import logging
import discord


class Warden(AutoShardedBot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = kwargs.pop("config", Config())
        
        self.path = Path(__file__).parent.resolve().absolute()
        self.cogs_path = self.path.joinpath(self.config.cogs_path).resolve()
        self.langs_path = Path(self.config.langs_path).absolute().resolve()
        
        self.session = ClientSession(loop=self.loop)

        self.db = Db(self.config.db_type, **self.config.to_dict("database", "host", "user", "password"))

        self.uptime = None
        self.langs = {}

    def load_langs(self):
        langs = {}

        for path in self.langs_path.glob("*.json"):
            if path.is_file():
                with path.open(encoding='utf-8', mode='r') as f:
                    langs[path.stem] = json_load(f)

        self.langs = langs

    def load_cogs(self, reload=False):

        def to_ext(path):
            parent = str(path.parent.parent.resolve().absolute())
            path = str(path.resolve().absolute())

            return multi_replace(path[len(parent) + 1:-3], ['\\', '/'], '.')

        for path in self.cogs_path.glob("*.py"):
            if not path.is_file():
                continue

            try:
                ext_path = to_ext(path)
                
                if reload and ext_path in self.extensions:
                    self.unload_extension(ext_path)

                self.load_extension(ext_path)

                logging.info(f"Loaded - {ext_path}")
            except Exception as e:
                logging.error(f"Failed to load extension {ext_path}:\n{str(e)}")

    def get_member(self, guild_id, member_id):
        guild = self.get_guild(guild_id)

        if guild is None:
            return

        return guild.get_member(member_id)

    async def get_color(self, guild):
        color = await self.db.execute("SELECT `color` FROM `colors` WHERE `colors`.`server` = ?",
            guild.id)

        color = color or self.config.default_color

        return discord.Colour.from_rgb(*map(int, color.split(';')))

    async def get_lang(self, guild):
        lang = await self.db.execute("SELECT `lang` FROM `langs` WHERE `langs`.`server` = ?",
            guild.id)

        return self.langs[lang or self.config.default_lang]

    async def process_commands(self, message):
        if message.guild is None:
            return

        ctx = await self.get_context(message, cls=WardenContext)

        if ctx.command is None:
            return

        ctx.lang = await self.get_lang(message.guild)
        ctx.color = await self.get_color(message.guild)

        from cogs.economy import EconomyCommand

        if isinstance(ctx.command, EconomyCommand):
            economy_cog = self.get_cog("Economy")
            ctx.currency = await economy_cog.eco.get_currency(message.guild)

        await self.invoke(ctx)

    async def on_message(self, message):
        if not message.author.bot:
            await self.process_commands(message)

    async def on_ready(self):
        self.uptime = datetime.now()
        logging.info(f'{self.user.name} started with {len(self.guilds)} guilds')
