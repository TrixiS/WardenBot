import discord

from discord.ext import commands
from typing import Optional, Union

from .utils.checks import is_commander
from .utils.strings import markdown
from .utils.converters import CommandConverter, ModuleConverter
from .utils.disable import set_disabled, set_disable_state


class General(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.required_commands = (self.bot.get_command(c)
            for c in self.bot.config.required_commands)

    async def _settings_pattern(self, ctx, table: str, field: str, new_value: str, message: str):
        check = await self.bot.db.execute(f"UPDATE `{table}` SET `{field}` = ? WHERE `{table}`.`server` = ?",
            new_value, ctx.guild.id, with_commit=True)

        if not check:
            await self.bot.db.execute(f"INSERT INTO `{table}` VALUES (?, ?)",
                ctx.guild.id, new_value, with_commit=True)

        await ctx.answer(message)

    @commands.command(name="lang")
    @is_commander()
    async def lang(self, ctx, lang_code: Optional[str.lower]):
        supperted_langs = self.bot.langs.keys()

        if lang_code is None or lang_code not in supperted_langs:
            answer = ctx.lang["general"]["supported_langs"].format(
                ', '.join(markdown(l, "**") for l in supperted_langs))

            return await ctx.answer(answer)

        ctx.lang = self.bot.langs[lang_code]

        await self._settings_pattern(ctx, "langs", "lang", lang_code, 
            ctx.lang["general"]["now_speaks"].format(self.bot.user.name, lang_code))

    @commands.group(invoke_without_command=True, name="embed-color")
    @is_commander()
    async def embed_color(self, ctx, *, new_color: Optional[discord.Colour]):
        if new_color is None:
            hex_command = self.bot.get_command("hex")
            return await hex_command.callback(hex_command.cog, ctx, ctx.color)

        rgb_str = ';'.join(map(str, new_color.to_rgb()))

        ctx.color = new_color

        await self._settings_pattern(ctx, "colors", "color", rgb_str, 
            ctx.lang["general"]["embed_color_changed"].format(rgb_str))

    @embed_color.command(name="default")
    @is_commander()
    async def embed_color_default(self, ctx):
        await ctx.answer(ctx.lang["general"]["color_set_to_default"])
        await self.bot.db.execute(
            "DELETE FROM `colors` WHERE `colors`.`server` = ?",
            ctx.guild.id, with_commit=True)

    @embed_color.command(name="random")
    @is_commander()
    async def embed_color_random(self, ctx):
        await ctx.answer(ctx.lang["general"]["color_set_to_random"])
        check = await self.bot.db.execute(
            "UPDATE `colors` SET `color` = ? WHERE `colors`.`server` = ?",
            "rnd", ctx.guild.id, with_commit=True)

        if not check:
            await self.bot.db.execute(
                "INSERT INTO `colors` VALUES (?, ?)", 
                ctx.guild.id, "rnd", with_commit=True)

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

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def commander(self, ctx, role: Optional[discord.Role]):
        await self._role_setup_pattern(ctx, role, "commanders", 
            "no_commander", "is_commander", "new_commander")

    @commander.command(name="delete")
    @commands.has_permissions(administrator=True)
    async def commander_delete(self, ctx):
        await self._role_delete_pattern(ctx, "commanders", "deleted_commander")

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def moderator(self, ctx, role: Optional[discord.Role]):
        await self._role_setup_pattern(ctx, role, "moderators", 
            "no_moderator", "is_moderator", "new_moderator")

    @moderator.command(name="delete")
    @commands.has_permissions(administrator=True)
    async def moderator_delete(self, ctx):
        await self._role_delete_pattern(ctx, "moderators", "deleted_moderator")

    @commands.command()
    @commands.cooldown(1, 15, commands.BucketType.guild)
    @is_commander()
    async def disable(self, ctx, *, cmd_or_cog: Union[CommandConverter, ModuleConverter]):
        if (isinstance(cmd_or_cog, commands.Command) and
                cmd_or_cog in self.required_commands):
            return await ctx.answer(ctx.lang["general"]["need_opt_command"].format(
                cmd_or_cog.qualified_name))

        if (isinstance(cmd_or_cog, commands.Cog) and
                any(c in self.required_commands
                for c in cmd_or_cog.walk_commands())):
            return await ctx.answer(ctx.lang["general"]["need_opt_cog"].format(
                cmd_or_cog.qualified_name))

        set_disabled(cmd_or_cog)

        if (ctx.guild.id in cmd_or_cog.disabled_in and
                cmd_or_cog.disabled_in[ctx.guild.id]):
            cmd_or_cog.disabled_in[ctx.guild.id] = False
            
            if isinstance(cmd_or_cog, commands.Command):
                await ctx.answer(ctx.lang["general"]["cmd_enabled"].format(
                    cmd_or_cog.qualified_name))
            else:
                await ctx.answer(ctx.lang["general"]["cog_enabled"].format(
                    cmd_or_cog.qualified_name))

            check = await self.bot.db.execute(
                "UPDATE `disable` SET `disabled` = ? WHERE `server` = ? AND `command` = ?",
                False, ctx.guild.id, cmd_or_cog.qualified_name,
                with_commit=True)

            if not check:
                await set_disable_state(ctx, cmd_or_cog, False)
        else:
            if isinstance(cmd_or_cog, commands.Command):
                await ctx.answer(ctx.lang["general"]["cmd_disabled"].format(
                    cmd_or_cog.qualified_name))
            else:
                await ctx.answer(ctx.lang["general"]["cog_disabled"].format(
                    cmd_or_cog.qualified_name))

            if ctx.guild.id not in cmd_or_cog.disabled_in:
                await set_disable_state(ctx, cmd_or_cog, True)

            cmd_or_cog.disabled_in[ctx.guild.id] = True

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()

        disables = await self.bot.db.execute(
            "SELECT * FROM `disable`", 
            fetch_all=True)

        if disables is None:
            return  

        models = {}

        for name in set(map(lambda x: x[1], disables)):
            if name[0].isupper():
                model = self.bot.get_cog(name)
            else:
                model = self.bot.get_command(name)

            if model is not None:
                models[name] = model

        incorrect_guilds = []

        for guild_id, name, is_disabled in filter(
                lambda x: x[0] not in incorrect_guilds, 
                disables):
                
            if name not in models:
                continue

            guild = self.bot.get_guild(guild_id)

            if guild is None:
                incorrect_guilds.append(guild_id)
                continue

            model = models[name]
            set_disabled(model)
            model.disabled_in[guild_id] = bool(is_disabled)


def setup(bot):
    bot.add_cog(General(bot))