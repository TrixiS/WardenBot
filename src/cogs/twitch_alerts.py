import discord
import time
import datetime
import logging

from discord.ext import commands, tasks
from twitch import TwitchClient
from .utils.checks import is_commander

# TODO (#1):
#   add langs for moderation + twitch


class Alerts:

    def __init__(self, bot):
        self.bot = bot

    async def get_anonse_channel(self, guild):
        channel_id = await self.bot.db.execute("SELECT `channel` FROM `twitch_channels` WHERE `twitch_channels`.`server` = ?",
            guild.id)

        if channel_id is None:
            return

        return guild.get_channel(channel_id)

    async def set_anonse_channel(self, guild, new_channel):
        check = await self.bot.db.execute("UPDATE `twitch_channels` SET `channel` = ? WHERE `twitch_channels`.`server` = ?",
            new_channel.id, guild.id, with_commit=True)

        if not check:
            await self.bot.db.execute("INSERT INTO `twitch_channels` VALUES (?, ?)",
                guild.id, new_channel.id, with_commit=True)

    async def get_subscribed_guilds(self, user_id):
        check = await self.bot.db.execute("SELECT `server` FROM `twitch` WHERE `twitch`.`user_id` = ?",
            user_id, fetch_all=True)

        guilds = []

        for row in check:
            guild = self.bot.get_guild(row[0])

            if guild is None:
                continue

            guilds.append(guild) 

        return guilds


class TwitchAlertsCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.client = TwitchClient(client_id=bot.config.twitch_client_id)
        self.alerts = Alerts(bot)
        self.base_url = "https://twitch.tv/"

        self.anonse.start()

    def cog_unload(self):
        self.anonse.cancel()

    def embed_url(self, user):
        return f"[{user['display_name']}]({self.base_url}{user['name']})"

    async def send_alert(self, channel, user, stream):
        if not channel.permissions_for(channel.guild.me).send_messages:
            return

        lang = await self.bot.get_lang(channel.guild)
        color = await self.bot.get_color(channel.guild)

        em = discord.Embed(
            description=f"[{stream['channel']['status']}](https://twitch.tv/{user['name']}/)", 
            colour=color)
        
        em.add_field(name=lang["twitch"]["game"], value=stream["game"].capitalize())
        em.add_field(name=lang["twitch"]["viewers"], value=stream["viewers"])
        
        em.set_author(name=user["display_name"], icon_url=user["logo"])
        em.set_image(url=stream["preview"]["large"])
        em.set_thumbnail(url=user["logo"])

        await channel.send(embed=em)

    @tasks.loop(minutes=1, count=None)
    async def anonse(self):
        check = await self.bot.db.execute("SELECT `user_id` FROM `twitch` GROUP BY `user_id` HAVING COUNT(*) >= 1",
            fetch_all=True)
        
        if check is None or len(check) == 0:
            return

        for row in check:
            user = self.client.users.get_by_id(row[0])

            if user is None or len(user) == 0:
                continue

            stream = self.client.streams.get_stream_by_user(row[0])

            if stream is None or len(stream) == 0 or stream["created_at"] < datetime.datetime.now():
                continue

            for guild in (await self.alerts.get_subscribed_guilds(row[0])):
                anonse_channel = await self.alerts.get_anonse_channel(guild)

                if anonse_channel is not None:
                    await self.send_alert(anonse_channel, user, stream)

    @anonse.before_loop
    async def anonse_before(self):
        await self.bot.wait_until_ready()

    @commands.group(invoke_without_command=True)
    @is_commander()
    async def twitch(self, ctx):
        subs = await self.bot.db.execute("SELECT `user_id` FROM `twitch` WHERE `twitch`.`server` = ?",
            ctx.guild.id, fetch_all=True)

        if subs is None or len(subs) == 0:
            return await ctx.answer(ctx.lang["twitch"]["no_subs"])

        users = map(lambda s: self.client.users.get_by_id(s[0]), subs)

        em = discord.Embed(title=ctx.lang["twitch"]["subs_title"], colour=ctx.color)
        em.description = ', '.join(map(self.embed_url, users))
        em.set_thumbnail(url=ctx.guild.icon_url)

        await ctx.send(embed=em)

    @twitch.command(name="sub")
    @is_commander()
    async def twitch_sub(self, ctx, *, username: str):
        user = self.client.users.translate_usernames_to_ids(username)

        if len(user) == 0:
            return await ctx.answer(ctx.lang["twitch"]["invalid_user"].format(
                username))
        else:
            user = user[0]

        check = await self.bot.db.execute("DELETE FROM `twitch` WHERE `twitch`.`user_id` = ? AND `twitch`.`server` = ?",
            user["id"], ctx.guild.id, with_commit=True)

        if check:
            await ctx.answer(ctx.lang["twitch"]["unsub"].format(self.embed_url(user)))
        else:
            await self.bot.db.execute("INSERT INTO `twitch` VALUES (?, ?)",
                ctx.guild.id, user["id"], with_commit=True)

            await ctx.answer(ctx.lang["twitch"]["sub"].format(self.embed_url(user)))

    @twitch.command(name="channel")
    @is_commander()
    async def twitch_channel(self, ctx, channel: discord.TextChannel=None):
        set_channel = await self.alerts.get_anonse_channel(ctx.guild)

        if channel is None:
            if set_channel is None:
                await ctx.answer(ctx.lang["twitch"]["no_channel"])
            else:
                await ctx.answer(ctx.lang["twitch"]["now_channel"].format(set_channel.mention))
        else:
            if channel == set_channel:
                await self.bot.db.execute("DELETE FROM `twitch_channels` WHERE `twitch_channels`.`server` = ?",
                    ctx.guild.id, with_commit=True)
                await ctx.answer(ctx.lang["twitch"]["channel_deleted"].format(channel.mention))
            else:
                await self.alerts.set_anonse_channel(ctx.guild, channel)
                await ctx.answer(ctx.lang["twitch"]["new_channel"].format(channel.mention))


def setup(bot):
    bot.add_cog(TwitchAlertsCog(bot))