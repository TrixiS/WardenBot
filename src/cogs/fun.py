import discord

from discord.ext import commands
from enum import Enum
from typing import Optional

from .utils.constants import EmbedConstants, FunConstants
from .utils.strings import markdown

# TODO:
#   choose command

class RextesterPLs(Enum):

    CSharp = 1
    VBNet = 2
    FSharp = 3
    Java = 4
    Python2 = 5
    C = 6
    CPP = 7
    PHP = 8
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
    NodeJS = 23
    Python3 = 24
    Octave = 25
    D = 30
    R = 31
    TCL = 32
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
        arg = arg.lower().replace('#', 'sharp').replace('++', 'pp')

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

    @commands.group(aliases=["rex"], invoke_without_command=True)
    @commands.cooldown(1, 5, type=commands.BucketType.user)
    async def rextester(self, ctx, prog_lang: RextesterPLConverter, *, code: Optional[str]):
        right_attachment = discord.utils.find(
            lambda a: 0 < a.size <= FunConstants.ATTACH_MAX_SIZE,
            ctx.message.attachments)
        
        if code is None and right_attachment is not None:
            try:
                code = (await right_attachment.read()).decode("utf-8")
            except:
                return await ctx.answer(ctx.lang["fun"]["invalid_attachment"].format(
                    FunConstants.ATTACH_MAX_SIZE / 1000000))
        elif code is None:
            return await ctx.answer(ctx.lang["fun"]["need_code"])    

        req_data = {
            "LanguageChoice": str(prog_lang.value),
            "Program": code.strip("`\n "),
            "Input": "",
            "CompilerArgs": f"source_file.{prog_lang.name.lower()} -o a.out"
        }

        async with self.bot.session.post(self.rextester_api_url, data=req_data) as req:
            data = await req.json()

        offset = EmbedConstants.DESC_MAX_LEN - len("```")

        if data["Errors"] is not None and len(data["Errors"]):
            await ctx.answer(markdown(data["Errors"][:offset], "```"))
        elif data["Result"] is not None and len(data["Result"]):
            await ctx.answer(markdown(data["Result"][:offset], "```"))
        else:
            await ctx.answer(ctx.lang["fun"]["no_result"])

    @rextester.command(name="langs")
    async def rextester_langs(self, ctx):
        lang_info = sorted(RextesterPLs.__members__.keys())
        await ctx.answer(markdown(', '.join(lang_info), "```"))

    @commands.command(aliases=["ava"])
    async def avatar(self, ctx, member: Optional[discord.Member]):
        em = discord.Embed(
            title=ctx.lang["fun"]["avatar"].format((member or ctx.author).name),
            colour=ctx.color)

        em.set_image(url=(member or ctx.author).avatar_url)

        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Fun(bot))