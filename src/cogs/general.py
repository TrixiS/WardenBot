import discord

from discord.ext.commands import Cog, command, has_permissions, group
from .utils.checks import is_commander


class GeneralCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    @command(name="language", aliases=["lang"])
    @is_commander()
    async def language(self, ctx, lang_code: str.lower=None):
        supported_langs = self.bot.langs.keys()

        if lang_code is None or not lang_code in supported_langs:
            answer = ctx.lang["general"]["supported_langs"].format(
                ', '.join(f"**{l}**" for l in supported_langs)
            )

            return await ctx.answer(answer)

        check = await self.bot.db.execute("SELECT `lang` FROM `langs` WHERE `langs`.`server` = ?", 
            ctx.guild.id)

        if check is not None:
            await self.bot.db.execute("UPDATE `langs` SET `lang` = ? WHERE `langs`.`server` = ?", 
                lang_code, ctx.guild.id, with_commit=True)
        else:
            await self.bot.db.execute("INSERT INTO `langs` (`server`, `lang`) VALUES (?, ?)", 
                ctx.guild.id, lang_code, with_commit=True)

        await ctx.answer(ctx.lang["general"]["now_speaks"].format(lang_code))

    @command(name="embed-color")
    @is_commander()
    async def embed_color(self, ctx, *, hex: discord.Colour):
        rgb_str = ';'.join(map(str, hex.to_rgb()))

        check = await self.bot.db.execute("SELECT `color` FROM `colors` WHERE `colors`.`server` = ?",
            ctx.guild.id)

        if check is None:
            await self.bot.db.execute("INSERT INTO `colors` (`server`, `color`) VALUES (?, ?)", 
                ctx.guild.id, rgb_str, with_commit=True)
        else:
            await self.bot.db.execute("UPDATE `colors` SET `color` = ? WHERE `server` = ?",
                rgb_str, ctx.guild.id, with_commit=True)

        await ctx.answer(ctx.lang["general"]["embed_color_changed"].format(rgb_str))

    async def _role_setup_pattern(self, ctx, role: discord.Role, table: str, no_key: str, is_key: str, new_key: str):
        check = await self.bot.db.execute(f"SELECT `role` FROM `{table}` WHERE `{table}`.`server` = ?",
            ctx.guild.id)

        if role is None:
            checked_role = ctx.guild.get_role(check)

            if check is None or checked_role is None:
                await ctx.answer(ctx.lang["general"][no_key])
            else:
                await ctx.answer(ctx.lang["general"][is_key].format(checked_role.mention))            
        else:
            if check is None:
                await self.bot.db.execute(f"INSERT INTO `{table}` (`server`, `role`) VALUES (?, ?)",
                    ctx.guild.id, role.id, with_commit=True)
            else:
                await self.bot.db.execute(f"UPDATE `{table}` SET `role` = ? WHERE `server` = ?",
                    role.id, ctx.guild.id, with_commit=True)

            await ctx.answer(ctx.lang["general"][new_key].format(role.mention))

    async def _role_delete_pattern(self, ctx, table: str, deleted_key: str):
        await self.bot.db.execute(f"DELETE FROM `{table}` WHERE `{table}`.`server` = ?",
            ctx.guild.id, with_commit=True)

        await ctx.answer(ctx.lang["general"][deleted_key])

    @group(invoke_without_command=True)
    @has_permissions(administrator=True)
    async def commander(self, ctx, role: discord.Role=None):
        await self._role_setup_pattern(ctx, role, "commanders", 
            "no_commander", "is_commander", "new_commander")

    @commander.command(name="delete")
    @has_permissions(administrator=True)
    async def commander_delete(self, ctx):
        await self._role_delete_pattern(ctx, "commanders", "deleted_commander")

    @group(invoke_without_command=True)
    @has_permissions(administrator=True)
    async def moderator(self, ctx, role: discord.Role=None):
        await self._role_setup_pattern(ctx, role, "moderators", 
            "no_moderator", "is_moderator", "new_moderator")

    @moderator.command(name="delete")
    @has_permissions(administrator=True)
    async def moderator_delete(self, ctx):
        await self._role_delete_pattern(ctx, "moderators", "deleted_moderator")

def setup(bot):
    bot.add_cog(GeneralCog(bot))