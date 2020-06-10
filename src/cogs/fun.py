import discord
import random
import string
import datetime

from discord.ext import commands
from enum import Enum
from typing import Optional
from urllib.parse import urlencode

from .utils.constants import EmbedConstants, FunConstants, DiscordConstants
from .utils.strings import markdown, human_choice, multi_replace
from .utils.converters import EnumConverter, EqualRole
from .utils.checks import bot_has_permissions


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


class RextesterPLConverter(EnumConverter):

    __qualname__ = "ProgrammingLanguage"

    def __init__(self):
        super().__init__(RextesterPLs)

    async def convert(self, ctx, arg):
        arg = arg.lower().replace('#', 'sharp').replace('++', 'pp')
        return await super().convert(ctx, arg)


class SpellerLanguage(Enum):

    RU = 0
    UK = 1
    EN = 2


class SpellerLanguageConverter(EnumConverter):

    __qualname__ = "Language"

    def __init__(self):
        super().__init__(SpellerLanguage)


class Fun(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.group(aliases=["rex"], invoke_without_command=True)
    @commands.cooldown(1, 5, type=commands.BucketType.user)
    async def rextester(self, ctx, prog_lang: RextesterPLConverter, *, code: Optional[str]):
        right_attachment = discord.utils.find(
            lambda a: 0 < a.size <= FunConstants.ATTACH_MAX_SIZE,
            ctx.message.attachments)
            
        if code is None and right_attachment is not None:
            try:
                code = (await right_attachment.read()).decode("utf-8")
            except Exception:
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

        async with self.bot.session.post(FunConstants.REX_API_URL, data=req_data) as req:
            data = await req.json()

        offset = EmbedConstants.DESC_MAX_LEN - len("```") * 2

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

    @commands.command()
    async def choose(self, ctx, *words: str):
        if len(words) == 0:
            await ctx.answer(ctx.lang["fun"]["choose_seq"])
        else:
            await ctx.send(random.choice(words))

    @commands.command()
    async def dog(self, ctx):
        async with self.bot.session.get(FunConstants.DOG_API_URL) as req:
            image_url = (await req.json())['message']

        em = discord.Embed(
            title=ctx.lang["fun"]["dog"].format(ctx.author.name), 
            colour=ctx.color)
        em.set_image(url=image_url)

        await ctx.send(embed=em)

    @commands.command()
    async def coin(self, ctx):
        await ctx.send(random.choice(ctx.lang["fun"]["coins"]))

    @commands.command()
    async def reverse(self, ctx, *, text: commands.clean_content):
        await ctx.send(text[::-1])

    @commands.command(aliases=["switch"])
    async def punto(self, ctx, *, text: commands.clean_content):
        ru_letters = {
            'й': 'q',
            'ц': 'w',
            'у': 'e',
            'к': 'r',
            'е': 't',
            'н': 'y',
            'г': 'u',
            'ш': 'i',
            'щ': 'o',
            'з': 'p',
            'х': '[',
            'ъ': ']',
            'ф': 'a',
            'ы': 's',
            'в': 'd',
            'а': 'f',
            'п': 'g',
            'р': 'h',
            'о': 'j',
            'л': 'k',
            'д': 'l',
            'ж': ';',
            'э': '\'',
            'я': 'z',
            'ч': 'x',
            'с': 'c',
            'м': 'v',
            'и': 'b',
            'т': 'n',
            'ь': 'm',
            'б': ',',
            'ю': '.'
        }       

        en_letters = {
            'q': 'й',
            'w': 'ц',
            'e': 'у',
            'r': 'к',
            't': 'е',
            'y': 'н',
            'u': 'г',
            'i': 'ш',
            'o': 'щ',
            'p': 'з',
            '[': 'х',
            ']': 'ъ',
            'a': 'ф',
            's': 'ы',
            'd': 'в',
            'f': 'а',
            'g': 'п',
            'h': 'р',
            'j': 'о',
            'k': 'л',
            'l': 'д',
            ';': 'ж',
            '\'': 'э',
            'z': 'я',
            'x': 'ч',
            'c': 'с',
            'v': 'м',
            'b': 'и',
            'n': 'т',
            'm': 'ь',
            ',': 'б',
            '.': 'ю'
        }

        translated_text = ""

        for letter in text:
            was_upper = letter.isupper()
            letter = letter.lower()
            translated_letter = None

            if letter in ru_letters:
                translated_letter = ru_letters[letter]
            elif letter in en_letters:
                translated_letter = en_letters[letter]
            else:
                translated_letter = letter

            if was_upper:
                translated_text += translated_letter.upper()
            else:
                translated_text += translated_letter

        await ctx.send(translated_text)

    @commands.command()
    async def speller(self, ctx, lang: SpellerLanguageConverter, word: str):
        if not word.isalpha():
            return await ctx.answer(ctx.lang["fun"]["alpha_needed"])
        
        req_data = {
            "text": word,
            "lang": lang.name,
            "format": "plain"
        }

        async with self.bot.session.post(FunConstants.SPELLER_API_URL, data=req_data) as req:
            data = await req.json()
    
        if len(data) == 0 or len(data[0]['s']) == 0:
            return await ctx.answer(ctx.lang["fun"]["no_mistakes"])

        await ctx.answer(', '.join(data[0]['s']).capitalize())

    @commands.command()
    async def say(self, ctx, *, text: commands.clean_content):
        await ctx.send(text)

    @commands.command()
    async def roll(self, ctx, min_value: Optional[int] = 1, max_value: Optional[int] = 100):
        await ctx.send(str(random.randint(min_value, max_value)))

    @commands.command(aliases=["color", "colour"])
    async def hex(self, ctx, hex_color: discord.Colour):
        em = discord.Embed(
            title=ctx.lang["shared"]["color"], 
            colour=hex_color)
        
        str_hex = str(hex_color)[1:].upper()

        em.add_field(
            name="HEX", 
            value=str_hex, 
            inline=False)
        em.add_field(
            name="RGB", 
            value=str(hex_color.to_rgb()), 
            inline=False)

        req_data = {
            "hex": str_hex,
            "width": 200,
            "height": 200
        }

        em.set_thumbnail(url=FunConstants.IMAGE_API_URL + urlencode(req_data))

        await ctx.send(embed=em)

    @commands.command()
    async def cycle(self, ctx, *, text: commands.clean_content):
        result = []
        
        for i, s in enumerate(text):
            if (i + 1) % 2 != 0:
                result.append(s.upper())
            else:
                result.append(s.lower())

        await ctx.send(''.join(result))

    @commands.command()
    async def encode(self, ctx, *, text: str):
        encoded = ' '.join(
            str(bin(ord(s)))[2:] 
            for s in text 
            if s not in string.whitespace)

        await ctx.answer(encoded)

    @commands.command()
    async def decode(self, ctx, *, text: str):
        if any(s not in "01 " for s in text):
            return await ctx.answer(ctx.lang["fun"]["binary_only"])
        
        decoded = (
            chr(int(code, base=2)) 
            for code in text.split()
            if len(code) <= FunConstants.MAX_CHAR_BYTE_LEN)

        await ctx.answer(''.join(decoded) or ctx.lang["fun"]["incorrect_bytes"])

    @commands.command()
    @bot_has_permissions(manage_roles=True)
    async def colorme(self, ctx, *, color: discord.Colour):
        select_sql = """
        SELECT `role`
        FROM `color_roles`
        WHERE `color_roles`.`server` = ? AND `color_roles`.`member` = ?
        """

        role_id = await self.bot.db.execute(
            select_sql, ctx.author.id, ctx.guild.id)

        color_role = ctx.guild.get_role(role_id) or discord.utils.find(
            lambda r: r.name == str(ctx.author), 
            ctx.guild.roles)

        if color_role is None:
            color_role = await ctx.guild.create_role(
                name=str(ctx.author), 
                colour=color)

            await self.bot.db.execute(
                "INSERT INTO `color_roles` VALUES (?, ?, ?)", 
                ctx.guild.id, ctx.author.id, color_role.id,
                with_commit=True)
        else:
            if color_role >= ctx.guild.me.top_role:
                return await ctx.answer(ctx.lang["errors"]["role_over_top_role"].format(
                    color_role.mention))

            await color_role.edit(colour=color)

        if color_role not in ctx.author.roles:
            await ctx.author.add_roles(color_role)

        await ctx.answer(ctx.lang["fun"]["color_changed"].format(
            str(color).upper()))


def setup(bot):
    bot.add_cog(Fun(bot))
