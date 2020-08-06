import discord
import datetime as dt
import logging

from discord.ext import commands, tasks
from typing import Optional
from multidict import MultiDict

from .utils.checks import is_commander
from .utils.constants import EmbedConstants
from .utils.converters import Index, IndexConverter
from .utils.models import Pages


class TwitchAPIToken:

    def __init__(self, api, token, expr_date):
        self.api = api
        self.token = token
        self.exrp_date = expr_date

    def __str__(self):
        return self.token

    @property
    def expired(self):
        return dt.datetime.utcnow() >= self.exrp_date


class TwitchEntity:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class TwitchAPI:

    base_api_url = "https://api.twitch.tv/helix/"
    oauth_url = "https://id.twitch.tv/oauth2/token"

    def __init__(self, bot):
        self.bot = bot
        self.client_id = bot.config.twitch_client_id
        self.client_secret = bot.config.twitch_client_secret
        self.token = None

    async def get_api_token(self):
        if self.token is not None and not self.token.expired:
            return self.token

        req_params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        async with self.bot.session.post(
                self.oauth_url,
                params=req_params) as r:
            data = await r.json()

        self.token = TwitchAPIToken(
            self, data["access_token"], 
            dt.datetime.utcnow() + dt.timedelta(seconds=data["expires_in"]))

        return self.token

    async def req(self, api_method, **params):
        token = await self.get_api_token()

        req_headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {str(token)}",
        }

        params_values = []

        for key, value in params.items():
            if isinstance(value, (list, tuple)):
                for item in value:
                    params_values.append((key, item))
            else:
                params_values.append((key, value))

        params = MultiDict(params_values)

        async with self.bot.session.get(
                self.base_api_url + api_method,
                params=params,
                headers=req_headers) as r:
            data = (await r.json())["data"]

            if len(data) == 0:
                return
            
            return tuple(TwitchEntity(**entity) for entity in data)


class TwitchChannel(commands.Converter):

    async def convert(self, ctx, arg):
        channel = await ctx.command.cog.get_twitch_channel(arg.lower())

        if channel is None or len(channel) == 0:
            raise commands.BadArgument(ctx.lang["twitch"]["invalid_user"])

        return channel[0]


