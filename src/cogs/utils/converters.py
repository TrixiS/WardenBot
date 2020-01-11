import discord

from discord.ext import commands
from asyncio import iscoroutinefunction as is_coro


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


class HumanTime(commands.Converter):

    async def convert(self, ctx, arg):
        seconds_in = ctx.lang["time_map"]
        
        try:
            return int(arg[:-1]) * seconds_in[arg[-1]]
        except:
            raise commands.BadArgument(ctx.lang["errors"]["time_convert_failed"])


class EqualMember(commands.MemberConverter):

    async def convert(self, ctx, arg):
        member = await super().convert(ctx, arg)

        if member == ctx.author:
            raise commands.BadArgument(ctx.lang["errors"]["cant_use_to_yourself"])

        if ctx.author == ctx.guild.owner:
            return member

        member_perms = ctx.channel.permissions_for(member)
        author_perms = ctx.channel.permissions_for(ctx.author)

        if author_perms <= member_perms:
            raise commands.BadArgument(
                ctx.lang["errors"]["member_has_eq_over_perms"].format(member.mention))

        return member


class _Check(commands.Converter):

    def __init__(self, *, converter=None, check=None):
        self.converter = converter
        self.check = check

    def __getitem__(self, params):
        if not isinstance(params, tuple):
            params = (params, )

        if len(params) < 1:
            raise TypeError("Check[...] only takes > 1 arguments")

        if len(params) == 1:
            params = (params[0], lambda x: bool(x))

        converter, check = params

        if not callable(check):
            raise TypeError("Check function must be callable")

        if not (callable(converter) or isinstance(converter, commands.Converter) or converter is type(None)):
            raise TypeError("Converter parameter must be commands.Converter or a function")

        return self.__class__(converter=converter, check=check)

    async def convert(self, ctx, argument):
        convertered = None
        
        if isinstance(self.converter, commands.Converter):
            convertered = await self.converter.convert(ctx, argument)
        elif not is_coro(self.converter):
            convertered = self.converter(argument)
        elif is_coro(self.converter):
            convertered = await self.converter(argument)
        else:
            convertered = type(self.converter)(argument)

        checked = False

        if is_coro(self.check):
            checked = await self.check(convertered)
        elif not is_coro(self.check):
            checked = self.check(convertered)

        if not checked:
            raise commands.BadArgument(ctx.lang["errors"]["not_checked"])

        return convertered


Check = _Check()