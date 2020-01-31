import logging

from os import system
from bot import Warden
from cogs.utils.config import Config
from cogs.utils.global_checks import *

system("git pull")

logging.basicConfig(level=logging.INFO, format=f"%(levelname)s: %(message)s - %(asctime)s")
#logging.getLogger("asyncio").setLevel(logging.CRITICAL)

config = Config()

bot = Warden(command_prefix=config.prefixes, config=config)

bot.add_check(none_guild)
bot.add_check(has_message_perms)

bot.load_cogs()
bot.load_langs()

bot.run(config.bot_token, reconnect=True)
