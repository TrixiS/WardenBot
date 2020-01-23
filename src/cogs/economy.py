import discord

from discord.ext import commands
from .utils.constants import EconomyConstants
from .utils.converters import Uint
from .utils.checks import is_commander
from enum import Enum

# TODO (#2):
#   make safe money append (db int bounds)

class Account:

    def __init__(self, bot, member, cash, bank):
        self.bot = bot
        self.member = member
        self.cash = cash
        self.bank = bank

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


class MoneyType(Enum):

    cash = 0
    bank = 1


class MoneyTypeConverter(commands.Converter):

    async def convert(self, ctx, argument):
        argument = argument.lower()

        if argument == MoneyType.Cash.name:
            return MoneyType.Cash
        
        if argument == MoneyType.Bank.name:
            return MoneyType.Bank

        raise commands.BadArgument(ctx.lang["economy"]["incorrect_money_type"])


class Economy(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.eco = _Economy(bot)

    def currency_fmt(self, currency, amount):
        return f"{}**{:3,}**".format(currency, amount)

    # make place showing in the footer
    @commands.command(aliases=["bal", "money"], cls=EconomyCommand)
    async def balance(self, ctx, *, member: discord.Member=None):
        account = await self.eco.get_money(member or ctx.author)

        em = discord.Embed(colour=ctx.color)
        em.set_author(name=account.member.name, icon_url=account.member.avatar_url)
        em.add_field(name=ctx.lang["economy"]["cash"], value=self.currency_fmt(ctx.currency, account.cash))
        em.add_field(name=ctx.lang["economy"]["bank"], value=self.currency_fmt(ctx.currency, amount.bank))
        em.add_field(name=ctx.lang["shared"]["sum"], value=self.currency_fmt(ctx.currency, amount.sum))

        await ctx.send(embed=em)

    @commands.command(aliases=["dep"], cls=EconomyCommand)
    async def deposit(self, ctx, amount: Uint(include_zero=False)=None):
        account = await self.eco.get_money(ctx.author)

        if amount is None:
            amount = account.cash

        if amount > account.cash:
            return await ctx.answer(ctx.lang["economy"]["not_enough_cash"])

        account.cash -= amount
        account.bank += amount

        await account.save()
        await ctx.answer(ctx.lang["economy"]["deposited"].format())


def setup(bot):
    bot.add_cog(Economy(bot))

