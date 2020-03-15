import discord
import time
import datetime
import logging
import pytz
import twitch

from discord.ext import commands, tasks
from typing import Optional
from math import ceil

from .utils.checks import is_commander
from .utils.constants import TwitchAlertsConstants
from .utils.converters import Index, IndexConverter


class Alerts:

    def __init__(self, bot):
        self.bot = bot

    async def get_anonse_channel(self, guild):
        channel_id = await self.bot.db.execute("SELECT `channel` FROM `twitch_channels` WHERE `twitch_channels`.`server` = ?",
            guild.id)

        if channel_id is None:
            return

        return guild.get_channel(channel_id)

    async def set_anonse_channel(self, new_channel):
        check = await self.bot.db.execute("UPDATE `twitch_channels` SET `channel` = ? WHERE `twitch_channels`.`server` = ?",
            new_channel.id, new_channel.guild.id, with_commit=True)

        if not check:
            await self.bot.db.execute("INSERT INTO `twitch_channels` VALUES (?, ?)",
                new_channel.guild.id, new_channel.id, with_commit=True)

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


class TwitchAlerts(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.client = twitch.Helix(bot.config.twitch_client_id)
        self.alerts = Alerts(bot)
        self.latest_iter_time = self.utc_now()
        self.base_url = "https://twitch.tv/"

        self.anonse.start()

    def cog_unload(self):
        self.anonse.stop()

    def embed_url(self, user):
        return f"[{user.display_name}]({self.base_url}{user.login})"

    def utc_now(self):
        return datetime.datetime.now().astimezone(pytz.utc)

    async def send_alert(self, data, stream, user):
        lang, color, channel = data
        thumb_url = f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{user.login}-640x360.jpg"

        em = discord.Embed(
            description=f"[{stream.title}](https://twitch.tv/{user.login}/)", 
            colour=color)
        
        em.add_field(name=lang["twitch"]["viewers"], value=stream.viewer_count)

        em.set_author(name=user.display_name, icon_url=user.profile_image_url)
        em.set_image(url=thumb_url)
        em.set_thumbnail(url=user.profile_image_url)

        await channel.send(embed=em)

    async def get_subscriptions(self):
        check = await self.bot.db.execute("SELECT `user_id` FROM `twitch` GROUP BY `user_id` HAVING COUNT(*) >= 1",
            fetch_all=True)
        
        if check is None or len(check) == 0:
            return

        subscriptions = []
        users = self.client.users(map(lambda i: i[0], check))   

        for user in filter(lambda u: u is not None and u.is_live, users):
            try:
                stream = user.stream
            except Exception:
                continue

            if stream is None:
                continue

            stream_started = datetime.datetime.strptime(
                stream.started_at, r"%Y-%m-%dT%H:%M:%S%z").astimezone(pytz.utc)

            if self.latest_iter_time > stream_started:
                continue

            subscribed_guilds = await self.alerts.get_subscribed_guilds(
                int(stream.user_id))
            
            if len(subscribed_guilds):
                subscriptions.append((user, stream, subscribed_guilds))

        return subscriptions
            
    async def get_guild_data(self, guild):
        lang = await self.bot.get_lang(guild)
        color = await self.bot.get_color(guild)
        anonse_channel = await self.alerts.get_anonse_channel(guild)

        return lang, color, anonse_channel

    @tasks.loop(minutes=1, count=None)
    async def anonse(self):
        subscriptions = await self.get_subscriptions()

        if subscriptions is None or len(subscriptions) == 0:
            return

        guild_data = {}
        all_guilds = set()

        for row in subscriptions:
            all_guilds.update(row[2])

        for guild in all_guilds:
            data = await self.get_guild_data(guild)

            if data[2] is not None and data[2].permissions_for(guild.me).send_messages:
                guild_data[guild] = data

        for user, stream, guilds in subscriptions:
            for guild in guilds:
                if guild in guild_data:
                    await self.send_alert(guild_data[guild], stream, user)

        self.latest_iter_time = self.utc_now()

    @anonse.before_loop
    async def anonse_before(self):
        await self.bot.wait_until_ready()

    @commands.group(invoke_without_command=True)
    async def twitch(self, ctx, page: Optional[IndexConverter]=Index(0)):
        sql = """
        SELECT `user_id`
        FROM `twitch`
        WHERE `twitch`.`server` = ?
        LIMIT ? OFFSET ?
        """

        subs = await self.bot.db.execute(
            sql, ctx.guild.id, 
            TwitchAlertsConstants.USER_PER_PAGE,
            TwitchAlertsConstants.USER_PER_PAGE * page.value,
            fetch_all=True)

        if subs is None or len(subs) == 0:
            return await ctx.answer(ctx.lang["twitch"]["pages"].format(
                page.humanize()))

        count = await self.bot.db.execute(
            "SELECT COUNT(*) FROM `twitch` WHERE `twitch`.`server` = ?",
            ctx.guild.id)

        users = self.client.users(map(lambda x: x[0], subs))

        em = discord.Embed(
            title=ctx.lang["twitch"]["subs_title"], 
            description=', '.join(
                map(self.embed_url, 
                filter(lambda u: u is not None, users))),
            colour=ctx.color)

        footer_text = f"{ctx.lang['shared']['page']} " \
            f"{page.humanize()}/{ceil(count / TwitchAlertsConstants.USER_PER_PAGE)}"

        em.set_thumbnail(url=ctx.guild.icon_url)
        em.set_footer(text=footer_text)

        await ctx.send(embed=em)

    @twitch.command(name="sub")
    @is_commander()
    async def twitch_sub(self, ctx, *, twitch: str):
        user = self.client.user(twitch)

        if user is None:
            return await ctx.answer(ctx.lang["twitch"]["invalid_user"])

        int_user_id = int(user.id)

        check = await self.bot.db.execute(
            "DELETE FROM `twitch` WHERE `twitch`.`server` = ? AND `twitch`.`user_id` = ?", 
            ctx.guild.id, int_user_id, with_commit=True)

        if check:
            await ctx.answer(ctx.lang["twitch"]["unsub"].format(
                self.embed_url(user)))
        else:
            await ctx.answer(ctx.lang["twitch"]["sub"].format(
                self.embed_url(user)))

            await self.bot.db.execute("INSERT INTO `twitch` VALUES (?, ?)",
                ctx.guild.id, int_user_id, with_commit=True)

    @twitch.command(name="channel")
    @is_commander()
    async def twitch_channel(self, ctx, channel: Optional[discord.TextChannel]=None):
        set_channel = await self.alerts.get_anonse_channel(ctx.guild)

        if channel is None:
            if set_channel is None:
                await ctx.answer(ctx.lang["twitch"]["no_channel"])
            else:
                await ctx.answer(ctx.lang["twitch"]["now_channel"].format(set_channel.mention))
        else:
            if channel == set_channel:
                await ctx.answer(ctx.lang["twitch"]["channel_deleted"].format(channel.mention))
                await self.bot.db.execute("DELETE FROM `twitch_channels` WHERE `twitch_channels`.`server` = ?",
                    ctx.guild.id, with_commit=True)
            else:
                await ctx.answer(ctx.lang["twitch"]["new_channel"].format(channel.mention))
                await self.alerts.set_anonse_channel(channel)


def setup(bot):
    bot.add_cog(TwitchAlerts(bot))
