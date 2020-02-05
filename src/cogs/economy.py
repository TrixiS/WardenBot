import discord
import logging

from discord.ext import commands, tasks
from enum import Enum
from typing import Optional, Union
from math import ceil

from .utils.cooldown import CooldownCommand, custom_cooldown
from .utils.constants import EconomyConstants, StringConstants
from .utils.converters import NotAuthor, SafeUint, IndexConverter, Index, HumanTime, CommandConverter
from .utils.checks import is_commander, has_permissions
from .utils.strings import markdown
from .utils.models import PseudoMember
from .utils.db import DbType

# TODO:
#   make SQL refactoring


class Account:

    def __init__(self, bot, member, cash=None, bank=None, saved=False):
        self.bot = bot
        self.member = member
        self.cash = cash
        self.bank = bank
        self.saved = saved

    @property
    def sum(self):
        return self.bank + self.cash

    async def save(self):
        self.cash = self.bot.db.make_safe_value(int(self.cash))
        self.bank = self.bot.db.make_safe_value(int(self.bank))

        check = await self.bot.db.execute("UPDATE `money` SET `cash` = ?, `bank` = ? WHERE `money`.`server` = ? AND `money`.`member` = ?",
            self.cash, self.bank, self.member.guild.id, self.member.id, with_commit=True)

        if not check:
            await self.bot.db.execute("INSERT INTO `money` VALUES (?, ?, ?, ?)",
                self.member.guild.id, self.member.id, self.cash, self.bank, with_commit=True)

        self.saved = True

    async def delete(self):
        await self.bot.db.execute("DELETE FROM `money` WHERE `money`.`server` = ? AND `money`.`member` = ?",
            self.member.guild.id, self.member.id, with_commit=True)


class _Economy:

    def __init__(self, bot):
        self.bot = bot

    async def get_money(self, member):
        money = await self.bot.db.execute("SELECT `cash`, `bank` FROM `money` WHERE `money`.`server` = ? AND `money`.`member` = ?",
            member.guild.id, member.id)

        if money is None:
            start = await self.bot.db.execute("SELECT `cash`, `bank` FROM `start_money` WHERE `start_money`.`server` = ?",  
                member.guild.id)

            cash, bank = start or (0, 0)
        else:
            cash, bank = money

        account = Account(self.bot, member, cash, bank, money is not None)
        
        await self.get_income(account)
        
        return account

    async def get_income(self, account):
        select_sql = """
        SELECT `income`.`amount`, `is_percentage`,
            (UNIX_TIMESTAMP() - `income`.`seen`) / `income`.`interval`
        FROM `income`
        WHERE `income`.`server` = ? AND `income`.`member` = ?
            AND `income`.`seen` + `income`.`interval` <= UNIX_TIMESTAMP()
        """

        income = await self.bot.db.execute(
            select_sql, 
            account.member.guild.id, 
            account.member.id)

        if income is None:
            return

        update_sql = """
        UPDATE `income`
        SET `seen` = UNIX_TIMESTAMP()
        WHERE `income`.`server` = ? AND `income`.`member` = ?
        """

        await self.bot.db.execute(
            update_sql,
            account.member.guild.id,
            account.member.id,
            with_commit=True)

        amount, is_percentage, ticks = income

        if is_percentage:
            account.bank += ceil(account.bank * (amount / 100)) * ticks
        else:
            account.bank += amount * ticks

        await account.save()

    async def get_place(self, member):
        all_accounts = await self.bot.db.execute("SELECT `member` FROM `money` WHERE `money`.`server` = ? AND `money`.`cash` + `money`.`bank` > 0 ORDER BY `money`.`cash` + `money`.`bank` DESC",
            member.guild.id, fetch_all=True)

        member_case = (member.id, )

        if all_accounts is None or len(all_accounts) == 0 or member_case not in all_accounts:
            return 1

        return all_accounts.index(member_case) + 1

    async def get_currency(self, guild):
        currency = await self.bot.db.execute("SELECT `symbol` FROM `currency` WHERE `currency`.`server` = ?",
            guild.id)

        emoji = self.bot.get_emoji(currency)

        if emoji is None:
            return EconomyConstants.DEFAULT_SYMBOL

        return str(emoji)


class EconomyCommand(commands.Command):
    
    async def prepare(self, ctx):
        await super().prepare(ctx)
        ctx.currency = await ctx.cog.eco.get_currency(ctx.guild)


class EconomyGroup(EconomyCommand, commands.Group):
    pass


class EconomyGame(EconomyCommand, CooldownCommand):
    pass


class MoneyType(Enum):

    cash = 0
    bank = 1


