import discord

from discord.ext import commands
from typing import Optional


class Info(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["server"])
    async def guild(self, ctx):
        em = discord.Embed(
            description=f"**{ctx.lang['shared']['guild']}:** {ctx.guild.name}",
            colour=ctx.color)
        
        em.add_field(
            name=ctx.lang["shared"]["id"], 
            value=ctx.guild.id)
        em.add_field(
            name=ctx.lang["shared"]["created"], 
            value="{:%d.%m.%Y}".format(ctx.guild.created_at))
        em.add_field(
            name=ctx.lang["info"]["region"],
            value=str(ctx.guild.region).title())
        em.add_field(
            name=ctx.lang["shared"]["owner"],
            value=ctx.guild.owner.mention)
        em.add_field(
            name=ctx.lang["info"]["members"],
            value=ctx.guild.member_count)
        em.add_field(
            name=ctx.lang["info"]["roles"], 
            value=len(ctx.guild.roles))
        em.add_field(
            name=ctx.lang["info"]["channels"],
            value=len(ctx.guild.channels))
        em.add_field(
            name=ctx.lang["info"]["emojis"], 
            value=len(ctx.guild.emojis))
        em.add_field(
            name=ctx.lang["info"]["afk_channel"],
            value=(ctx.guild.afk_channel and ctx.guild.afk_channel.mention) or ctx.lang["shared"]["no"])

        em.set_thumbnail(url=ctx.guild.icon_url)

        await ctx.send(embed=em)

    @commands.command(aliases=["user"])
    async def member(self, ctx, *, member: Optional[discord.Member]):
        if member is None:
            member = ctx.author
        
        em = discord.Embed(
            description=f"**{ctx.lang['shared']['member']}:** {member.mention}",
            colour=ctx.color)

        date_fmt = r"{:%d.%m.%Y, %H:%M}"

        em.add_field(
            name=ctx.lang["shared"]["id"],
            value=member.id)
        em.add_field(
            name=ctx.lang["shared"]["created"],
            value=date_fmt.format(member.created_at))
        em.add_field(
            name=ctx.lang["info"]["joined"], 
            value=date_fmt.format(member.joined_at))
        em.add_field(
            name=ctx.lang["info"]["status"],
            value=str(member.status).title())
        em.add_field(
            name=ctx.lang["shared"]["color"], 
            value=str(member.color).upper())
        em.add_field(
            name=ctx.lang["info"]["top_role"],
            value=member.top_role.mention)

        em.set_thumbnail(url=member.avatar_url)

        await ctx.send(embed=em)

    @commands.command()
    async def channel(self, ctx, channel: Optional[discord.TextChannel]):
        if channel is None:
            channel = ctx.channel

        em = discord.Embed(
            description=f"**{ctx.lang['shared']['channel']}:** {channel.mention}",
            colour=ctx.color)

        em.add_field(
            name=ctx.lang["shared"]["id"],
            value=channel.id)
        em.add_field(
            name=ctx.lang["shared"]["created"],
            value="{:%d.%m.%Y}".format(channel.created_at))
        em.add_field(
            name=ctx.lang["shared"]["type"],
            value=str(channel.type).title())
        em.add_field(
            name="NSFW", 
            value=ctx.lang["shared"][str(channel.is_news())])
        em.add_field(
            name=ctx.lang["info"]["is_news"], 
            value=ctx.lang["shared"][str(channel.is_news())])
        em.add_field(
            name=ctx.lang["info"]["slowmode"],
            value=f"{channel.slowmode_delay} {ctx.lang['shared']['seconds']}")

        em.set_thumbnail(url=ctx.guild.icon_url)

        await ctx.send(embed=em)

    @commands.command()
    async def emoji(self, ctx, emoji: discord.Emoji):
        em = discord.Embed(
            description=f"**{ctx.lang['shared']['emoji']}:** {str(emoji)}",
            colour=ctx.color)

        em.add_field(
            name=ctx.lang["shared"]["id"], 
            value=emoji.id)
        em.add_field(
            name=ctx.lang["shared"]["created"], 
            value="{:%d.%m.%Y}".format(emoji.created_at))
        em.add_field(
            name="URL", 
            value=f"[{ctx.lang['shared']['click']}]({emoji.url})")
        em.add_field(
            name=ctx.lang["info"]["code"], 
            value=f"```{str(emoji)}```")

        em.set_thumbnail(url=emoji.url)

        await ctx.send(embed=em)

# TODO:
#   bot command
#   last change command (last commit from ghub (may be check its api))

def setup(bot):
    bot.add_cog(Info(bot))