import discord

from discord.ext import commands
from typing import Optional
from .utils.strings import markdown, join_or_default, collect_attributes
from .utils.constants import StringConstants, RanksConstants
from .utils.checks import is_commander, bot_has_permissions
from .utils.converters import EqualRole


class Ranks(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True, name="rank", aliases=["ranks"])
    @bot_has_permissions(manage_roles=True)
    async def rank(self, ctx, *, role: Optional[EqualRole]):
        check = await self.bot.db.execute(
            "SELECT `role` FROM `ranks` WHERE `ranks`.`server` = ? LIMIT ?",
            ctx.guild.id, RanksConstants.ROLES_MAX_COUNT, fetch_all=True)

        if check is None or not len(check):
            return await ctx.answer(ctx.lang["ranks"]["no_ranks"])

        ranks_roles = [ctx.guild.get_role(c[0]) for c in check]

        if role is not None:
            if role not in ranks_roles:
                return await ctx.answer(
                    ctx.lang["ranks"]["role_is_not_rank"].format(role.mention))

            if role in ctx.author.roles:
                await ctx.author.remove_roles(role, reason=ctx.lang["ranks"]["title"])
                await ctx.answer(ctx.lang["ranks"]["removed"].format(role.mention))
            else:
                await ctx.author.add_roles(role, reason=ctx.lang["ranks"]["title"])
                await ctx.answer(ctx.lang["ranks"]["added"].format(role.mention))
        else:
            answer = '\n'.join(
                f"{markdown(role.name, '**')} {StringConstants.DOT_SYMBOL} {len(role.members)}"
                for role in ranks_roles 
                if len(role.name) <= RanksConstants.ROLE_NAME_MAX_LEN)

            em = discord.Embed(
                description=answer,
                colour=ctx.color,
                title=ctx.lang["ranks"]["title"])

            await ctx.send(embed=em)

    @rank.command(name="toggle")
    @is_commander()
    @bot_has_permissions(manage_roles=True)
    async def rank_toggle(self, ctx, roles: commands.Greedy[discord.Role]):
        roles = tuple(role for role in roles if role < ctx.guild.me.top_role)

        if len(roles) == 0:
            return await ctx.answer(ctx.lang["errors"]["no_roles"])
        
        check = await self.bot.db.execute(
            "SELECT `role` FROM `ranks` WHERE `ranks`.`server` = ?",
            ctx.guild.id, fetch_all=True)

        ranks_roles = tuple(ctx.guild.get_role(c[0]) for c in check)
        ranks_roles = tuple(role for role in ranks_roles if role is not None)

        deleted = {role for role in roles if role in ranks_roles}
        max_to_add = RanksConstants.ROLES_MAX_COUNT - len(ranks_roles) + len(deleted)
        added = tuple(set(roles) ^ deleted)[:max_to_add]

        delete_sql = """
        DELETE 
        FROM `ranks`
        WHERE `ranks`.`server` = ? AND `ranks`.`role` IN ({})
        """

        if len(deleted):
            await self.bot.db.execute(
                delete_sql.format(', '.join(map(lambda r: str(r.id), deleted))),
                ctx.guild.id, with_commit=True)

        if len(added):
            await self.bot.db.executemany(
                "INSERT INTO `ranks` VALUES (?, ?)",
                ((ctx.guild.id, role.id) for role in added), 
                with_commit=True)

        em = discord.Embed(colour=ctx.color, title=ctx.lang["ranks"]["title"])
        
        em.add_field(
            name=ctx.lang["shared"]["added"], 
            value=join_or_default(
                collect_attributes(added, "mention"), ', ', 
                ctx.lang["shared"]["no"]), 
            inline=False)

        em.add_field(
            name=ctx.lang["shared"]["deleted"],
            value=join_or_default(
                collect_attributes(deleted, "mention"), ', ', 
                ctx.lang["shared"]["no"]),
            inline=False)

        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Ranks(bot))