import discord
import logging
import traceback
import sys
import traceback

from discord.ext import commands


class ErrorHandler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        err_type, value, traceback = sys.exc_info()
        logging.error(f"{event} -> {err_type} {value} {traceback[-50:]}")

    # TODO: add lang support for d.py exceptions
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandError):
            message = getattr(error, "message", str(error))

            em = discord.Embed(colour=ctx.color)

            em.add_field(
                name=ctx.lang["error_handler"]["title"].format(ctx.command.qualified_name),
                value=message)

            em.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

            await ctx.send(embed=em)
        else:
            await ctx.answer(ctx.lang["errors"]["unknown_error"])
            fmt = traceback.format_exception(type(error), error, error.__traceback__)
            logging.error(''.join(fmt))


def setup(bot):
    bot.add_cog(ErrorHandler(bot))