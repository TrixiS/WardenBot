import discord

from discord.ext import commands
from .utils.checks import is_commander
from .utils.strings import join_or_default, collect_attributes


class RoleManagerCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def get_ignored(self, ctx):
        ignored_roles = set()
        ignored_users = set()

        check = await self.bot.db.execute("SELECT `model`, `is_role` FROM `rm_ignore` WHERE `rm_ignore`.`server` = ?",
            ctx.guild.id, fetch_all=True)

        if check is not None:
            for row in check:
                model_id, is_role = row

                if is_role:
                    role = ctx.guild.get_role(model_id)

                    if role is not None:
                        ignored_roles.add(role)
                else:
                    user = self.bot.get_user(model_id)

                    if user is not None:
                        ignored_users.add(user)

        return ignored_roles, ignored_users

    @commands.group(name="rm", invoke_without_command=True)
    @is_commander()
    async def role_manager(self, ctx):
        enabled = await self.bot.db.execute("SELECT `enabled` FROM `rm_enabled` WHERE `rm_enabled`.`server` = ?",
            ctx.guild.id)

        if enabled is None:
            enabled = False

        roles, users = await self.get_ignored(ctx)

        em = discord.Embed(
            title=ctx.lang["rm"]["title"],
            description=ctx.lang["shared"]["enabled"] if
                enabled else ctx.lang["shared"]["disabled"],
            colour=ctx.color
        )
        em.add_field(
            name=ctx.lang["rm"]["ignored_roles"],
            value=join_or_default(
                collect_attributes(roles, "mention"), ', ', 
                ctx.lang["shared"]["no"]
            ),
            inline=False
        )
        em.add_field(
            name=ctx.lang["rm"]["ignored_users"],
            value=join_or_default(
                collect_attributes(users, "mention"), ', ', 
                ctx.lang["shared"]["no"]
            ),
            inline=False
        )

        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(RoleManagerCog(bot))