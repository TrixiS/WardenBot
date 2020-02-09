from os import system

system("git pull")

import logging
from bot import Warden
from config import Config
from cogs.utils.global_checks import *

logging.basicConfig(level=logging.INFO, format=f"%(levelname)s: %(message)s - %(asctime)s")

config = Config()

bot = Warden(command_prefix=config.prefixes, config=config)

bot.add_check(none_guild)
bot.add_check(has_message_perms)

bot.load_cogs()
bot.load_langs()
bot.load_plugins()

bot.run()
