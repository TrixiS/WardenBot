import discord

from discord.ext import commands


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

# TODO:
#   member
#   channel
#   emoji command with human emoji for lang adding

def setup(bot):
    bot.add_cog(Info(bot))