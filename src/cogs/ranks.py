import discord

from discord.ext import commands
from .utils.strings import markdown
from .utils.constants import StringConstants, RanksConstants

class RankCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True, name="rank", aliases=["ranks"])
    async def rank(self, ctx, *, role: discord.Role=None):
        check = await self.bot.db.execute("SELECT `role` FROM `ranks` WHERE `ranks`.`server` = ?",
            ctx.guild.id, fetch_all=True)

        if not len(check):
            return await ctx.send(ctx.lang["ranks"]["no_ranks"])

        ranks_roles = [ctx.guild.get_role(c[0]) for c in check]

        del check

        if role is not None:
            if role not in ranks_roles:
                return await ctx.answer(
                    ctx.lang["ranks"]["role_is_not_rank"].format(role.mention)
                )

            if role in ctx.autor.roles:
                ctx.author.remove_roles(role)
                await ctx.answer(ctx.lang["ranks"]["removed"].format(role.mention))
            else:
                ctx.author.add_roles(role)
                await ctx.answer(ctx.lang["ranks"]["added"].format(role.mention))
        else:
            answer = '\n'.join(
                f"{markdown(role.name, '**')} {StringConstants.DOT_SYMBOL} {len(role.members)}"
                for role in ranks_roles if len(role.name) <= RanksConstants.ROLE_NAME_MAX_LEN 
            )

            em = discord.Embed(
                description=answer,
                colour=ctx.color,
                title=ctx.lang["ranks"]["title"]    
            )

            await ctx.send(embed=em)

    @rank.command(name="toggle")
    async def rank_toggle(self, ctx, roles: commands.Greedy[discord.Role]):
        roles = {role for role in roles if role < ctx.guild.me.top_role}

        if not len(roles):
            raise commands.BadArgument(ctx.lang["errors"]["no_roles"])
        
        check = await self.bot.db.execute("SELECT `role` FROM `ranks` WHERE `ranks`.`server` = ?",
            ctx.guild.id, fetch_all=True)

        ranks_roles = tuple(ctx.guild.get_role(c[0]) for c in check)

        del check

        deleted = []
        added = []

        for role in roles:
            if role in ranks_roles:
                await self.bot.db.execute("DELETE FROM `ranks` WHERE `ranks`.`server` = ? AND `ranks`.`role` = ?",
                    ctx.guild.id, role.id, with_commit=True)
                
                deleted.append(role)
            else:
                await self.bot.db.execute("INSERT INTO `ranks` VALUES (?, ?)",
                    ctx.guild.id, role.id, with_commit=True)

                added.append(role)

        def build_field(ranks: list) -> str:
            result = ', '.join(
                role.mention for role in ranks 
                if role is not None
            )

            return result or ctx.lang["shared"]["no"]

        em = discord.Embed(colour=ctx.color, title=ctx.lang["ranks"]["title"])
        em.add_field(
            name=ctx.lang["shared"]["added"], 
            value=build_field(added), 
            inline=False
        )
        em.add_field(
            name=ctx.lang["shared"]["deleted"],
            value=build_field(deleted),
            inline=False
        )

        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(RankCog(bot))