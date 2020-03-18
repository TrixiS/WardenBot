import discord
import datetime

from discord.ext import commands
from typing import Optional

from .utils.constants import InfoConstants

# TODO:
# add langs and economy commands and update bot command
# on prod bot


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

    @commands.command()
    async def bot(self, ctx):
        em = discord.Embed(
            description=self.bot.user.mention, 
            colour=ctx.color)

        em.add_field(
            name=ctx.lang["info"]["uptime"], 
            value="{} {:%d.%m.%y %H:%M}".format(ctx.lang["info"]["since"], self.bot.uptime))
        em.add_field(
            name=ctx.lang["info"]["invite"], 
            value=f"[{ctx.lang['shared']['click']}]"
                    f"({InfoConstants.BOT_INVITE_URL.format(self.bot.user.id)})")
        em.add_field(
            name=ctx.lang["info"]["members"],
            value=len(self.bot.users))
        em.add_field(
            name=ctx.lang["info"]["guilds"],
            value=len(self.bot.guilds))
        em.add_field(
            name=ctx.lang["info"]["latency"],
            value=f"{round(self.bot.latency, 3)} {ctx.lang['shared']['seconds']}")
        em.add_field(
            name=ctx.lang["info"]["owners"],  
            value='\n'.join(self.bot.get_user(uid).mention for uid in self.bot.config.owners))

        em.set_thumbnail(url=self.bot.user.avatar_url)

        await ctx.send(embed=em)

    @commands.command()
    async def lastchange(self, ctx):
        url = InfoConstants.GHUB_API_URL + "/repos/TrixiS/WardenBot/commits/master"

        async with self.bot.session.get(url) as req:
            data = await req.json()

        em = discord.Embed(
            title=ctx.lang["info"]["last_commit"], 
            colour=ctx.color)

        em.add_field(
            name=ctx.lang["shared"]["author"], 
            value=f"[{data['author']['login']}]({data['author']['html_url']})")
        em.add_field(
            name=ctx.lang["info"]["committer"], 
            value=f"[{data['committer']['login']}]({data['committer']['html_url']})")
        em.add_field(
            name="URL", 
            value=f"[{ctx.lang['shared']['click']}]({data['html_url']})")

        commit_date = datetime.datetime.strptime(
            data["commit"]["committer"]["date"], 
            "%Y-%m-%dT%H:%M:%SZ")
        
        em.add_field(
            name=ctx.lang["shared"]["created"], 
            value="{:%d.%m.%Y %H:%M}".format(commit_date))
        em.add_field(
            name=ctx.lang["shared"]["message"],
            value=data["commit"]["message"],
            inline=False)

        em.set_thumbnail(url=data["committer"]["avatar_url"])

        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Info(bot))