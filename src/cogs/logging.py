import discord

from discord.ext import commands
from .utils.checks import is_commander
from .utils.constants import EmbedConstants


class Logging(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def get_log_channel(self, guild):
        check = await self.bot.db.execute("SELECT `channel` FROM `log` WHERE `log`.`server` = ?",
            guild.id)

        return guild.get_channel(check)

    @commands.group(invoke_without_command=True)
    @is_commander()
    async def log(self, ctx, *, channel: discord.TextChannel=None):
        if channel is None:
            log_channel = await self.get_log_channel(ctx.guild)

            if log_channel is None:
                await ctx.answer(ctx.lang["logging"]["no_log_channel"])
            else:
                await ctx.answer(ctx.lang["logging"]["is_log_channel"].format(log_channel.mention))
        else:
            check = await self.bot.db.execute("UPDATE `log` SET `channel` = ? WHERE `log`.`server` = ?",
                channel.id, ctx.guild.id, with_commit=True)

            if not check:
                await self.bot.db.execute("INSERT INTO `log` VALUES (?, ?)",
                    ctx.guild.id, channel.id, with_commit=True)

            await ctx.answer(ctx.lang["logging"]["new_log_channel"].format(channel.mention))

    @log.command(name="delete")
    @is_commander()
    async def log_delete(self, ctx):
        check = await self.bot.db.execute("DELETE FROM `log` WHERE `server` = ?",
            ctx.guild.id, with_commit=True)
        
        if not check:
            await ctx.answer(ctx.lang["logging"]["no_log_channel"])
        else:
            await ctx.answer(ctx.lang["logging"]["channel_deleted"])

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        log_channel = await self.get_log_channel(message.guild)

        if log_channel is None or not log_channel.permissions_for(message.guild.me).send_messages:
            return

        lang = await self.bot.get_lang(message.guild)
        color = await self.bot.get_color(message.guild)

        em = discord.Embed(
            colour=color, 
            description=lang["logging"]["message_deleted"].format(
                message.author.mention, message.channel.mention))

        if message.content:
            em.add_field(
                name=lang["logging"]["message_content"], 
                value=message.content[:EmbedConstants.FIELD_VALUE_MAX_LEN])

        image = discord.utils.find(lambda a: a.width or a.height, message.attachments)

        if image is not None:
            em.set_image(url=image.proxy_url)

        em.set_author(name=message.author.name, icon_url=message.author.avatar_url)

        await log_channel.send(embed=em)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or after.author.bot:
            return

        log_channel = await self.get_log_channel(after.guild)

        if log_channel is None or not log_channel.permissions_for(after.guild.me).send_messages:
            return

        lang = await self.bot.get_lang(after.guild)
        color = await self.bot.get_color(after.guild)

        em = discord.Embed(
            colour=color, 
            description=lang["logging"]["message_edited"].format(
                after.author.mention, after.channel.mention))

        if before.content:
            em.add_field(
                name=lang["logging"]["before_content"],
                value=before.content[:EmbedConstants.FIELD_VALUE_MAX_LEN], 
                inline=False)

        if after.content:
            em.add_field(
                name=lang["logging"]["after_content"],
                value=after.content[:EmbedConstants.FIELD_VALUE_MAX_LEN],
                inline=False)

        image = discord.utils.find(
            lambda a: a.width or a.height, 
            before.attachments + after.attachments)
        
        if image is not None:
            em.set_image(url=image.proxy_url)

        em.set_author(name=after.author.name, icon_url=after.author.avatar_url)

        await log_channel.send(embed=em)


def setup(bot):
    bot.add_cog(Logging(bot))