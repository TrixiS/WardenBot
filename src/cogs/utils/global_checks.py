from .checks import check_bot_permissions


async def none_guild(ctx):
    return ctx.guild is not None


async def has_message_perms(ctx):
    return check_bot_permissions(ctx, {"send_messages": True})
