import discord
import logging
import traceback
import sys
import traceback
import datetime as dt
import math

from discord.ext import commands


class ErrorHandler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        err_type, value, traceback = sys.exc_info()
        logging.error(f"{event} -> {err_type} {value} {traceback[-50:]}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        logging.info(str(error))

        if isinstance(error, commands.DisabledCommand):
            return
        elif isinstance(error, commands.CommandOnCooldown):
            logging.info(error.retry_after)
            message = ctx.lang["errors"]["on_cooldown"].format(
                (dt.datetime.now() + dt.timedelta(seconds=math.ceil(error.retry_after))).strftime(ctx.lang["long_date"]))
        elif isinstance(error, commands.CheckFailure):
            message = error.message
        elif isinstance(error, discord.DiscordException):
            message = ctx.lang["errors"]["exception"].format(
                ctx.command.qualified_name)
        else:
            await ctx.answer(ctx.lang["errors"]["unknown_error"])
            fmt = traceback.format_exception(type(error), error, error.__traceback__)
            logging.error(''.join(fmt))

        em = discord.Embed(colour=ctx.color)
        
        em.add_field(
            name=ctx.lang["error_handler"]["title"].format(ctx.command.qualified_name),
            value=message)
        em.set_author(
            name=ctx.author.name, 
            icon_url=ctx.author.avatar_url)

        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(ErrorHandler(bot))