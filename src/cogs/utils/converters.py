import discord

from discord.ext import commands

class Uint(commands.Converter):

    def __init__(self, include_zero=True):
        self.include_zero = include_zero

    async def convert(self, ctx, arg):
        arg = int(arg)

        if arg < 0:
            raise commands.BadArgument(ctx.lang["errors"]["arg_over_or_equal_zero"])

        if arg == 0 and not self.include_zero:
            raise commands.BadArgument(ctx.lang["errors"]["arg_over_zero"])

        return arg


class Index:

    def __init__(self, value: int):
        self.value = value

    def humanize(self) -> int:
        return self.value + 1


class IndexConverter(Uint):

    async def convert(self, ctx, arg):
        convertered = await super().convert(ctx, arg) - 1

        return Index(convertered if convertered >= 0 else 0)
        