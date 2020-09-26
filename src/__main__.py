from os import system

system("git pull")

import logging
from bot import Warden
from config import Config
from cogs.utils.global_checks import *

logging.basicConfig(
    filename="warden.log",
    level=logging.ERROR,
    format=f"%(asctime)s - %(levelname)s: %(message)s")

config = Config()

bot = Warden(command_prefix=config.prefixes, config=config)

bot.add_check(none_guild)
bot.add_check(has_message_perms)
bot.add_check(is_command_disabled)

bot.load_cogs()
bot.load_langs()

bot.run()
