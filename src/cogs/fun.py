import discord

from discord.ext import commands
from enum import Enum

from .utils.constants import EmbedConstants
from .utils.strings import markdown


class RextesterPLs(Enum):

    CSharp = 1
    VBNet = 2
    FSharp = 3
    Java = 4
    Python = 5
    C = 6
    CPP = 7
    Php = 8
    Pascal = 9
    ObjectiveC = 10
    Haskell = 11
    Ruby = 12
    Perl = 13
    Lua = 14
    Nasm = 15
    JavaScript = 17
    Lisp = 18
    Prolog = 19
    Go = 20
    Scala = 21
    Scheme = 22
    Nodejs = 23
    Python3 = 24
    Octave = 25
    D = 30
    R = 31
    Tcl = 32
    MySQL = 33
    PostgreSQL = 34
    Oracle = 35
    Swift = 37
    Bash = 38
    Ada = 39
    Erlang = 40
    Elixir = 41
    Ocaml = 42
    Kotlin = 43
    BrainFuck = 44
    Fortran = 45


class RextesterPLConverter(commands.Converter):

    __qualname__ = "Programming language"

    async def convert(self, ctx, arg):
        arg = arg.lower()

        lang = discord.utils.find(
            lambda x: x[0].lower() == arg, 
            RextesterPLs.__members__.items())

        if lang is None:
            raise commands.BadArgument(ctx.lang["fun"]["invalid_prog_lang"])

        return lang[1]


class Fun(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.rextester_api_url = "https://rextester.com/rundotnet/api"

    # TODO:
    #   use Optional[code] then read code from a file
    #   file maxsize idk*
    @commands.group(invoke_without_command=True)
    @commands.cooldown(5, 1, type=commands.BucketType.user)
    async def rextester(self, ctx, prog_lang: RextesterPLConverter, *, code: str):
        code = code.strip("`\n ")

        req_data = {
            "LanguageChoice": str(prog_lang.value),
            "Program": code,
            "Input": "",
            "CompilerArgs": f"source_file.{prog_lang.name.lower()} -o a.out"
        }

        async with self.bot.session.post(self.rextester_api_url, data=req_data) as req:
            data = await req.json()

        if data["Errors"] is not None and len(data["Errors"]):
            await ctx.answer(data["Errors"][:EmbedConstants.DESC_MAX_LEN])
        elif data["Result"] is not None and len(data["Result"]):
            await ctx.answer(data["Result"][:EmbedConstants.DESC_MAX_LEN])
        else:
            await ctx.answer(ctx.lang["fun"]["no_result"])

    @rextester.command(name="langs")
    @commands.cooldown(5, 1, type=commands.BucketType.user)
    async def rextester_langs(self, ctx):
        lang_info = map(lambda x: x[0], RextesterPLs.__members__.items())
        await ctx.answer(markdown(', '.join(lang_info), "```"))


def setup(bot):
    bot.add_cog(Fun(bot))