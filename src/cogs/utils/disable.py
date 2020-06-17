from discord.ext import commands


def set_disabled(command):
    if not hasattr(command, "disabled_in"):
        setattr(command, "disabled_in", {})


async def set_disable_state(ctx, command, state):
    return await ctx.bot.db.execute(
        "INSERT INTO `disable` VALUES (?, ?, ?)",
        ctx.guild.id, command.qualified_name, state,
        with_commit=True)


def disabled_command():

    async def predicate(ctx):
        if ctx.bot.is_owner(ctx.author):
            return True

        set_disabled(ctx.command)

        if ctx.guild.id not in ctx.command.disabled_in:
            ctx.command.disabled_in[ctx.guild.id] = True
            raise commands.DisabledCommand()

        set_disabled(ctx.command.cog)

        if ctx.guild.id not in ctx.commands.cog.disabled_in:
            ctx.command.cog.disabled_in[ctx.guild.id] = True
            raise commands.DisabledCommand()

        return True

    return commands.check(predicate)