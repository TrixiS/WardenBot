from cogs.utils.db import DataBase
from cogs.utils.strings import multi_replace
from cogs.utils.plugin_loader import PluginLoader

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

        self.config = kwargs.pop("config")
        self.path = Path(__file__).parent.resolve().absolute()
        self.assets_path = self.path.parent / "assets"
        self.session = ClientSession(loop=self.loop)
        self.db = DataBase(self.config.db_type, **self.config.database_settings)
        self.uptime = None
        self.langs = None
        
        if self.config.use_csharp_plugins:
            self.plugin_loader = PluginLoader(self)
        else:
            self.plugin_loader = None

    def load_langs(self):
        langs = {}

        for path in (self.assets_path / "langs").glob("*.json"):
            if path.is_file():
                with path.open(encoding='utf-8', mode='r') as f:
                    langs[path.stem] = json_load(f)

        self.langs = langs

    def load_cogs(self, reload=False):

        def to_ext(path):
            parent = str(path.parent.parent.resolve().absolute())
            path = str(path.resolve().absolute())

            return multi_replace(path[len(parent) + 1:-3], ('\\', '/'), '.')

        for path in (self.path / "cogs").glob("*.py"):
            if not path.is_file() or path.name.startswith('_') or path.name.endswith('_'):
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

    def get_role(self, guild_id, role_id):
        guild = self.get_guild(guild_id)

        if guild is None:
            return

        return guild.get_role(role_id)

    def is_owner(self, user):
        return user.id in self.config.owners

    def run(self):
        super().run(self.config.bot_token, reconnect=True)

    async def close(self):
        await self.session.close()
        await super().close()

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

        await self.invoke(ctx)

    async def on_message(self, message):
        if not message.author.bot:
            await self.process_commands(message)

    async def on_ready(self):
        self.uptime = datetime.now()
        logging.info(f'{self.user.name} started with {len(self.guilds)} guilds')
