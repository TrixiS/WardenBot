import discord
import datetime as dt

from discord.ext import commands, tasks
from multidict import MultiDict

from .utils.checks import bot_has_permissions, is_commander
from .utils.constants import EmbedConstants
from .utils.converters import Index, IndexConverter
from .utils.models import Pages


class TwitchAPIToken:

    def __init__(self, token, expr_date):
        self.token = token
        self.expr_date = expr_date

    def __str__(self):
        return self.token

    @property
    def expired(self):
        return dt.datetime.utcnow().timestamp() >= self.expr_date


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
            data["access_token"],
            dt.datetime.utcnow().timestamp() + int(data["expires_in"]) - 3600
        )

        return self.token

    async def req(self, api_method, method="GET", with_cursor=False, **params):
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
            elif value is not None:
                params_values.append((key, value))

        params = MultiDict(params_values)

        async with self.bot.session.request(
                method,
                self.base_api_url + api_method,
                params=params,
                headers=req_headers) as r:
            try:
                json = await r.json()
                data = json["data"]
            except Exception:
                return

            if len(data) == 0:
                return

            result = tuple(TwitchEntity(**entity) for entity in data)

            if with_cursor and "cursor" in json["pagination"] and len(json["pagination"]["cursor"]):
                setattr(result[0], "cursor", json["pagination"]["cursor"])

            return result


class TwitchChannel(commands.Converter):

    async def convert(self, ctx, arg):
        channel = await ctx.command.cog.get_twitch_channel(arg.lower())

        if channel is None or len(channel) == 0:
            raise commands.BadArgument(ctx.lang["twitch"]["invalid_user"])

        return channel[0]


class TwitchAlerts(commands.Cog):

    base_url = "https://twitch.tv/"
    sub_url = "https://api.twitch.tv/helix/streams?user_id={}"

    def __init__(self, bot):
        self.bot = bot
        self.api = TwitchAPI(bot)
        self.latest_iter_time = dt.datetime.utcnow()
        self.check_subs.start()

    def cog_unload(self):
        self.check_subs.stop()

    def embed_url(self, user, capital=False):
        name = user.display_name.capitalize() if capital else user.display_name
        return f"[{name}]({self.base_url}{name.lower()})"

    async def toggle_sub(self, user, subscribe=True):
        req_params = {
            "hub.callback": self.bot.config.twitch_webhooks_callback,
            "hub.mode": "subscribe" if subscribe else "unsubscribe",
            "hub.topic": self.sub_url.format(user.id),
            "hub.lease_seconds": 864000,
            "hub.secret": self.bot.config.twitch_webhooks_secret
        }

        await self.api.req(
            "webhooks/hub",
            method="POST",
            **req_params)

    @tasks.loop(minutes=10, count=None)
    async def check_subs(self):
        await self.bot.wait_until_ready()

        ids = await self.bot.db.execute(
            "SELECT `user_id` FROM `twitch` GROUP BY `user_id` HAVING COUNT(*) >= 1",
            fetch_all=True)

        if ids is None or len(ids) == 0:
            return

        notification_subs_ids = tuple(
            int(s.topic.split('=')[1])
            for s in await self.get_notification_subs())

        for user_id in map(lambda x: x[0], ids):
            if user_id not in notification_subs_ids:
                await self.toggle_sub(discord.Object(user_id))

    async def get_notification_subs(self):
        result = []
        cursor = None

        while True:
            searched = await self.api.req(
                "webhooks/subscriptions",
                with_cursor=True,
                first=100, after=cursor)

            if searched is None or (len(searched) and searched == tuple(result)):
                break

            if hasattr(searched[0], "cursor"):
                cursor = searched[0].cursor

            result.extend(searched)

        return result

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

    async def any_guild_subscribed(self, user):
        return bool(await self.bot.db.execute(
            "SELECT 1 FROM `twitch` WHERE `user_id` = ?",
            int(user.id)))

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
                self.embed_url(channel, capital=True)))

        if not await self.any_guild_subscribed(channel):
            await self.toggle_sub(channel)

        await self.bot.db.execute(
            "INSERT INTO `twitch` VALUES (?, ?)",
            ctx.guild.id, int(channel.id),
            with_commit=True)

        await ctx.answer(ctx.lang["twitch"]["sub"].format(
            self.embed_url(channel, capital=True)))

    @is_commander()
    @twitch.command(name="unsubscribe", aliases=["unsub"])
    async def twitch_unsubscribe(self, ctx, channel: TwitchChannel):
        check = await self.bot.db.execute(
            "DELETE FROM `twitch` WHERE `server` = ? AND `user_id` = ?",
            ctx.guild.id, int(channel.id),
            with_commit=True)

        if check:
            await ctx.answer(ctx.lang["twitch"]["unsub"].format(
                self.embed_url(channel, capital=True)))
        else:
            await ctx.answer(ctx.lang["twitch"]["not_subscribed"].format(
                self.embed_url(channel, capital=True)))

        if not await self.any_guild_subscribed(channel):
            await self.toggle_sub(channel, subscribe=False)

    @is_commander()
    @bot_has_permissions(manage_webhooks=True)
    @twitch.command(name="channel")
    async def twitch_channel(self, ctx, *, channel: discord.TextChannel):
        webhook = None
        webhook_id = await self.bot.db.execute(
            "SELECT `id` FROM `twitch_webhooks` WHERE `server` = ?",
            ctx.guild.id
        )

        if webhook_id is not None:
            guild_webhooks = await ctx.guild.webhooks()
            webhook = discord.utils.find(
                lambda x: x.id == int(webhook_id),
                guild_webhooks
            )

        webhook_channel = ctx.guild.get_channel(webhook.channel_id) if webhook else None

        if webhook is not None and webhook_channel == channel:
            return await ctx.answer(ctx.lang["twitch"]["webhook_already_set"].format(
                channel.mention
            ))

        if webhook is not None:
            await webhook.delete()

        avatar_asset = self.bot.user.avatar_url_as(
            format="png",
            size=128
        )

        new_webhook = await channel.create_webhook(
            name=ctx.lang["twitch"]["webhook_name"],
            avatar=await avatar_asset.read()
        )

        if webhook_id is None:
            await self.bot.db.execute(
                "INSERT INTO `twitch_webhooks` VALUES (?, ?, ?)",
                ctx.guild.id, str(new_webhook.id), new_webhook.token,
                with_commit=True
            )
        else:
            await self.bot.db.execute(
                "UPDATE `twitch_webhooks` SET `id` = ?, `token` = ? WHERE `server` = ?",
                str(new_webhook.id), new_webhook.token, ctx.guild.id,
                with_commit=True
            )

        await ctx.answer(ctx.lang["twitch"]["webhook_set"].format(
            channel.mention
        ))


def setup(bot):
    bot.add_cog(TwitchAlerts(bot))
