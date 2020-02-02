import discord

from discord.ext import commands
from enum import Enum


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


def setup(bot):
    bot.add_cog(Fun(bot))