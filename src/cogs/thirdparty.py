import re
import discord

from discord.ext import commands

LIGTAZ_GUILD_ID = 642389039579791360
VIDEOS_CHANNEL_ID = 719902573834010694


class ThirdParty(commands.Cog):

    url_pattern = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

    def __init__(self, bot):
        self.bot = bot

    async def filter_youtube_links(self, message):
        if message.guild is None or message.channel is None:
            return

        if message.guild.id != LIGTAZ_GUILD_ID or message.channel.id != VIDEOS_CHANNEL_ID:
            return

        if message.content is None or len(message.content) == 0:
            return

        matches = set(self.url_pattern.findall(message.content.lower()))

        if len(matches) == 0:
            return await message.delete()

        for match in matches:
            if "youtu" not in match:
                return await message.delete()    

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.filter_youtube_links(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await self.filter_youtube_links(after)


def setup(bot):
    bot.add_cog(ThirdParty(bot))