class MoneyTypeConverter(commands.Converter):

    __qualname__ = "MoneyType"

    async def convert(self, ctx, argument):
        argument = argument.lower()

        if argument == ctx.lang["economy"]["cash"].lower():
            return MoneyType.cash
        
        if argument == ctx.lang["economy"]["bank"].lower():
            return MoneyType.bank

        raise commands.BadArgument(ctx.lang["economy"]["incorrect_money_type"])


class IncomeValue:

    __slots__ = ("amount", "is_percentage")

    def __init__(self, amount, is_percentage):
        self.amount = amount
        self.is_percentage = is_percentage

    def __str__(self):
        return f"{self.amount}%" if self.is_percentage else str(self.amount)


class IncomeValueConverter(SafeUint):

    __qualname__ = "IncomeValue"

    async def convert(self, ctx, arg):
        if arg.endswith('%'):
            value = await super().convert(ctx, arg[:-1])
        else:
            value = await super().convert(ctx, arg)

        return IncomeValue(ctx.bot.db.make_safe_value(value), arg.endswith('%'))


class Economy(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.eco = _Economy(bot)

    def currency_fmt(self, currency, amount):
        return "{}**{:3,}**".format(currency, amount)

    @commands.command(aliases=["bal", "money"], cls=EconomyCommand)
    async def balance(self, ctx, *, member: Optional[discord.Member]):
        account = await self.eco.get_money(member or ctx.author)

        em = discord.Embed(colour=ctx.color)
        em.set_author(name=account.member.name, icon_url=account.member.avatar_url)
        em.add_field(name=ctx.lang["economy"]["cash"], value=self.currency_fmt(ctx.currency, account.cash))
        em.add_field(name=ctx.lang["economy"]["bank"], value=self.currency_fmt(ctx.currency, account.bank))
        em.add_field(name=ctx.lang["shared"]["sum"], value=self.currency_fmt(ctx.currency, account.sum))

        if account.sum > 0:
            if account.saved:
                place = await self.eco.get_place(account.member)
                em.set_footer(text=ctx.lang["economy"]["balance_place"].format(place))
            else:
                await account.save()

        await ctx.send(embed=em)

    @commands.command(aliases=["dep"], cls=EconomyCommand)
    async def deposit(self, ctx, amount: Optional[SafeUint]):
        account = await self.eco.get_money(ctx.author)

        if amount is None:
            amount = account.cash

        if amount > account.cash or amount == 0:
            return await ctx.answer(ctx.lang["economy"]["not_enough_cash"])

        account.cash -= amount
        account.bank += amount

        await account.save()
    
        await ctx.answer(ctx.lang["economy"]["deposited"].format(
            self.currency_fmt(ctx.currency, amount)))

    @commands.command(aliases=["with"], cls=EconomyCommand)
    async def withdraw(self, ctx, amount: Optional[SafeUint]):
        account = await self.eco.get_money(ctx.author)

        if amount is None:
            amount = account.bank

        if amount > account.bank or amount == 0:
            return await ctx.answer(ctx.lang["economy"]["not_enough_bank"])

        account.bank -= amount
        account.cash += amount

        await account.save()

        await ctx.answer(ctx.lang["economy"]["withdrew"].format(
            self.currency_fmt(ctx.currency, amount)))

    @commands.command(cls=EconomyCommand)
    async def give(self, ctx, member: NotAuthor, amount: SafeUint(include_zero=False)):
        if member == ctx.author:
            return await ctx.answer(ctx.lang["errors"]["cant_use_to_yourself"])
        
        author_account = await self.eco.get_money(ctx.author)
        
        if amount > author_account.cash:
            return await ctx.answer(ctx.lang["economy"]["not_enough_cash"])

        member_account = await self.eco.get_money(member)

        author_account.cash -= amount
        member_account.cash += amount

        await author_account.save()
        await member_account.save()

        await ctx.answer(ctx.lang["economy"]["add_money"].format(
            member.mention, self.currency_fmt(ctx.currency, amount), MoneyType.cash.name))

    @commands.command(name="add-money", cls=EconomyCommand)
    @is_commander()
    async def add_money(self, ctx, member: discord.Member, money_type: MoneyTypeConverter, amount: SafeUint):
        account = await self.eco.get_money(member)

        if money_type == MoneyType.bank:
            account.bank += amount
        elif money_type == MoneyType.cash:
            account.cash += amount

        await account.save()

        await ctx.answer(ctx.lang["economy"]["add_money"].format(
            member.mention, self.currency_fmt(ctx.currency, amount), money_type.name))

    @commands.command(name="remove-money", cls=EconomyCommand)
    @is_commander()
    async def remove_money(self, ctx, member: discord.Member, money_type: MoneyTypeConverter, amount: SafeUint):
        account = await self.eco.get_money(member)

        if money_type == MoneyType.bank:
            account.bank -= amount
        elif money_type == MoneyType.cash:
            account.cash -= amount

        await account.save()

        await ctx.answer(ctx.lang["economy"]["remove_money"].format(
            member.mention, self.currency_fmt(ctx.currency, amount), money_type.name))

    @commands.command(name="delete-money")
    @is_commander()
    async def delete_money(self, ctx, *, member: discord.Member):
        accept = await ctx.ask(ctx.lang["economy"]["really_delete?"].format(markdown(member.name, "**")),
            check=lambda m: m.content.lower() in (ctx.lang["shared"]["yes"].lower(), ctx.lang["shared"]["no"].lower()))

        if accept is None or accept == ctx.lang["shared"]["no"].lower():
            return

        account = Account(self.bot, member)

        await account.delete()

        await ctx.answer(ctx.lang["economy"]["lost_all_money"].format(
            member.mention))

    @commands.command(name="start-money", cls=EconomyCommand)
    @is_commander()
    async def start_money(self, ctx, money_type: MoneyTypeConverter, amount: SafeUint(include_zero=True)):
        check = await self.bot.db.execute("UPDATE `start_money` SET `{}` = ? WHERE `start_money`.`server` = ?".format(money_type.name),
            amount, ctx.guild.id, with_commit=True)

        if not check:
            await self.bot.db.execute("INSERT INTO `start_money` VALUES (?, ?, ?)",
                ctx.guild.id, 
                amount if money_type == MoneyType.cash else 0, 
                amount if money_type == MoneyType.bank else 0,
                with_commit=True)

        await ctx.answer(ctx.lang["economy"]["start_money_set"].format(
            self.currency_fmt(ctx.currency, amount), money_type.name))

    @commands.command(cls=EconomyCommand)
    @is_commander()
    async def currency(self, ctx, symbol: discord.Emoji):
        check = await self.bot.db.execute("UPDATE `currency` SET `symbol` = ? WHERE `currency`.`server` = ?",
            symbol.id, ctx.guild.id, with_commit=True)
        
        if not check:
            await self.bot.db.execute("INSERT INTO `currency` VALUES (?, ?)",
                ctx.guild.id, symbol.id, with_commit=True)

        await ctx.answer(ctx.lang["economy"]["new_symbol"].format(
            str(symbol), ctx.currency))

    @commands.command(aliases=["lb", "board", "top"], cls=EconomyCommand)
    async def leaderboard(self, ctx, page: Optional[IndexConverter]=Index(0)):
        if self.bot.db.db_type == DbType.SQLite:
            where = "WHERE `money`.`server` = ? AND `money_sum` > 0"
        elif self.bot.db.db_type == DbType.MySQL:
            where = "WHERE `money`.`server` = ?\nHAVING `money_sum` > 0"

        sql = f"""
        SELECT `member`, `money`.`cash` + `money`.`bank` AS `money_sum`
        FROM `money`
        {where}
        ORDER BY `money_sum` DESC 
        LIMIT ? OFFSET ?
        """

        check = await self.bot.db.execute(sql,
            ctx.guild.id, EconomyConstants.USER_PER_PAGE, 
            EconomyConstants.USER_PER_PAGE * page.value,
            fetch_all=True)

        if check is None or len(check) == 0:
            return await ctx.answer(ctx.lang["economy"]["empty_page"].format(page.humanize()))

        count = await self.bot.db.execute("SELECT COUNT(*) FROM `money` WHERE `money`.`server` = ? AND `money`.`cash` + `money`.`bank` > 0",
            ctx.guild.id)

        place = None
        description = []

        for member_id, money_sum in check:
            member = ctx.guild.get_member(member_id)
                
            if place is None:
                place = await self.eco.get_place(PseudoMember(member_id, ctx.guild))
            else:
                place += 1

            description.append("**{}**. {} {} {}".format(
                place, (member and member.mention) or ctx.lang["shared"]["left_member"],
                StringConstants.DOT_SYMBOL, self.currency_fmt(ctx.currency, money_sum)))

        em = discord.Embed(
            title=ctx.lang["economy"]["lb_title"].format(ctx.guild.name),
            description='\n'.join(description),
            colour=ctx.color)
                
        em.set_footer(text="{} {}/{}".format(
            ctx.lang["shared"]["page"], 
            page.humanize(), 
            ceil(count / EconomyConstants.USER_PER_PAGE)))

        await ctx.send(embed=em)

    @commands.command(name="economy-stats", cls=EconomyCommand)
    async def economy_stats(self, ctx):
        sql = """
        SELECT SUM(`cash`), SUM(`bank`), COUNT(*)
        FROM `money`
        WHERE `money`.`server` = ?
        """

        money = await self.bot.db.execute(sql, ctx.guild.id) or (0, 0, 0)

        em = discord.Embed(colour=ctx.color)
        em.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
        em.set_footer(text=f"{ctx.lang['economy']['accounts']} {money[2]}")

        em.add_field(
            name=ctx.lang["economy"]["cash"], 
            value=self.currency_fmt(ctx.currency, money[0]),
            inline=False)
        em.add_field(
            name=ctx.lang["economy"]["bank"],
            value=self.currency_fmt(ctx.currency, money[1]),
            inline=False)
        em.add_field(
            name=ctx.lang["shared"]["sum"], 
            value=self.currency_fmt(ctx.currency, sum(money[:2])),
            inline=False)
        
        await ctx.send(embed=em)

    @commands.command(name="economy-reset")
    @has_permissions(administrator=True)
    async def economy_reset(self, ctx):
        accept = await ctx.ask(ctx.lang["economy"]["really_reset?"].format(ctx.guild.name),
            check=lambda m: m.content.lower() in (ctx.lang["shared"]["yes"].lower(), ctx.lang["shared"]["no"].lower()))

        if accept is None or accept == ctx.lang["shared"]["no"].lower():
            return

        await self.bot.db.execute("DELETE FROM `money` WHERE `money`.`server` = ?",
            ctx.guild.id, with_commit=True)

        await ctx.answer(ctx.lang["economy"]["reset"])

    @commands.group(cls=EconomyGroup, invoke_without_command=True)
    @is_commander()
    async def income(self, ctx, *, member: discord.Member):
        sql = """
        SELECT `amount`, `is_percentage`, `interval`
        FROM `income` 
        WHERE `income`.`server` = ? AND `income`.`member` = ?
        """

        check = await self.bot.db.execute(sql, ctx.guild.id, member.id)

        if check is None:
            return await ctx.answer(ctx.lang["economy"]["no_income"].format(
                member.mention))

        value = IncomeValue(check[0], check[1])

        em = discord.Embed(
            title=ctx.lang["economy"]["income_title"].format(member.name),
            colour=ctx.color)
        
        em.set_thumbnail(url=ctx.guild.icon_url)

        em.add_field(
            name=ctx.lang["shared"]["amount"],
            value=str(value) if value.is_percentage 
                else self.currency_fmt(ctx.currency, value.amount), 
            inline=False)

        em.add_field(
            name=ctx.lang["economy"]["interval"],
            value=f"{check[2]} {ctx.lang['shared']['seconds']}",
            inline=True)

        await ctx.send(embed=em)

    @income.command(aliases=["add"], name="set", cls=EconomyCommand)
    @is_commander()
    async def income_set(self, ctx, member: discord.Member, value: IncomeValueConverter, interval: HumanTime):
        sql = """
        UPDATE `income`
        SET `amount` = ?, `interval` = ?, `is_percentage` = ?, `seen` = UNIX_TIMESTAMP()
        WHERE `income`.`server` = ? AND `income`.`member` = ?
        """

        check = await self.bot.db.execute(
            sql, value.amount, 
            interval, value.is_percentage, 
            ctx.guild.id, member.id,
            with_commit=True)

        if not check:
            await self.bot.db.execute(
                "INSERT INTO `income` VALUES (?, ?, ?, ?, ?, UNIX_TIMESTAMP())",
                ctx.guild.id, member.id,
                value.amount, value.is_percentage,
                interval, with_commit=True)

        await ctx.answer(ctx.lang["economy"]["set_income"].format(
            member.mention, str(value) if value.is_percentage 
                else self.currency_fmt(ctx.currency, value.amount)))

    @income.command(aliases=["delete"], name="remove", cls=EconomyCommand)
    @is_commander()
    async def income_remove(self, ctx, *, member: discord.Member):
        check = await self.bot.db.execute("DELETE FROM `income` WHERE `income`.`server` = ? AND `income`.`member` = ?",
            ctx.guild.id, member.id, with_commit=True)

        if check:
            await ctx.answer(ctx.lang["economy"]["income_deleted"].format(
                member.mention))
        else:
            await ctx.answer(ctx.lang["economy"]["no_income"].format(
                member.mention))


def setup(bot):
    bot.add_cog(Economy(bot))

