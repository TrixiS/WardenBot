from discord.ext.commands import check as cmd_check


async def none_guild(ctx):
    return ctx.guild and ctx.guild is not None


async def check_permissions(ctx, perms, *, check=all):
    if ctx.author.id in ctx.bot.config.owners:
        return True

    resolved = ctx.message.channel.permissions_for(ctx.author)

    return check(getattr(resolved, name, None) == value for name, value in perms.items())


def has_permissions(*, check=all, **perms):

    async def predicate(ctx):
        return await check_permissions(ctx, perms, check=check)

    return cmd_check(predicate)


def is_owner():
    
    def predicate(ctx):
        return ctx.message.author.id in ctx.bot.config.owners

    return cmd_check(predicate)


def is_commander(*, check=all, **perms):
    if not len(perms):
        perms["manage_guild"] = True

    async def predicate(ctx):
        check = await ctx.bot.db.execute("SELECT `role` FROM `commanders` WHERE `commanders`.`server` = ?", 
            ctx.guild.id)

        if check is not None:
            role = ctx.message.guild.get_role(check[0]) 

            if role is not None and role in ctx.message.author.roles:
                return True

        return await check_permissions(ctx, perms, check=check)

    return cmd_check(predicate)


def is_moderator(*, check=all, **perms):

    async def predicate(ctx):
        check = await ctx.bot.db.execute("SELECT `role` FROM `moderators` WHERE `moderators`.`server` = ?", 
            ctx.guild.id)

        if check is not None:
            role = ctx.message.guild.get_role(check[0])

            if role is not None and role in ctx.message.author.roles:
                return True

        return await check_permissions(ctx, perms, check=check)

    return cmd_check(predicate)