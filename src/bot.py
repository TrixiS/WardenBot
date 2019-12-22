from discord.ext.commands import Bot
from pathlib import Path
from aiohttp import ClientSession

from config import Config


class Warden(Bot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.path = Path(__file__).parent.resolve()
        self.http_session = ClientSession(loop=self.loop)
        self.config = Config()