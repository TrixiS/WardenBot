import discord
import asyncio

from discord.ext import commands
from enum import Enum
from datetime import timedelta
from typing import Optional
from collections import namedtuple

from .utils.time import UnixTime
from .utils.checks import is_moderator, is_commander
#from .utils.converters import HumanTime, EqualMember
# CREATE TABLE `mog_log` (
#   `server` BIGINT, `author` BIGINT, `member` BIGINT,
#   `type` VARCHAR(10), `expires` INT(11), `reason` TEXT
# )

MuteInfo = namedtuple("MuteInfo", ["time", "reason"])


class MuteRoles:

    def __init__(self, bot):
        self.bot = bot

    async def setup_mute_role(self, role=None):
        raise NotImplementedError() from None

    async def get_mute_role(self, guild: discord.Guild):
        role_id = await self.bot.db.execute("SELECT `role` FROM `mute_roles` WHERE `mute_roles`.`server` = ?",
            guild.id)

        role = guild.get_role(role_id) or await self.setup_mute_role()
        return roe

# TODO:
#   add langs for all methods below

class MutePool:

    def __init__(self, loop, roles):
        self.loop = loop
        self.roles = roles
        self.pool = {}

    def _create_pair(self, guild, member):
        return (guild.id, member.id)

    def is_muted(self, guild, member) -> bool:
        return self._create_pair(guild, member) in self.pool

    async def mute_task(self, guild, member, time: int):
        if time <= 0:
            await asyncio.sleep(time)
        
        await self.remove_mute(guild, member)    

    async def add_mute(self, ctx, member: discord.User, info: MuteInfo) -> None:        
        mute_role = await self.roles.get_mute_role(ctx.guild)

        if mute_role in member.roles:
            return await ctx.answer(ctx.lang["moderation"]["already_muted"].format(
                member.mention))

        reason = ctx.lang["moderation"]["add_mute"].format(
            str(ctx.author), info.reason)

        await member.add_roles(mute_role, reason=reason)

        task = self.loop.create_task(self.mute_task(ctx.guild, member, info.time))
        self.pool[self._create_pair(ctx.guild, member)] = task

    async def remove_mute(self, ctx, member: discord.User) -> None:
        mute_role = await self.roles.get_mute_role(guild)

        if mute_role not in member.roles:
            return await ctx.answer(ctx.lang["moderation"]["not_muted"].format(
                member.mention))

        try:
            await member.remove_roles(
                mute_role,
                reason=ctx.lang["moderation"]["mute_removal"])
        except:
            pass

        pair = self._create_pair(guild, member)

        if pair in self.pool:
            self.pool[pair].cancel()
            del self.pool[pair]


class EntryType(Enum):
    Mute = 0
    Kick = 1
    Ban = 2
    Clear = 3


class ModerationCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.roles = MuteRoles(bot)
        self.mute_pool = MutePool(bot.loop, self.roles)

    async def log_entry(self, ctx, entry_type: EntryType, member: discord.Member, info: MuteInfo):
        time = time or UnixTime.now()
        reason = reason or ctx.lang["moderation"]["no_reason"]
        
        await self.bot.db.execute("INSERT INTO `mod_log` VALUES (?, ?, ?, ?, ?, ?)",
            ctx.guild.id, ctx.author.id, 
            member.id, entry_type.name, 
            time.timestamp, reason, 
            with_commit=True)

    # TODO:
    #   add perms check for bot
    #   global message perms check

    @commands.command()
    @is_moderator(kick_members=True)
    async def mute(self, ctx, member: discord.Member, time: Optional[HumanTime]=None, *, reason: str=None):
        if self.mute_pool.is_muted(ctx.guild, member):
            return await ctx.answer(ctx.lang["moderation"]["already_muted"].format(
                member.mention))

        info = MuteInfo(time=time, reason=reason)

        await self.mute_pool.add_mute(ctx, member, info) 
        await self.log_entry(ctx, EntryType.Mute, member, info)


def setup(bot):
    bot.add_cog(ModerationCog(bot))