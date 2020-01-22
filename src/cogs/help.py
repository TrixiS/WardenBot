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

        def prepare_argument(typ, name: str, prefix: str) -> str:
            return f"{prefix} {prepare_name(name)} -> {prepare_type(typ)}"

        prepared = []

        for name, typ in arugments:
            true_type = type(typ)

            if (true_type == type(Union) and type(None) in typ.__args__) or \
                true_type == type(Optional):
                    prepared.append(prepare_argument(typ.__args__[0], name, '*'))
            elif true_type == type(Union):
                prepared.append(
                    f"{StringConstants.DOT_SYMBOL} {prepare_name(name)} -> " + human_choice(
                        tuple(map(lambda x: x.__qualname__, typ.__args__)), 
                        second_sep=ctx.lang["shared"]["or"]))
            else:
                prepared.append(
                    prepare_argument(typ, name, StringConstants.DOT_SYMBOL))

        return prepared

    @commands.command(name="help")
    async def help_command(self, ctx, *, command_or_module):
        cog = self.bot.get_cog(command_or_module)

        em = discord.Embed(colour=ctx.color)

        def qualified_names(to_inspect):
            for command in to_inspect.walk_commands():
                yield command.qualified_name

        if cog is not None:
            em.title = ctx.lang["help"]["cog_commands"].format(cog.__class__.__name__)
            em.description = markdown(
                '\n'.join(qualified_names(cog)), "```")
            
            return await ctx.send(embed=em)

        command = self.bot.get_command(command_or_module)

        if command is None:
            return await ctx.answer(ctx.lang["help"]["command_not_found"])

        arguments_expl = self.prepare_arguments(ctx, command.callback.__annotations__.items())

        em.add_field(
            name=ctx.lang["help"]["arguments"], 
            value=markdown('\n'.join(arguments_expl), "```") 
                if len(arguments_expl) else ctx.lang["shared"]["no"],
            inline=False)

        em.add_field(
            name=ctx.lang["help"]["subcommands"],
            value=markdown(
                '\n'.join(qualified_names(command)) 
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
