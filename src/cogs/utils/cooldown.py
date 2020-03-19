import discord
import asyncio
import datetime

from discord.ext import commands


class CooldownCommand(commands.Command):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_cooldown_buckets = []

    def current_bucket(self, ctx):
        return discord.utils.find(
            lambda x: x.guild == ctx.guild and x.user == ctx.author and x.command == ctx.command,
            self.custom_cooldown_buckets)

            
class CustomCooldownBucket:

    def __init__(self, ctx):
        self.bot = ctx.bot
        self.user = ctx.author
        self.guild = ctx.guild
        self.command = ctx.command
        self.semaphore = asyncio.Semaphore(1, loop=ctx.bot.loop)
        self.max_uses = None
        self.remaining_uses = None
        self.reset_timedelta = None
        self.reset_at = None

    def update(self, *, new_reset_seconds=None, new_max_uses=None):
        if new_max_uses is not None:
            self.max_uses = new_max_uses
            self.remaining_uses = new_max_uses
        else:
            self.remaining_uses = self.max_uses
        
        if new_reset_seconds is not None:
            self.reset_timedelta = datetime.timedelta(seconds=new_reset_seconds)
        
        self.reset_at = datetime.datetime.now() + self.reset_timedelta

    async def init(self):
        sql = """
        SELECT `max_uses`, `reset_seconds`
        FROM `cooldown`
        WHERE `cooldown`.`server` = ? AND `cooldown`.`command` = ?
        """

        bucket_info = await self.bot.db.execute(sql, 
            self.guild.id, self.command.qualified_name)

        if bucket_info is not None:
            max_uses, reset_seconds = bucket_info
        else:
            max_uses, reset_seconds = self.bot.config.default_cooldown

        self.update(new_reset_seconds=reset_seconds, new_max_uses=max_uses)

    async def use(self):
        async with self.semaphore:
            now = datetime.datetime.now()

            result = False

            if now >= self.reset_at:
                self.remaining_uses = self.max_uses
                self.reset_at = now + self.reset_timedelta

            if self.remaining_uses > 0:
                self.remaining_uses -= 1
                result = True

            return result


def custom_cooldown():

    async def predicate(ctx):
        command = ctx.command

        bucket = discord.utils.find(
            lambda b: b.guild == ctx.guild and b.user == ctx.author,
            command.custom_cooldown_buckets)

        if bucket is None:
            bucket = CustomCooldownBucket(ctx)

            await bucket.init()

            command.custom_cooldown_buckets.append(bucket)

        if not await bucket.use():
            raise commands.CheckFailure(ctx.lang["errors"]["on_cooldown"].format(
                bucket.reset_at.strftime(ctx.lang["long_date"])))
        
        return True

    return commands.check(predicate)

