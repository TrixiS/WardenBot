

def set_disabled(command):
    if not hasattr(command, "disabled_in"):
        setattr(command, "disabled_in", {})


async def set_disable_state(ctx, command, state):
    return await ctx.bot.db.execute(
        "INSERT INTO `disable` VALUES (?, ?, ?)",
        ctx.guild.id, command.qualified_name, state,
        with_commit=True)
