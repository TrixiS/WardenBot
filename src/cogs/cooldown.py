import discord

from discord.ext import commands
from typing import Union, Optional

from .utils.converters import HumanTime, SafeUint, CommandConverter
from .utils.cooldown import CooldownCommand
from .utils.checks import is_commander


class Cooldown(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    @is_commander()
    async def cooldown(self, ctx, max_uses: SafeUint, interval: HumanTime, *, command: CommandConverter(CooldownCommand)):
        sql = """
        UPDATE `cooldown`
        SET `max_uses` = ?, `reset_seconds` = ?
        WHERE `cooldown`.`server` = ? AND `cooldown`.`command` = ?
        """
        
        check = await self.bot.db.execute(sql,
            max_uses, interval, 
            ctx.guild.id, command.qualified_name,
            with_commit=True)

        if not check:
            await self.bot.db.execute("INSERT INTO `cooldown` VALUES (?, ?, ?, ?)",
                ctx.guild.id, command.qualified_name, max_uses, interval, with_commit=True)

        await ctx.answer(ctx.lang["economy"]["cooldown_updated"].format(
            command.qualified_name))

        for bucket in command.custom_cooldown_buckets:
            if bucket.guild == ctx.guild:
                bucket.update(new_reset_seconds=interval, new_max_uses=max_uses)

    @cooldown.command(name="for", aliases=["check"])
    async def cooldown_for(self, ctx, *, command: CommandConverter(CooldownCommand)):
        sql = """
        SELECT `max_uses`, `reset_seconds`
        FROM `cooldown`
        WHERE `cooldown`.`server` = ? AND `cooldown`.`command` = ?
        """

        cooldown_info = await self.bot.db.execute(sql,
            ctx.guild.id, command.qualified_name) or self.bot.config.default_cooldown

        em = discord.Embed(
            title=ctx.lang["economy"]["cooldown_for"].format(command.qualified_name),
            colour=ctx.color)

        em.set_thumbnail(url=ctx.guild.icon_url)

        em.add_field(
            name=ctx.lang["economy"]["max_uses"],
            value=cooldown_info[0],
            inline=False)

        em.add_field(
            name=ctx.lang["economy"]["interval"],
            value=f"{cooldown_info[1]} {ctx.lang['shared']['seconds']}",
            inline=False)

        await ctx.send(embed=em)

    @cooldown.command(name="reset")
    @is_commander()
    async def cooldown_reset(self, ctx, role_or_member: Optional[Union[discord.Role, discord.Member]], *, command: CommandConverter(CooldownCommand)):
        buckets = filter(
            lambda b: b.guild == ctx.guild, 
            command.custom_cooldown_buckets)

        if role_or_member is not None:
            if isinstance(role_or_member, discord.Role):
                buckets = filter(lambda b: role_or_member in b.user.roles, buckets)
            else:
                buckets = filter(lambda b: b.user == role_or_member, buckets)

        for bucket in buckets:
            bucket.update()

        await ctx.answer(ctx.lang["economy"]["cooldown_reset"].format(
            command.qualified_name, 
            (role_or_member and role_or_member.mention) or ctx.lang["shared"]["all_members"]))


def setup(bot):
    bot.add_cog(Cooldown(bot))