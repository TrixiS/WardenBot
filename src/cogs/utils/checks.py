from discord.ext import commands
from .strings import markdown


async def check_permissions(ctx, perms, *, check=all):
    if ctx.bot.is_owner(ctx.author):
        return True

    resolved = ctx.message.channel.permissions_for(ctx.author)

    return check(getattr(resolved, name, None) == value for name, value in perms.items())


async def check_bot_permissions(ctx, perms, *, check=all):
    resolved = ctx.message.channel.permissions_for(ctx.guild.me)

    return check(getattr(resolved, name, None) == value for name, value in perms.items())


def bot_has_permissions(*, check=all, **perms):

    async def predicate(ctx):
        if (await check_bot_permissions(ctx, perms, check=check)):
            return True

        raise commands.CheckFailure(ctx.lang["errors"]["bot_hasnt_perms"].format(
            ctx.bot.user.mention, 
            ', '.join(markdown(k.upper(), '**') for k in perms.keys())))

    return commands.check(predicate)


def has_permissions(*, check=all, **perms):

    async def predicate(ctx):
        if (await check_permissions(ctx, perms, check=check)):
            return True

        raise commands.CheckFailure(ctx.lang["errors"]["you_hasnt_perms"].format(
            ', '.join(markdown(k.upper(), '**') for k in perms.keys())))

    return commands.check(predicate)


def is_owner():
    
    def predicate(ctx):
        if not ctx.bot.is_owner(ctx.author):
            raise commands.CheckFailure(ctx.lang["errors"]["owner_only"])

        return True

    return commands.check(predicate)


def is_commander(*, check=all, **perms):
    if not len(perms):
        perms["manage_guild"] = True

    async def predicate(ctx):
        if ctx.bot.is_owner(ctx.author):
            return True

        role_id = await ctx.bot.db.execute("SELECT `role` FROM `commanders` WHERE `commanders`.`server` = ?", 
            ctx.guild.id)

        if role_id is not None:
            role = ctx.message.guild.get_role(role_id) 

            if role is not None and role in ctx.message.author.roles:
                return True

        if (await check_permissions(ctx, perms, check=check)):
            return True

        raise commands.CheckFailure(ctx.lang["errors"]["you_must_be_commander"])

    return commands.check(predicate)


def is_moderator(*, check=all, **perms):

    async def predicate(ctx):
        if ctx.bot.is_owner(ctx.author):
            return True

        role_id = await ctx.bot.db.execute("SELECT `role` FROM `moderators` WHERE `moderators`.`server` = ?", 
            ctx.guild.id)

        if role_id is not None:
            role = ctx.message.guild.get_role(role_id)

            if role is not None and role in ctx.message.author.roles:
                return True

        if (await check_permissions(ctx, perms, check=check)):
            return True

        raise commands.CheckFailure(ctx.lang["errors"]["you_must_be_moderator"])

    return commands.check(predicate)


def only_in_guilds(*guilds):

    async def predicate(ctx):
        return ctx.guild.id in guilds

    return predicate


def disabled_command():

    def predicate(ctx):
        if not hasattr(ctx.command, "disabled_in"):
            setattr(ctx.command, "disabled_in", {ctx.guild.id: True})
            raise commands.DisabledCommand()
        
        if ctx.guild.id not in ctx.command.disabled_in:
            raise commands.DisabledCommand()

        return True

    return commands.check(predicate)
