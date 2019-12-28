import discord

from discord.ext import commands


class MemberOrAuthor(commands.MemberConverter):

    async def convert(self, ctx, arg):
        try:
            return await super().convert(ctx, arg)
        except:
            return ctx.author


class Uint(commands.Converter):

    def __init__(self, include_zero=False):
        self.include_zero = include_zero

    async def convert(self, ctx, arg):
        arg = int(arg)

        if arg < 0:
            raise commands.BadArgument("Argument must be >= 0")

        if arg == 0 and not self.include_zero:
            raise commands.BadArgument("Argument must be > 0")

        return arg


class Index(Uint):

    async def convert(self, ctx, arg):
        convertered = await super().convert(ctx, arg) - 1

        return convertered if convertered >= 0 else 0