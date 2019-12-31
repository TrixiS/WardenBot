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


def setup(bot):
    bot.add_cog(RankCog(bot))