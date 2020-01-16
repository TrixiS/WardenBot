import discord
import asyncio

from discord.ext import commands
from enum import Enum
from datetime import timedelta
from typing import Optional
from collections import namedtuple

from .utils.time import UnixTime
from .utils.checks import is_moderator, is_commander, bot_has_permissions
from .utils.converters import HumanTime, EqualMember, EqualRole

MuteInfo = namedtuple("MuteInfo", ["time", "reason"])


class MuteRoles:
    
    overwrite = discord.PermissionOverwrite()
    overwrite.send_messages = False
    overwrite.embed_links = False
    overwrite.attach_files = False
    overwrite.create_instant_invite = False
    overwrite.manage_messages = False
    overwrite.send_tts_messages = False
    overwrite.mention_everyone = False
    overwrite.speak = False
    overwrite.use_voice_activation = False
    
    def __init__(self, bot):
        self.bot = bot

    async def setup_mute_role(self, *, guild=None, role=None):
        if role is None:
            role = discord.utils.get(guild.roles, name="Muted") or \
                await guild.create_role(name="Muted")

        for channel in role.guild.channels:
            await channel.set_permissions(role, overwrite=self.overwrite)

        check = await self.bot.db.execute("UPDATE `mute_roles` SET `role` = ? WHERE `mute_roles`.`server` = ?",
            role.id, role.guild.id, with_commit=True)

        if not check:
            await self.bot.db.execute("INSERT INTO `mute_roles` VALUES (?, ?)",
                role.guild.id, role.id, with_commit=True)

        return role

    async def get_mute_role(self, guild: discord.Guild):
        role_id = await self.bot.db.execute("SELECT `role` FROM `mute_roles` WHERE `mute_roles`.`server` = ?",
            guild.id)

        role = guild.get_role(role_id) or await self.setup_mute_role(guild=guild)
        
        return role


class MemberDict(dict):

    def __getitem__(self, member: discord.Member):
        return super().__getitem__((member.guild.id, member.id))

    def __setitem__(self, member: discord.Member, value):
        super().__setitem__((member.guild.id, member.id), value)

    def __contains__(self, member: discord.Member):
        return super().__contains__((member.guild.id, member.id))

    def __delitem__(self, member: discord.Member):
        super().__delitem__((member.guild.id, member.id))


class MutePool:

    def __init__(self, loop, roles):
        self.loop = loop
        self.roles = roles
        self.pool = MemberDict()

    def __contains__(self, member) -> bool:
        return member in self.pool

    def create_task(self, *args, **kwargs):
        return self.loop.create_task(self.mute_task(*args, **kwargs))

    async def mute_task(self, member, time: int):
        await asyncio.sleep(time)
        await self.remove_mute(member, MuteInfo(time=None, reason="Unmute"), 
            auto=True)

    async def add_mute(self, member: discord.Member, info: MuteInfo):        
        mute_role = await self.roles.get_mute_role(member.guild)

        if mute_role not in member.roles:
            await member.add_roles(mute_role, reason=info.reason)

        time = info.time.passed_seconds()

        if time > 0:
            self.pool[member] = self.create_task(member, time)

    async def remove_mute(self, member: discord.Member, info: MuteInfo, *, auto=False):
        mute_role = await self.roles.get_mute_role(member.guild)

        if mute_role in member.roles:
            await member.remove_roles(mute_role, reason=info.reason)

        if member in self.pool:
            if not auto:
                self.pool[member].cancel()
            
            del self.pool[member]


class EntryType(Enum):
    Mute = 0
    Unmute = 1
    Kick = 2
    Ban = 3
    Clear = 4

class ModerationCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.roles = MuteRoles(bot)
        self.mute_pool = MutePool(bot.loop, self.roles)

    async def log_entry(self, ctx, entry_type: EntryType, member: discord.Member, info: MuteInfo):
        check = await self.bot.db.execute("SELECT MAX(`id`) FROM `cases` WHERE `cases`.`server` = ?",
            ctx.guild.id)

        await self.bot.db.execute("INSERT INTO `cases` VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (check or 0) + 1, ctx.guild.id,
            ctx.author.id, member.id, 
            entry_type.name, int(info.time.timestamp),
            info.reason, False, with_commit=True)

        if entry_type == EntryType.Unmute:
            await self.bot.db.execute("UPDATE `cases` SET `removed` = ? WHERE `cases`.`id` = ?",
                True, check, with_commit=True)

    @commands.command()
    @bot_has_permissions(manage_roles=True)
    @is_moderator(manage_roles=True)
    async def mute(self, ctx, member: EqualMember, time: Optional[HumanTime]=0, *, reason: str=None):
        if member in self.mute_pool:
            return await ctx.answer(ctx.lang["moderation"]["already_muted"].format(
                member.mention))
        
        info = MuteInfo(
            time=UnixTime.now() + timedelta(seconds=time), 
            reason=reason or ctx.lang["shared"]["no"])

        await self.mute_pool.add_mute(member, info) 

        await ctx.answer(ctx.lang["moderation"]["muted"].format(
            member.mention))

        await self.log_entry(ctx, EntryType.Mute, member, info)

    @commands.command()
    @bot_has_permissions(manage_roles=True)
    @is_moderator(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member, *, reason: str=None):
        if member not in self.mute_pool:
            return await ctx.answer(ctx.lang["moderation"]["not_muted"].format(
                member.mention))

        info = MuteInfo(
            time=UnixTime.now(),
            reason=reason or ctx.lang["shared"]["no"])

        await self.mute_pool.remove_mute(member, info)

        await ctx.answer(ctx.lang["moderation"]["unmuted"].format(
            member.mention))
        
        await self.log_entry(ctx, EntryType.Unmute, member, info)

    @commands.group(name="mute-role", invoke_without_command=True)
    @bot_has_permissions(manage_roles=True, manage_channels=True)
    @is_commander(manage_roles=True)
    async def mute_role(self, ctx, role: EqualRole=None):
        if role is None:
            return await ctx.answer(ctx.lang["moderation"]["mute_role_now"].format(
                (await self.roles.get_mute_role(guild=ctx.guild)).mention))

        await self.roles.setup_mute_role(role=role)

        await ctx.answer(ctx.lang["moderation"]["new_mute_role"].format(
            role.mention))

    @mute_role.command(name="delete")
    @bot_has_permissions(manage_roles=True)
    @is_commander(manage_roles=True)
    async def mute_role_delete(self, ctx):
        check = await self.bot.db.execute("DELETE FROM `mute_roles` WHERE `mute_roles`.`server` = ?",
            ctx.guild.id, with_commit=True)

        if check:
            await ctx.answer(ctx.lang["moderation"]["mute_role_delete"])
        else:
            await ctx.answer(ctx.lang["moderation"]["no_mute_role"])

    @commands.Cog.listener()
    async def on_ready(self):
        check = await self.bot.db.execute("SELECT `server`, `member`, `expires` FROM `cases` WHERE `cases`.`type` = ? AND `cases`.`expires` > UNIX_TIMESTAMP() AND `cases`.`removed` = ?",
            EntryType.Mute.name, False, fetch_all=True)

        if check is None or len(check) == 0:
            return

        for row in check:
            guild_id, member_id, expires = row

            member = self.bot.get_member(guild_id, member_id)

            if member is None:
                continue

            time = UnixTime(expires).passed_seconds()
            
            self.mute_pool.pool[member] = self.mute_pool.create_task(member, time)


def setup(bot):
    bot.add_cog(ModerationCog(bot))
