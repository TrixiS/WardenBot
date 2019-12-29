import discord

from discord.ext import commands
from typing import Optional
from math import ceil

from .utils.converters import IndexConverter, Index
from .utils.strings import markdown


class TagCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.tag_check_page_max = 30

    @commands.group(invoke_without_command=True, aliases=['t'])
    async def tag(self, ctx, *, name: commands.clean_content):
        check = await self.bot.db.execute("SELECT `content` FROM `tags` WHERE `tags`.`member` = ? AND `tags`.`name` LIKE ?",
            ctx.author.id, name)

        if check is not None:
            await ctx.send(check)
            await ctx.message.delete()

            await self.bot.db.execute("UPDATE `tags` SET `used` = `used` + 1 WHERE `tags`.`member` = ? AND `tags`.`name` LIKE ?",
                ctx.author.id, name, with_commit=True)
        else:
            await ctx.answer(ctx.lang["tags"]["no"].format(name))

    @tag.command(name="check")
    async def tag_check(self, ctx, member: Optional[discord.Member]=None, page: IndexConverter=Index(0)):
        member = member or ctx.message.author
    
        check = await self.bot.db.execute("SELECT `name` FROM `tags` WHERE `tags`.`member` = ? ORDER BY `tags`.`created` LIMIT ? OFFSET ?",
            member.id, self.tag_check_page_max, self.tag_check_page_max * page.value,
            fetch_all=True
        )

        if check is not None and len(check) > 0:
            count = await self.bot.db.execute("SELECT COUNT(*) FROM `tags` WHERE `tags`.`member` = ?",
                member.id)

            em = discord.Embed(title=ctx.lang["tags"]["check_title"].format(member.name),
                description=', '.join(markdown(c[0], '`') for c in check),
                colour=ctx.color
            )
            em.set_thumbnail(url=member.avatar_url)
            em.set_footer(text=f'{ctx.lang["shared"]["page"]}: {page.humanize()}/{ceil(count / self.tag_check_page_max)}')           

            return await ctx.send(embed=em)

        await ctx.answer(ctx.lang["tags"]["dont_have_any"].format(member.mention, page.humanize()))            

    @tag.command(name="create")
    async def tag_create(self, ctx, *, name: commands.clean_content):
        check = await self.bot.db.execute("SELECT `name` FROM `tags` WHERE `tags`.`member` = ? AND `tags`.`name` LIKE ?",
            ctx.message.author.id, name)

        if check is None:
            content = await commands.clean_content().convert(ctx,
                await ctx.ask(ctx.lang["tags"]["content?"], timeout=30.0)
            )

            await self.bot.db.execute("INSERT INTO `tags` VALUES (?, ?, ?, ?, UNIX_TIMESTAMP())",
                ctx.message.author.id, name, content, 0, with_commit=True)

            return await ctx.answer(ctx.lang["tags"]["created"].format(name))

        await ctx.answer(ctx.lang["tags"]["already_created"].format(name))
            

def setup(bot):
    bot.add_cog(TagCog(bot))