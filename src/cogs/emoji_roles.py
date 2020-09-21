import discord
import typing
import emoji

from discord.ext import commands

from .utils.checks import is_commander, bot_has_permissions
from .utils.converters import EqualRole


class AllEmojiConverter(commands.EmojiConverter):

    async def convert(self, ctx, arg):
        arg = arg.lower()

        try:
            return await super().convert(ctx, arg)
        except Exception:
            pass

        if arg not in emoji.UNICODE_EMOJI:
            raise commands.BadArgument(ctx.lang["emroles"]["incorrect_emoji"])

        return discord.PartialEmoji(name=arg)


class EmojiRoles(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def get_reaction_role(self, message, emoji):
        emoji_id = emoji.id or str(emoji)
        emoji_role_id = await self.bot.db.execute(
            """
            SELECT `role_id`
            FROM `emoji_roles`
            WHERE `guild_id` = ? AND `emoji_id` = ? AND `message_id` = ?
            """,
            message.guild.id, str(emoji_id), message.id
        )

        return message.guild.get_role(emoji_role_id)

    def payload_to_data(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id) if guild else None
        member = guild.get_member(payload.user_id) if guild else None

        return {
            "guild": guild,
            "channel": channel,
            "member": member,
            "emoji": payload.emoji,
            "message_id": payload.message_id
        }

    async def process_payload(self, payload):
        if payload.guild_id is None:
            return

        data = self.payload_to_data(payload)

        if data["guild"] is None or data["member"] is None or data["member"].bot:
            return

        message = discord.Object(data["message_id"])
        setattr(message, "guild", data["guild"])

        emoji_role = await self.get_reaction_role(
            message,
            data["emoji"]
        )

        if emoji_role is None:
            return

        if data["channel"] is not None:
            perms = data["channel"].permissions_for(data["guild"].me)
        else:
            perms = data["guild"].me.guild_permissions

        if not perms.manage_roles:
            return

        if payload.event_type == "REACTION_ADD":
            if emoji_role not in data["member"].roles:
                await data["member"].add_roles(emoji_role)
        else:
            if emoji_role in data["member"].roles:
                await data["member"].remove_roles(emoji_role)

    @bot_has_permissions(manage_messages=True, manage_roles=True)
    @is_commander()
    @commands.group(invoke_without_command=True)
    async def emojirole(
        self, ctx,
        message: commands.MessageConverter,
        emoji: AllEmojiConverter,
        *, role: typing.Optional[EqualRole]
    ):
        emoji_id = emoji.id or str(emoji)
        emoji_role = await self.get_reaction_role(message, emoji)

        if role is None:
            if emoji_role is None:
                return await ctx.answer(ctx.lang["emroles"]["no_role"].format(str(emoji)))
            else:
                return await ctx.answer(ctx.lang["emroles"]["role"].format(
                    str(emoji), emoji_role.mention
                ))

        if emoji_role is None:
            await self.bot.db.execute(
                "INSERT INTO `emoji_roles` VALUES (?, ?, ?, ?)",
                ctx.guild.id,
                message.id,
                role.id,
                str(emoji_id),
                with_commit=True
            )
        else:
            await self.bot.db.execute(
                """
                UPDATE `emoji_roles`
                SET `role_id` = ?
                WHERE `guild_id` = ? AND `message_id` = ? WHERE `emoji_id` = ?
                """,
                role.id,
                ctx.guild.id,
                message.id,
                str(emoji_id),
                with_commit=True
            )

        await message.add_reaction(emoji)
        await ctx.answer(ctx.lang["emroles"]["role"].format(str(emoji), role.mention))

    @is_commander()
    @emojirole.command(name="remove")
    async def emojirole_remove(
        self, ctx,
        message: commands.MessageConverter,
        emoji: AllEmojiConverter
    ):
        emoji_role = await self.get_reaction_role(message, emoji)

        if emoji_role is None:
            return await ctx.answer(ctx.lang["emroles"]["no_role"].format(str(emoji)))

        await ctx.answer(ctx.lang["emroles"]["role_removed"].format(
            emoji_role.mention, str(emoji)
        ))

        await self.bot.db.execute(
            "DELETE FROM `emoji_roles` WHERE `guild_id` = ? AND `message_id` = ? AND `emoji_id` = ?",
            ctx.guild.id, message.id, str(emoji.id or emoji),
            with_commit=True
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.process_payload(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.process_payload(payload)


def setup(bot):
    bot.add_cog(EmojiRoles(bot))
