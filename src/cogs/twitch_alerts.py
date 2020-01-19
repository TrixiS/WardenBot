import discord

from discord.ext import commands
from twitch import TwitchClient


class TwtichAlertsCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.client = TwitchClient(client_id=bot.config.twitch_api_token)


def setup(bot):
    bot.add_cog(TwtichAlertsCog(bot))