import discord

from discord.ext import commands
from .utils.strings import markdown, human_choice
from .utils.constants import StringConstants
from typing import Union, Optional


class Help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def prepare_arguments(self, ctx, arugments) -> list:

        def prepare_type(typ):
            return getattr(typ, '__qualname__', typ.__class__.__qualname__)

        def prepare_name(name):
            return ' '.join(name.split('_')).capitalize()

        def prepare_argument(typ: type, name: str, prefix: str) -> str:
            return f"{prefix} {prepare_name(name)} -> {prepare_type(typ)}"

        prepared = []

        for name, typ in arugments:
            if hasattr(typ, "__origin__") and typ.__origin__._name == "Union":
                if type(None) not in typ.__args__:
                    args = typ.__args__
                    prefix = StringConstants.DOT_SYMBOL
                else:
                    args = typ.__args__[:-1]
                    prefix = '*'

                if len(args) > 1:
                    prepared.append(
                        f"{prefix} {prepare_name(name)} -> " + human_choice(
                            tuple(map(lambda x: x.__qualname__, args)), 
                            second_sep=ctx.lang["shared"]["or"]))
                else:
                    prepared.append(prepare_argument(args[0], name, prefix))
            elif isinstance(typ, type(commands.Greedy)):
                converted = prepare_argument(typ.converter, name, StringConstants.DOT_SYMBOL)
                prepared.append(converted + "[]")
            else:
                prepared.append(
                    prepare_argument(typ, name, StringConstants.DOT_SYMBOL))

        return prepared

    def qualified_names(self, to_inspect):
        for command in sorted(set(to_inspect.walk_commands()), key=lambda c: c.qualified_name):
            yield command.qualified_name

    @commands.command(name="help")
    async def help_command(self, ctx, *, command_or_module: Optional[str]):
        em = discord.Embed(colour=ctx.color)

        if command_or_module is None:
            em.title = ctx.lang["help"]["modules"].format(self.bot.user.name)
            em.description = f"[{ctx.lang['info']['docs']}]({self.bot.config.docs_url})\n\n" + \
                markdown('\n'.join(sorted(self.bot.cogs.keys())), "```")
            return await ctx.send(embed=em)
            
        cog = self.bot.get_cog(command_or_module)

        if cog is not None:
            em.title = ctx.lang["help"]["cog_commands"].format(cog.__class__.__name__)
            em.description = markdown(
                '\n'.join(self.qualified_names(cog)) or ctx.lang["shared"]["no"], "```")
            
            return await ctx.send(embed=em)

        command = self.bot.get_command(command_or_module)

        if command is None:
            return await ctx.answer(ctx.lang["help"]["command_not_found"])

        arguments_expl = self.prepare_arguments(ctx, command.callback.__annotations__.items())

        em.add_field(
            name=ctx.lang["help"]["arguments"], 
            value=markdown('\n'.join(arguments_expl) or ctx.lang["shared"]["no"], "```"),
            inline=False)

        em.add_field(
            name=ctx.lang["help"]["subcommands"],
            value=markdown(
                '\n'.join(self.qualified_names(command)) 
                if isinstance(command, commands.Group) else ctx.lang["shared"]["no"], 
                "```"),
            inline=False)

        permissions = []

        for check in command.checks:
            if check.__qualname__.startswith("is_"):
                func_name = check.__qualname__.split('.')[0][3:]
                permissions.append(func_name.capitalize())
            elif check.__qualname__.startswith("has_"):
                permissions.append(ctx.lang["help"]["guild_permissions"])

        em.add_field(
            name=ctx.lang["help"]["required_permissions"],
            value=markdown('\n'.join(permissions) or ctx.lang["shared"]["no"], "```"))

        em.title = f'{ctx.lang["help"]["command"]} {StringConstants.DOT_SYMBOL} **{command.qualified_name}**'

        await ctx.send(embed=em)


def setup(bot):
    bot.remove_command("help")
    bot.add_cog(Help(bot))