import discord

from discord.ext import commands
from typing import Optional
from math import ceil

from .utils.converters import IndexConverter, Index, Check
from .utils.strings import markdown
from .utils.time import UnixTime
from .utils.constants import TagsConstants


class Tags(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True, aliases=['t'])
    async def tag(self, ctx, *, name: commands.clean_content):
        check = await self.bot.db.execute("SELECT `content` FROM `tags` WHERE `tags`.`member` = ? AND `tags`.`name` = ?",
            ctx.author.id, name)

        if check is not None:
            await ctx.send(check)
            await ctx.message.delete()

            await self.bot.db.execute("UPDATE `tags` SET `used` = `used` + 1 WHERE `tags`.`member` = ? AND `tags`.`name` = ?",
                ctx.author.id, name, with_commit=True)
        else:
            await ctx.answer(ctx.lang["tags"]["no"].format(name))

    @tag.command(name="check")
    async def tag_check(self, ctx, member: Optional[discord.Member]=None, page: Optional[IndexConverter]=Index(0)):
        member = member or ctx.message.author
    
        check = await self.bot.db.execute("SELECT `name` FROM `tags` WHERE `tags`.`member` = ? ORDER BY `tags`.`created` LIMIT ? OFFSET ?",
            member.id, TagsConstants.CHECK_PAGE_MAX, 
            TagsConstants.CHECK_PAGE_MAX * page.value,
            fetch_all=True)

        if check is not None and len(check) > 0:
            count = await self.bot.db.execute("SELECT COUNT(*) FROM `tags` WHERE `tags`.`member` = ?",
                member.id)

            em = discord.Embed(title=ctx.lang["tags"]["check_title"].format(member.name),
                description=', '.join(markdown(c[0], '`') for c in check),
                colour=ctx.color)
            em.set_thumbnail(url=member.avatar_url)
            em.set_footer(text=f'{ctx.lang["shared"]["page"]}: {page.humanize()}/{ceil(count / TagsConstants.CHECK_PAGE_MAX)}')           

            return await ctx.send(embed=em)

        await ctx.answer(ctx.lang["tags"]["dont_have_any"].format(member.mention, page.humanize()))            

    @tag.command(name="create")
    async def tag_create(self, ctx, *, name: str):
        name = name[:TagsConstants.MAX_LEN]

        check = await self.bot.db.execute("SELECT `name` FROM `tags` WHERE `tags`.`member` = ? AND `tags`.`name` = ?",
            ctx.message.author.id, name)

        if check is None:
            content = await ctx.ask(ctx.lang["tags"]["content?"])

            if content is None:
                return

            content = await commands.clean_content().convert(ctx, 
                with_attachments=True, timeout=30.0)

            await self.bot.db.execute("INSERT INTO `tags` VALUES (?, ?, ?, ?, UNIX_TIMESTAMP())",
                ctx.message.author.id, name, content, 0, with_commit=True)

            return await ctx.answer(ctx.lang["tags"]["created"].format(name))

        await ctx.answer(ctx.lang["tags"]["already_created"].format(name))
            
    @tag.command(name="delete")
    async def tag_delete(self, ctx, *, name: commands.clean_content):
        check = await self.bot.db.execute("DELETE FROM `tags` WHERE `tags`.`member` = ? AND `tags`.`name` = ?",
            ctx.author.id, name, with_commit=True)

        if check:
            await ctx.answer(ctx.lang["tags"]["deleted"].format(name))
        else:
            await ctx.answer(ctx.lang["tags"]["no"].format(name))

    @tag.command(name="random")
    async def tag_random(self, ctx):
        check = await self.bot.db.execute("SELECT `member`, `name`, `content` FROM `tags` ORDER BY RAND() LIMIT 1")

        user = self.bot.get_user(check[0])
        fmt = f"{str(user)} - {check[1]}\n\n{check[2]}"

        await ctx.send(fmt)

    @tag.command(name="info")
    async def tag_info(self, ctx, member: Optional[discord.Member]=None, *, name: commands.clean_content):
        member = member or ctx.author

        check = await self.bot.db.execute("SELECT * FROM `tags` WHERE `tags`.`member` = ? AND `tags`.`name` = ?",
            member.id, name)

        if check is None:
            return await ctx.answer(ctx.lang["tags"]["no_with_name"].format(member.mention, name))

        owner = self.bot.get_user(check[0])
        created = UnixTime(check[4]).humanize()

        em = discord.Embed(title=ctx.lang["tags"]["information"], 
            colour=ctx.color)
        em.add_field(name=ctx.lang["shared"]["name"], value=name, inline=False)
        em.add_field(name=ctx.lang["shared"]["owner"], value=str(owner))
        em.add_field(name=ctx.lang["tags"]["used"], value=check[3])
        em.add_field(name=ctx.lang["shared"]["created"], value=created)
        em.set_thumbnail(url=ctx.message.author.avatar_url)

        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Tags(bot))