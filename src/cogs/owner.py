import discord
import ast

from discord.ext import commands

from .utils.checks import is_owner


def insert_returns(body):
	if isinstance(body[-1], ast.Expr):
		body[-1] = ast.Return(body[-1].value)
		ast.fix_missing_locations(body[-1])
	if isinstance(body[-1], ast.If):
		insert_returns(body[-1].body)
		insert_returns(body[-1].orelse)
	if isinstance(body[-1], ast.With):
		insert_returns(body[-1].body)


class Owner(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="load")
    @is_owner()
    async def load_cog(self, ctx, *, cog: str):
        try:
            self.bot.load_extension(cog)
            await ctx.answer(ctx.lang["owner"]["load_success"].format(cog))
        except Exception as e:
            await ctx.answer(f"{type(e).__name__}\n{e}")

    @commands.command(name="unload")
    @is_owner()
    async def unload_cog(self, ctx, *, cog: str):
        try:
            self.bot.unload_extension(cog)
            await ctx.answer(ctx.lang["owner"]["unload_success"].format(cog))
        except Exception as e:
            await ctx.answer(f"{type(e).__name__}\n{e}")

    @commands.command(name="reload")
    @is_owner()
    async def reload_cog(self, ctx, *, cog: str):
        try:
            self.bot.reload_extension(cog)
            await ctx.answer(ctx.lang["owner"]["reload_success"].format(cog))
        except Exception as e:
            await ctx.answer(f"{type(e).__name__}\n{str(e)}")

    @commands.command(name="eval")
    @is_owner()
    async def eval(self, ctx, *, code: str):
        fn_name = "_eval_expr"

        cmd = code.strip('` ')
        cmd = '\n'.join(f"	{i}" for i in cmd.splitlines())
        body = f"async def {fn_name}():\n{cmd}"

        parsed = ast.parse(body)
        body = parsed.body[0].body

        insert_returns(body)

        env = {
            "bot": ctx.bot,
            "discord": discord,
            "command": discord.ext.commands,
            "ctx": ctx,
            "__import__": __import__,
            "__name__": __name__
        }

        exec(compile(parsed, filename="<ast>", mode="exec"), env)

        fmt = "```Python\n{}```"

        try:
            result = (await eval(f"{fn_name}()", env))
            await ctx.answer(fmt.format(result))
        except Exception as e:
            await ctx.answer(fmt.format(f"{type(e).__name__}: {str(e)}"))

    @commands.command()
    @is_owner()
    async def kill(self, ctx):
        await self.bot.session.close()
        await self.bot.logout()
        exit()


def setup(bot):
    bot.add_cog(Owner(bot))