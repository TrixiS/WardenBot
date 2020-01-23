import discord

from discord.ext import commands
from .utils.constants import EconomyConstants
from .utils.converters import Uint

# TODO (#2):
#   make safe money append (db int bounds)

class Account:

    def __init__(self, bot, member, cash, bank):
        self.bot = bot
        self.member = member
        self.cash = cash
        self.bank = bank

    def __format__(self, format_spec):
        fmt = "{:3,}"

        if format_spec == "bank":
            return fmt.format(self.bank)
        elif format_spec == "cash":
            return fmt.format(self.cash)
        elif format_spec == "sum":
            return fmt.format(self.sum)

    @property
    def sum(self):
        return self.bank + self.cash

    async def save(self):
        check = await self.bot.db.execute("UPDATE `money` SET `cash` = ?, `bank` = ? WHERE `money`.`server` = ? AND `money`.`member` = ?",
            self.cash, self.bank, self.member.guild.id, self.member.id, with_commit=True)

        if not check:
            await self.bot.db.execute("INSERT INTO `money` VALUES (?, ?, ?, ?)",
                self.member.guild.id, self.member.id, self.cash, self.bank, with_commit=True)

    async def delete(self) -> None:
        await self.bot.db.execute("DELETE FROM `money` WHERE `money`.`server` = ? AND `money`.`member` = ?",
            self.member.guild.id, self.member.id, with_commit=True)


class _Economy:

    def __init__(self, bot):
        self.bot = bot

    async def get_money(self, member):
        money = await self.bot.db.execute("SELECT `cash`, `bank` FROM `money` WHERE `money`.`server` = ? AND `money`.`member` = ?",
            member.guild.id, member.id)

        if money is None:
            cash, bank = 0, 0
        else:
            cash, bank = money

        return Account(self.bot, member, cash, bank)

    async def get_currency(self, guild):
        currency = await self.bot.db.execute("SELECT `symbol` FROM `currency` WHERE `currency`.`server` = ?",
            guild.id)

        if currency is not None and currency.isalpha():
            return currency
        else:
            return EconomyConstants.DEFAULT_SYMBOL

        emoji = self.bot.get_emoji(int(currency))

        if emoji is not None:
            return str(emoji)
        
        return EconomyConstants.DEFAULT_SYMBOL


class EconomyCommand(commands.Command):
    pass


class Economy(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.eco = _Economy(bot)

    # make place showing in the footer
    @commands.command(aliases=["bal", "money"], cls=EconomyCommand)
    async def balance(self, ctx, *, member: discord.Member=None):
        account = await self.eco.get_money(member or ctx.author)

        em = discord.Embed(colour=ctx.color)
        em.set_author(name=account.member.name, icon_url=account.member.avatar_url)
        em.add_field(name=ctx.lang["economy"]["cash"], value="{}**{:cash}**".format(ctx.currency, account))
        em.add_field(name=ctx.lang["economy"]["bank"], value="{}**{:bank}**".format(ctx.currency, account))
        em.add_field(name=ctx.lang["shared"]["sum"], value="{}**{:sum}**".format(ctx.currency, account))

        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Economy(bot))

