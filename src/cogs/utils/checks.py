from discord.ext.commands import check as cmd_check

async def none_guild(ctx):
    return ctx.guild and ctx.guild is not None


def is_owner():
    
    def predicate(ctx):
        return ctx.message.author.id in ctx.bot.config.owners

    return cmd_check(predicate)