from .checks import check_bot_permissions
from discord.ext.commands import CheckFailure

class CommandDisabled(CheckFailure):
    pass


async def none_guild(ctx):
    return ctx.guild is not None


async def has_message_perms(ctx):
    return await check_bot_permissions(ctx, {"send_messages": True, "embed_links": True})


async def is_command_disabled(ctx):
    if (hasattr(ctx.command, "disabled_in") and 
            ctx.guild.id in ctx.command.disabled_in):
        raise CommandDisabled()

    return True
