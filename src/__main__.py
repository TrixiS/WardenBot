import logging

from bot import Warden
from cogs.utils.config import Config


logging.basicConfig(level=logging.INFO, format=f"%(levelname)s: %(message)s - %(asctime)s")

config = Config()

bot = Warden(command_prefix=config.prefixes, config=config)
bot.run(config.bot_token, reconnect=True)