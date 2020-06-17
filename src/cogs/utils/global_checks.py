from discord.ext.commands.errors import DisabledCommand
from .checks import check_bot_permissions


async def none_guild(ctx):
    return ctx.guild is not None


async def has_message_perms(ctx):
    return await check_bot_permissions(ctx, {"send_messages": True, "embed_links": True})


async def is_command_disabled(ctx):
    if ctx.bot.is_owner(ctx.author):
        return True

    if (hasattr(ctx.command, "disabled_in") and
            ctx.guild.id in ctx.command.disabled_in and
            ctx.command.disabled_in[ctx.guild.id]):
        raise DisabledCommand()

    if (hasattr(ctx.command.cog, "disabled_in") and
            ctx.guild.id in ctx.command.cog.disabled_in and
            ctx.command.cog.disabled_in[ctx.guild.id]):
        raise DisabledCommand()

    return True