class TwitchAlerts(commands.Cog):

    base_url = "https://twitch.tv/"

    def __init__(self, bot):
        self.bot = bot
        self.api = TwitchAPI(bot)
        self.latest_iter_time = dt.datetime.utcnow()
        self.anonse.start()

    def cog_unload(self):
        self.anonse.stop()

    def embed_url(self, user):
        name = user.display_name.capitalize()
        return f"[{name}]({self.base_url}{name})"

    @tasks.loop(minutes=2, count=None)
    async def anonse(self):
        anonses = await self.get_anonses()

        if anonses is None or len(anonses) == 0:
            return

        guild_data = {}
        all_guilds = set()

        for guilds in map(lambda x: x[1], anonses):
            all_guilds.update(guilds)

        for guild in all_guilds:
            data = await self.get_guild_data(guild)
            
            if data[2] is not None:
                channel_perms = data[2].permissions_for(guild.me)

                if channel_perms.send_messages and channel_perms.embed_links:
                    guild_data[guild] = data

        for stream, guilds in anonses:
            for guild in filter(lambda g: g in guild_data, guilds):
                self.bot.loop.create_task(self.send_alert(guild_data[guild], stream))

    async def send_alert(self, data, stream):
        lang, color, channel = data
        login = stream.user_name.lower()
        big_thumb_url = f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{login}-640x360.jpg"
        game = await self.api.req("games", id=stream.game_id, first=1)
        user = await self.api.req("users", id=stream.user_id, first=1)

        em = discord.Embed(
            description=f"[{stream.title}](https://twitch.tv/{login}/)", 
            colour=color)

        em.add_field(name=lang["twitch"]["viewers"], value=stream.viewer_count)
        em.add_field(name=lang["twitch"]["game"], value=game[0].name)
        em.set_author(name=stream.user_name.capitalize(), icon_url=user[0].profile_image_url)
        em.set_image(url=big_thumb_url)
        em.set_thumbnail(url=stream.thumbnail_url)

        await channel.send(embed=em)

    async def get_guild_data(self, guild):
        lang = await self.bot.get_lang(guild)
        color = await self.bot.get_color(guild)
        anonse_channel = await self.get_anonse_channel(guild)
        return lang, color, anonse_channel            

    async def get_anonses(self):
        ids = await self.bot.db.execute(
            "SELECT `user_id` FROM `twitch` GROUP BY `user_id` HAVING COUNT(*) >= 1",
            fetch_all=True)
        
        if ids is None or len(ids) == 0:
            return

        subscriptions = []
        streams = await self.get_streams(tuple(map(lambda x: x[0], ids)))

        for stream in filter(lambda s: s is not None and s.type == "live", streams):
            stream_started = dt.datetime.strptime(
                stream.started_at, r"%Y-%m-%dT%H:%M:%Sz")

            if self.latest_iter_time > stream_started:
                continue

            subscribed_guilds = await self.get_subscribed_guilds(
                int(stream.user_id))
            
            if len(subscribed_guilds):
                subscriptions.append((stream, subscribed_guilds))

        self.latest_iter_time = dt.datetime.utcnow()
        return subscriptions

    async def get_subscribed_guilds(self, user_id):
        check = await self.bot.db.execute(
            "SELECT `server` FROM `twitch` WHERE `twitch`.`user_id` = ?",
            user_id, fetch_all=True)

        guilds = []

        for row in check:
            guild = self.bot.get_guild(row[0])

            if guild is None:
                continue

            guilds.append(guild) 

        return guilds

    async def get_anonse_channel(self, guild):
        channel_id = await self.bot.db.execute(
            "SELECT `channel` FROM `twitch_channels` WHERE `twitch_channels`.`server` = ?",
            guild.id)

        if channel_id is None:
            return

        return guild.get_channel(channel_id)

    async def set_anonse_channel(self, new_channel):
        check = await self.bot.db.execute(
            "UPDATE `twitch_channels` SET `channel` = ? WHERE `twitch_channels`.`server` = ?",
            new_channel.id, new_channel.guild.id,
            with_commit=True)

        if not check:
            await self.bot.db.execute(
                "INSERT INTO `twitch_channels` VALUES (?, ?)",
                new_channel.guild.id, new_channel.id,
                with_commit=True)

    async def get_twitch_channel(self, username):
        return await self.api.req(
            "search/channels",
            query=username,
            first=1)

    def split_params(self, values, offset=100):
        offset_down = 0
        offset_up = offset
        result = []

        while True:
            splitted = values[offset_down:offset_up]

            if splitted:
                result.append(splitted)
            else:
                break

            offset_down += offset
            offset_up += offset

        return result

    async def get_users(self, ids):
        result = []

        for ids in self.split_params(ids):
            searched = await self.api.req(
                "users",
                id=list(ids),
                first=100)

            if searched:
                result.extend(searched)

        return result

    async def get_streams(self, ids):
        result = []

        for ids in self.split_params(ids):
            searched = await self.api.req(
                "streams",
                user_id=list(ids),
                first=100)

            if searched:
                result.extend(searched)

        return result

    async def get_subscriptions(self, guild):
        data = await self.bot.db.execute(
            "SELECT `user_id` FROM `twitch` WHERE `server` = ?",
            guild.id, fetch_all=True)

        ids = tuple(x[0] for x in data)
        return await self.get_users(ids)

    @commands.group(invoke_without_command=True)
    async def twitch(self, ctx, page: IndexConverter = Index(0)):
        subs = await self.get_subscriptions(ctx.guild)

        if len(subs) == 0:
            return await ctx.answer(ctx.lang["twitch"]["no_subs"])

        subs = map(self.embed_url, subs)
        sep = ', '
        sep_len = len(sep)
        pages_content = [[]]

        for sub in subs:
            if (sum(map(len, sub)) + len(sub) * sep_len + 
                    len(sub) + sep_len >= EmbedConstants.DESC_MAX_LEN):
                pages_content.append([sub])
            else:
                pages_content[-1].append(sub)

        if len(pages_content) < 2:
            return await ctx.answer(sep.join(pages_content[0]))

        pages = Pages(ctx, [{
                "title": ctx.lang["twitch"]["subs_title"],
                "description": sep.join(page)
            }
            for page in pages_content
        ])

        await pages.paginate()

    @is_commander()
    @twitch.command(name="subscribe", aliases=["sub"])
    async def twitch_subscribe(self, ctx, channel: TwitchChannel):
        check = await self.bot.db.execute(
            "SELECT 1 FROM `twitch` WHERE `server` = ? AND `user_id` = ?",
            ctx.guild.id, int(channel.id))

        if check:
            return await ctx.answer(ctx.lang["twitch"]["already_subscribed"].format(
                self.embed_url(channel)))

        await self.bot.db.execute(
            "INSERT INTO `twitch` VALUES (?, ?)",
            ctx.guild.id, int(channel.id),
            with_commit=True)

        await ctx.answer(ctx.lang["twitch"]["sub"].format(
            self.embed_url(channel)))

    @is_commander()
    @twitch.command(name="unsubscribe", aliases=["unsub"])
    async def twitch_unsubscribe(self, ctx, channel: TwitchChannel):
        check = await self.bot.db.execute(
            "DELETE FROM `twitch` WHERE `server` = ? AND `user_id` = ?",
            ctx.guild.id, int(channel.id),
            with_commit=True)

        if check:
            await ctx.answer(ctx.lang["twitch"]["unsub"].format(
                self.embed_url(channel)))
        else:
            await ctx.answer(ctx.lang["twitch"]["not_subscribed"].format(
                self.embed_url(channel)))

    @is_commander()
    @twitch.command(name="channel")
    async def twitch_channel(self, ctx, *, channel: Optional[discord.TextChannel]):
        set_channel = await self.get_anonse_channel(ctx.guild)

        if channel is None:
            if set_channel is None:
                await ctx.answer(ctx.lang["twitch"]["no_channel"])
            else:
                await ctx.answer(ctx.lang["twitch"]["now_channel"].format(set_channel.mention))
        else:
            if channel == set_channel:
                await ctx.answer(ctx.lang["twitch"]["channel_deleted"].format(channel.mention))
                await self.bot.db.execute(
                    "DELETE FROM `twitch_channels` WHERE `twitch_channels`.`server` = ?",
                    ctx.guild.id, with_commit=True)
            else:
                await ctx.answer(ctx.lang["twitch"]["new_channel"].format(channel.mention))
                await self.set_anonse_channel(channel)


def setup(bot):
    bot.add_cog(TwitchAlerts(bot))
