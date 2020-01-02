import discord

from discord.ext import commands
from .utils.checks import is_commander
from .utils.strings import join_or_default, collect_attributes

from typing import Union


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
    @is_commander(manage_roles=True)
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
            colour=ctx.color)
        em.add_field(
            name=ctx.lang["rm"]["ignored_roles"],
            value=join_or_default(
                collect_attributes(roles, "mention"), ', ', 
                ctx.lang["shared"]["no"]),
            inline=False)
        em.add_field(
            name=ctx.lang["rm"]["ignored_users"],
            value=join_or_default(
                collect_attributes(users, "mention"), ', ', 
                ctx.lang["shared"]["no"]),
            inline=False)

        await ctx.send(embed=em)

    @role_manager.command(name="toggle")
    @is_commander(manage_roles=True)
    async def role_manager_toggle(self, ctx):
        enabled = await self.bot.db.execute("SELECT `enabled` FROM `rm_enabled` WHERE `rm_enabled`.`server` = ?",
            ctx.guild.id)

        if enabled is None:
            await self.bot.db.execute("INSERT INTO `rm_enabled` VALUES (?, ?)",
                ctx.guild.id, True, with_commit=True)

            return await ctx.answer(ctx.lang["rm"]["now_enabled"])

        enabled = not enabled

        await self.bot.db.execute("UPDATE `rm_enabled` SET `enabled` = ? WHERE `rm_enabled`.`server` = ?",
            enabled, ctx.guild.id, with_commit=True)
        
        if enabled:
            await ctx.answer(ctx.lang["rm"]["now_enabled"])
        else:
            await ctx.answer(ctx.lang["rm"]["now_disabled"])

    @role_manager.command(name="ignore")
    @is_commander(manage_roles=True)
    async def role_manager_ignore(self, ctx, role_or_user: Union[discord.Role, discord.User]):
        check = await self.bot.db.execute("DELETE FROM `rm_ignore` WHERE `rm_ignore`.`server` = ? AND `rm_ignore`.`model` = ?",
            ctx.guild.id, role_or_user.id, with_commit=True)

        if not check:
            await self.bot.db.execute("INSERT INTO `rm_ignore` VALUES (?, ?, ?)",   
                ctx.guild.id, 
                role_or_user.id, 
                isinstance(role_or_user, discord.Role),
                with_commit=True)

            return await ctx.answer(
                ctx.lang["rm"]["now_ignored"].format(role_or_user.mention))
        
        await ctx.answer(ctx.lang["rm"]["now_not_ignored"].format(
            role_or_user.mention))


def setup(bot):
    bot.add_cog(RoleManagerCog(bot))