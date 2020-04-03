import discord
import string
import datetime as dt

from discord.ext import commands


class without_whitespace(commands.clean_content):

    async def convert(self, ctx, arg):
        result = await super().convert(ctx, arg)

        if any(s in result for s in string.whitespace[1:]):
            raise commands.BadArgument(ctx.lang["fun"]["alpha_needed"])

        return result


class EnumConverter(commands.Converter):

    def __init__(self, enum_cls):
        self.enum_cls = enum_cls

    async def convert(self, ctx, arg):
        arg = arg.lower()

        result = discord.utils.find(
            lambda x: x[0].lower() == arg,
            self.enum_cls.__members__.items())

        if result is None:
            raise commands.BadArgument(ctx.lang["errors"]["cant_convert_enum"].format(
                self.enum_cls.__qualname__))

        return result[1]

    @staticmethod
    def convert_value(enum_cls, value):
        return discord.utils.find(
            lambda x: x.value == value,
            enum_cls.__members__.values())


class CommandConverter(commands.Converter):

    __qualname__ = "Command"

    def __init__(self, cls=commands.Command):
        self.cls = cls

    async def convert(self, ctx, arg):
        command = ctx.bot.get_command(arg)

        if command is None:
            raise commands.BadArgument(ctx.lang["help"]["command_not_found"])

        if not isinstance(command, self.cls):
            raise commands.BadArgument(ctx.lang["errors"]["ivalid_command"].format(
                self.cls.__qualname__))

        return command
        

class uint(commands.Converter):

    __qualname__ = "uint"

    def __init__(self, include_zero=False):
        self.include_zero = include_zero

    async def convert(self, ctx, arg):
        arg = int(arg)

        if arg <= 0 and not self.include_zero:
            raise commands.BadArgument(ctx.lang["errors"]["arg_over_zero"])

        if arg < 0:
            raise commands.BadArgument(ctx.lang["errors"]["arg_over_or_equal_zero"])

        return ctx.bot.db._make_safe_value(arg)


class Index:

    __slots__ = ("value")
    __qualname__ = "uint"

    def __init__(self, value: int):
        self.value = value

    def humanize(self) -> int:
        return self.value + 1


class IndexConverter(uint):

    __qualname__ = "uint"

    async def convert(self, ctx, arg):
        convertered = await super().convert(ctx, arg) - 1

        return Index(convertered if convertered >= 0 else 0)


class HumanTime(commands.Converter):

    SECONDS_IN_YEAR = 31536000

    async def convert(self, ctx, arg):
        arg = arg.lower()

        seconds_in = ctx.lang["time_map"]
        
        try:
            total_seconds = int(arg[:-1]) * seconds_in[arg[-1]]
            return min(max(1, total_seconds), self.SECONDS_IN_YEAR)
        except:
            raise commands.BadArgument(ctx.lang["errors"]["time_convert_failed"])


class NotAuthor(commands.MemberConverter):

    async def convert(self, ctx, argument):
        member = await super().convert(ctx, argument)

        if member == ctx.author:
            raise commands.BadArgument(ctx.lang["errors"]["cant_use_to_yourself"])

        return member


class EqualMember(NotAuthor):

    async def convert(self, ctx, arg):
        member = await super().convert(ctx, arg)

        if member.top_role >= ctx.guild.me.top_role or ctx.guild.owner == member:
            raise commands.BadArgument(ctx.lang["errors"]["member_over_bot"].format(
                ctx.bot.user.mention, member.mention))

        if ctx.author == ctx.guild.owner:
            return member

        member_perms = ctx.channel.permissions_for(member)
        author_perms = ctx.channel.permissions_for(ctx.author)

        if author_perms <= member_perms and not ctx.bot.is_owner(ctx.author):
            raise commands.BadArgument(
                ctx.lang["errors"]["member_has_eq_over_perms"].format(member.mention))

        return member


class EqualRole(commands.RoleConverter):

    async def convert(self, ctx, arg):
        role = await super().convert(ctx, arg)

        if role.managed:
            raise commands.BadArgument(ctx.lang["errors"]["managed_role"].format(
                role.mention))

        if (role >= ctx.author.top_role and not ctx.bot.is_owner(ctx.author)) or \
            role >= ctx.guild.me.top_role:
                raise commands.BadArgument(
                    ctx.lang["errors"]["role_over_top_role"].format(
                        role.mention, ctx.bot.user.mention))

        return role
