import discord

from discord.ext import commands
from .utils.checks import is_moderator, is_commander


class ModerationCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(ModerationCog(bot))