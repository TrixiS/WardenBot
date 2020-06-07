import discord

from discord.ext import commands
from typing import Union, Optional

from .utils.constants import StringConstants
from .utils.strings import markdown, human_choice
from .utils.checks import bot_has_permissions
from .utils.models import Pages


class Help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.arg_page = """
        {lang[help][arguments_expl]}\n
        * — {lang[help][optional_argument]}
        {dot} — {lang[help][required_argument]}\n
        ```[* {lang[shared][or]} {dot}] \
        [{lang[help][arg_name]}] -> \
        [{lang[help][arg_type]}]```
        """.replace(' ' * 8, '')

        self.type_page = """{lang[help][types_expl]}\n
        {types}"""

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

    # TODO: close todos from #todos channel
    # TODO: add lang description to all commands
    # TODO: maybe use mysql async lib rewrite db.py
    @commands.group(name="help", invoke_without_command=True)
    async def help_command(self, ctx, *, command_or_module: Optional[str]):
        em = discord.Embed(colour=ctx.color)

        if command_or_module is None:
            em.title = ctx.lang["help"]["modules"].format(self.bot.user.name)
            em.description = (f"[{ctx.lang['info']['docs']}]({self.bot.config.docs_url})\n\n" +
                markdown('\n'.join(sorted(cog.qualified_name for cog in self.bot.cogs.values())), "```\n"))
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

        if arguments_expl:
            em.add_field(
                name=ctx.lang["help"]["arguments"], 
                value=markdown('\n'.join(arguments_expl), "```"),
                inline=False)

        if command.aliases:
            em.add_field(
                name=ctx.lang["help"]["aliases"],
                value=markdown(", ".join(command.aliases), "```"),
                inline=False)

        if isinstance(command, commands.Group):
            subcommands = self.qualified_names(command)

            if subcommands:
                em.add_field(
                    name=ctx.lang["help"]["subcommands"],
                    value=markdown('\n'.join(subcommands), "```"),
                    inline=False)

        permissions = []

        for check in command.checks:
            if check.__qualname__.startswith("is_"):
                func_name = check.__qualname__.split('.')[0][3:]
                permissions.append(func_name.capitalize())
            elif check.__qualname__.startswith("has_"):
                permissions.append(ctx.lang["help"]["guild_permissions"])

        if permissions:
            em.add_field(
            name=ctx.lang["help"]["required_permissions"],
            value=markdown('\n'.join(permissions), "```"))

        em.title = f'{ctx.lang["help"]["command"]} {StringConstants.DOT_SYMBOL} **{command.qualified_name}**'

        await ctx.send(embed=em)
    
    @help_command.command(name="arguments", aliases=["args", "argument", "arg"])
    @bot_has_permissions(add_reactions=True)
    async def help_args(self, ctx):
        pages = Pages(ctx, [
            discord.Embed(**kwargs, colour=ctx.color)
            for kwargs in ctx.lang["help"]["help_args_pages"]
        ])

        await pages.paginate()


def setup(bot):
    bot.remove_command("help")
    bot.add_cog(Help(bot))