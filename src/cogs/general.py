import discord

from discord.ext.commands import Cog, command, has_permissions, group
from .utils.checks import is_commander
from .utils.strings import markdown


class General(Cog):

    def __init__(self, bot):
        self.bot = bot

    async def _settings_pattern(self, ctx, table: str, field: str, new_value: str, message: str):
        check = await self.bot.db.execute(f"UPDATE `{table}` SET `{field}` = ? WHERE `{table}`.`server` = ?",
            new_value, ctx.guild.id, with_commit=True)

        if not check:
            await self.bot.db.execute(f"INSERT INTO `{table}` VALUES (?, ?)",
                ctx.guild.id, new_value, with_commit=True)

        await ctx.answer(message)

    @command(name="lang")
    @is_commander()
    async def lang(self, ctx, lang_code: str.lower=None):
        supperted_langs = self.bot.langs.keys()

        if lang_code is None or lang_code not in supperted_langs:
            answer = ctx.lang["general"]["supported_langs"].format(
                ', '.join(markdown(l, "**") for l in supperted_langs))

            return await ctx.answer(answer)

        ctx.lang = self.bot.langs[lang_code]

        await self._settings_pattern(ctx, "langs", "lang", lang_code, 
            ctx.lang["general"]["now_speaks"].format(self.bot.user.name, lang_code))

    @command(name="embed-color")
    @is_commander()
    async def embed_color(self, ctx, *, new_color: discord.Colour=None):
        if new_color is None:
            return await ctx.answer(str(ctx.color).upper())

        rgb_str = ';'.join(map(str, new_color.to_rgb()))

        ctx.color = new_color

        await self._settings_pattern(ctx, "colors", "color", rgb_str, 
            ctx.lang["general"]["embed_color_changed"].format(rgb_str))

    async def _role_setup_pattern(self, ctx, role: discord.Role, table: str, no_key: str, is_key: str, new_key: str):
        if role is None:
            check = await self.bot.db.execute(f"SELECT `role` FROM `{table}` WHERE `{table}`.`server` = ?",
                ctx.guild.id)

            checked_role = ctx.guild.get_role(check)

            if check is None or checked_role is None:
                await ctx.answer(ctx.lang["general"][no_key])
            else:
                await ctx.answer(ctx.lang["general"][is_key].format(checked_role.mention))        
        else:
            await self._settings_pattern(ctx, table, "role", role.id, 
                ctx.lang["general"][new_key].format(role.mention))

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