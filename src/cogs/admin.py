import discord

from .utils.checks import is_commander
from .utils.converters import Check
from discord.ext import commands
from typing import Optional


class Administration(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def delete_pattern(self, ctx, table: str, deleted: str, no: str):
        check = await self.bot.db.execute(f"DELETE FROM `{table}` WHERE `{table}`.`server` = ?",
            ctx.guild.id, with_commit=True)

        if check:
            await ctx.answer(ctx.lang["admin"][deleted])
        else:
            await ctx.answer(ctx.lang["admin"][no])

    @commands.group(invoke_without_command=True)
    @is_commander()
    async def welcome(self, ctx, *, content: str=None):
        if content is not None:
            check = await self.bot.db.execute("UPDATE `welcome` SET `content` = ? WHERE `welcome`.`server` = ?",
                content, ctx.guild.id, with_commit=True)

            if not check:
                await self.bot.db.execute("INSERT INTO `welcome` VALUES (?, ?)",
                    ctx.guild.id, content, with_commit=True)

            return await ctx.answer(ctx.lang["admin"]["welcome_changed"])

        check = await self.bot.db.execute("SELECT `content` FROM `welcome` WHERE `welcome`.`server` = ?",
            ctx.guild.id)

        if check is not None:
            await ctx.answer(check)
        else:
            await ctx.answer(ctx.lang["admin"]["no_welcome"])

    @welcome.command(name="delete")
    @is_commander()
    async def welcome_delete(self, ctx):
        await self.delete_pattern(ctx, "welcome", 
            "welcome_deleted", "no_welcome")

    @commands.group(invoke_without_command=True)
    @is_commander()
    async def autorole(self, ctx, *, role: Optional[discord.Role]):
        if role is not None:
            if role.id == ctx.guild.id:
                raise commands.BadArgument(ctx.lang["errors"]["no_roles"])

            check = await self.bot.db.execute("UPDATE `autorole` SET `role` = ? WHERE `autorole`.`server` = ?",
                role.id, ctx.guild.id, with_commit=True)
            
            if not check:
                await self.bot.db.execute("INSERT INTO `autorole` VALUES (?, ?)",
                    ctx.guild.id, role.id, with_commit=True)

            return await ctx.answer(
                ctx.lang["admin"]["now_autorole"].format(role.mention))

        check = await self.bot.db.execute("SELECT `role` FROM `autorole` WHERE `autorole`.`server` = ?",
            ctx.guild.id)

        role = ctx.guild.get_role(check)

        if role is not None:
            await ctx.answer(
                ctx.lang["admin"]["is_autorole"].format(role.mention))
        else:
            await ctx.answer(ctx.lang["admin"]["no_autorole"])

    @autorole.command(name="delete")
    @is_commander()
    async def autorole_delete(self, ctx):
        await self.delete_pattern(ctx, "autorole", 
            "autorole_deleted", "no_autorole")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        welcome_content = await self.bot.db.execute("SELECT `content` FROM `welcome` WHERE `welcome`.`server` = ?",
            member.guild.id)

        if welcome_content:
            user = self.bot.get_user(member.id)

            em = discord.Embed(
                description=welcome_content,
                colour=(await self.bot.get_color(member.guild)))
            em.set_thumbnail(url=member.guild.icon_url)

            try:
                await user.send(embed=em)
            except:
                pass

        if not member.guild.me.guild_permissions.manage_roles:
            return

        autorole_id = await self.bot.db.execute("SELECT `role` FROM `autorole` WHERE `autorole`.`server` = ?",
            member.guild.id)

        if autorole_id:
            role = member.guild.get_role(autorole_id)

            if member.guild.me.top_role < role:
                return

            try:
                await member.add_roles(
                    role,
                    reason=(await self.bot.get_lang(member.guild))["events"]["autorole"])
            except:
                pass


def setup(bot):
    bot.add_cog(Administration(bot))