import discord

from discord.ext import commands
from .utils.checks import is_commander
from .utils.strings import join_or_default, collect_attributes

from typing import Union


class RoleManager(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def get_ignored(self, guild):
        ignored_roles = []
        ignored_users = []

        check = await self.bot.db.execute("SELECT `model`, `is_role` FROM `rm_ignore` WHERE `rm_ignore`.`server` = ?",
            guild.id, fetch_all=True)

        if check is not None:
            for row in check:
                model_id, is_role = row

                if is_role:
                    role = guild.get_role(model_id)

                    if role is not None:
                        ignored_roles.append(role)
                else:
                    user = self.bot.get_user(model_id)

                    if user is not None:
                        ignored_users.append(user)

        return ignored_roles, ignored_users

    @commands.group(name="rm", invoke_without_command=True)
    @is_commander(manage_roles=True)
    async def role_manager(self, ctx):
        enabled = await self.bot.db.execute("SELECT `enabled` FROM `rm_enabled` WHERE `rm_enabled`.`server` = ?",
            ctx.guild.id)

        if enabled is None:
            enabled = False

        roles, users = await self.get_ignored(ctx.guild)

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
        toggled = await self.bot.db.execute("UPDATE `rm_enabled` SET `enabled` = NOT `enabled` WHERE `rm_enabled`.`server` = ?",
            ctx.guild.id, with_commit=True)

        if toggled:
            await ctx.answer(ctx.lang["rm"]["toggled"])
        else:
            await self.bot.db.execute("INSERT INTO `rm_enabled` VALUES (?, ?)",
                ctx.guild.id, True, with_commit=True)
            
            await ctx.answer(ctx.lang["rm"]["now_enabled"])

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

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not member.guild.me.guild_permissions.manage_roles:
            return

        enabled = await self.bot.db.execute("SELECT `enabled` FROM `rm_enabled` WHERE `rm_enabled`.`server` = ?",
            member.guild.id)

        if not enabled:
            return

        ignored_roles, ignored_users = await self.get_ignored(member.guild)

        if member in ignored_users:
            return

        check = await self.bot.db.execute("SELECT `role` FROM `rm_buffer` WHERE `rm_buffer`.`server` = ? AND `rm_buffer`.`member` = ?",
            member.guild.id, member.id, fetch_all=True)

        if check is None or not len(check):
            return

        roles_to_return = []

        for row in check:
            role = member.guild.get_role(row[0])

            if role is not None and member.guild.me.top_role > role \
                and role.id != member.guild.id and role not in ignored_roles \
                and role not in member.roles:
                    roles_to_return.append(role)

        await self.bot.db.execute("DELETE FROM `rm_buffer` WHERE `rm_buffer`.`server` = ? AND `rm_buffer`.`member` = ?",
            member.guild.id, member.id, with_commit=True)

        if len(roles_to_return):
            await member.add_roles(*roles_to_return, reason="Role manager")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if not member.guild.me.guild_permissions.manage_roles:
            return
        
        enabled = await self.bot.db.execute("SELECT `enabled` FROM `rm_enabled` WHERE `rm_enabled`.`server` = ?",
            member.guild.id)

        if not enabled:
            return

        query_args = tuple(
            (member.guild.id, member.id, role.id) for role in member.roles
            if role < member.guild.me.top_role)

        if len(query_args):
            await self.bot.db.executemany("INSERT INTO `rm_buffer` VALUES (?, ?, ?)",
                query_args, with_commit=True)


def setup(bot):
    bot.add_cog(RoleManagerCog(bot))