import discord
import logging
import random
import datetime as dt

from discord.ext import commands
from enum import Enum
from typing import Optional, Union
from math import ceil
from asyncio import TimeoutError
from collections import namedtuple

from .utils.cooldown import CooldownCommand, custom_cooldown
from .utils.constants import EconomyConstants, StringConstants, EmbedConstants
from .utils.converters import (NotAuthor, uint, IndexConverter, 
    Index, HumanTime, CommandConverter, EnumConverter, without_whitespace)
from .utils.checks import is_commander, has_permissions
from .utils.strings import markdown, human_choice
from .utils.models import PseudoMember, ContextFormatter
from .utils.db import DbType

# !!! TODO: the whole shop system
# TODO: fill MORE stories lists in langs
# TODO: check permissions to send messages in ctx.send

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
        update_sql = """
        UPDATE `money` 
        SET `cash` = ?, `bank` = ? 
        WHERE `money`.`server` = ? AND `money`.`member` = ?
        """

        check = await self.bot.db.execute(
            update_sql, self.cash, 
            self.bank, self.member.guild.id, 
            self.member.id, with_commit=True)

        if not check:
            await self.bot.db.execute(
                "INSERT INTO `money` VALUES (?, ?, ?, ?)",
                self.member.guild.id, self.member.id, 
                self.cash, self.bank, with_commit=True)

        self.saved = True

    async def delete(self):
        await self.bot.db.execute(
            "DELETE FROM `money` WHERE `money`.`server` = ? AND `money`.`member` = ?",
            self.member.guild.id, self.member.id, with_commit=True)


class _Economy:

    def __init__(self, bot):
        self.bot = bot

    async def get_money(self, member):
        select_money_sql = """
        SELECT `cash`, `bank` 
        FROM `money` 
        WHERE `money`.`server` = ? AND `money`.`member` = ?
        """

        money = await self.bot.db.execute(
            select_money_sql,
            member.guild.id, 
            member.id)

        if money is None:
            select_start_sql = """
            SELECT `cash`, `bank` 
            FROM `start_money` 
            WHERE `start_money`.`server` = ?
            """

            start = await self.bot.db.execute(
                select_start_sql,  
                member.guild.id)

            cash, bank = start or (0, 0)
        else:
            cash, bank = money

        account = Account(self.bot, member, cash, bank, money is not None)
        
        await self.get_income(account)
        
        return account

    async def get_income(self, account):
        if account.bank >= self.bot.db.int_max_bound:
            return 
        
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
        select_place_sql = """
        SELECT `member` 
        FROM `money` 
        WHERE `money`.`server` = ? AND `money`.`cash` + `money`.`bank` > 0 
        ORDER BY `money`.`cash` + `money`.`bank` DESC
        """

        all_accounts = await self.bot.db.execute(
            select_place_sql, member.guild.id, 
            fetch_all=True)

        member_case = (member.id, )

        if all_accounts is None or len(all_accounts) == 0 or member_case not in all_accounts:
            return 1

        return all_accounts.index(member_case) + 1

    async def get_currency(self, guild):
        currency = await self.bot.db.execute(
            "SELECT `symbol` FROM `currency` WHERE `currency`.`server` = ?",
            guild.id)

        emoji = self.bot.get_emoji(currency)

        if emoji is None:
            return EconomyConstants.DEFAULT_SYMBOL

        return str(emoji)

    async def get_chance(self, guild, command):
        select_sql = """
        SELECT `chance`
        FROM `chances`
        WHERE `chances`.`server` = ? AND `chances`.`command` = ?
        """

        current_chance = await self.bot.db.execute(
            select_sql, guild.id, command.qualified_name)

        if current_chance is None:
            current_chance = self.bot.config.default_chances.get(
                command.qualified_name, 50)

        return current_chance

    async def get_game_config(self, ctx, command=None):
        config_select_sql = """
        SELECT `chance`, `reward`
        FROM `game_config`
        WHERE `game_config`.`server` = ? AND `game_config`.`command` = ?
        """

        story_select_sql = """
        SELECT `id`, `text` FROM `story`
        WHERE `story`.`server` = ? AND `story`.`lang` = ? 
            AND `story`.`type` = ? AND `story`.`result_type` = ?
        ORDER BY RAND() 
        LIMIT 1
        """

        if command is None:
            command = ctx.command

        game_config = await self.bot.db.execute(
            config_select_sql, ctx.guild.id, 
            command.qualified_name)
        
        config = EconomyGameConfig(*(game_config or self.bot.config.default_game_config))

        if isinstance(command, StoryGame):
            story = await self.bot.db.execute(
                story_select_sql, ctx.guild.id, 
                ctx.lang["lang_code"], 
                command.qualified_name,
                config.game_result.value)

            config.story = story or (None, random.choice(
                ctx.lang["economy"]["stories"][command.qualified_name][config.game_result.name]))
        else:
            config.story = None

        return config

    async def edit_game_config(self, guild, command, *, chance=None, reward=None):
        if chance is None and reward is None:
            return

        update_sql = """
        UPDATE `game_config` 
        {} 
        WHERE `game_config`.`server` = ? AND `game_config`.`command` = ?
        """

        if chance is not None and reward is not None:
            check = await self.bot.db.execute(
                update_sql.format("SET `reward` = ?, `chance` = ?"),
                reward, chance, guild.id, command.qualified_name,
                with_commit=True)
        elif chance is not None:
            check = await self.bot.db.execute(
                update_sql.format("SET `chance` = ?"),
                chance, guild.id, command.qualified_name,
                with_commit=True)
        elif reward is not None:
            check = await self.bot.db.execute(
                update_sql.format("SET `reward` = ?"),
                reward, guild.id, command.qualified_name,
                with_commit=True)

        if not check:
            await self.bot.db.execute(
                "INSERT INTO `game_config` VALUES (?, ?, ?, ?)",
                guild.id, command.qualified_name,
                chance or self.bot.config.default_game_config[0],
                reward or self.bot.config.default_game_config[1])

    async def get_item(self, guild, name):
        select_sql = """
        SELECT `author`, `buy_count`, {}  
        FROM `shop_items`
        WHERE `shop_items`.`server` = ? AND `shop_items`.`name` = ?
        """
        
        to_select = ', '.join(markdown(prop, '`') for prop in ShopItem.properties.keys())
        check = await self.bot.db.execute(select_sql.format(to_select), guild.id, name)

        if check is None:
            return

        check = list(check)
        check[0] = guild.get_member(check[0])
        check[5] = guild.get_role(check[5])
        check[7] = EnumConverter.convert_value(MessageType, check[7]).name.upper()

        return ShopItem(guild, *check)


class MessageType(Enum):

    dm = 0
    guild = 1


class ShopItem:

    properties = {
        "name": without_whitespace(),
        "price": uint(),
        "description": without_whitespace(),
        "role": commands.RoleConverter(),
        "stock": uint(include_zero=True),
        "message_type": EnumConverter(MessageType),
        "message": commands.clean_content()
    }

    def __init__(self, guild, author, buy_count, *args):
        self.guild = guild
        self.author = author
        self.buy_count = buy_count

        fields_names = tuple(self.properties.keys())
        for i, arg in enumerate(args):
            setattr(self, fields_names[i], arg)


class EconomyGameConfig:

    def __init__(self, chance, reward):
        self.chance = chance
        self.reward = reward
        self.rolled_chance = random.randint(1, 100)
        self.rolled_reward = random.randint(1, reward)
        
        if self.rolled_chance <= chance:
            self.game_result = GameResult.success
        else:
            self.game_result = GameResult.fail


class EconomyCommand(commands.Command):
    
    async def invoke(self, ctx):
        ctx.currency = await ctx.cog.eco.get_currency(ctx.guild)
        await super().invoke(ctx)


class EconomyGroup(EconomyCommand, commands.Group):
    pass


class EconomyGame(EconomyCommand, CooldownCommand):
    
    async def invoke(self, ctx):
        ctx.account = await self.cog.eco.get_money(ctx.author)
        await super().invoke(ctx)


class StoryGame(EconomyGame):
    
    async def invoke(self, ctx):
        ctx.game_config = await self.cog.eco.get_game_config(ctx)
        await super().invoke(ctx)

    async def use(self, ctx):
        formatter = ContextFormatter(
            member=ctx.author,
            guild=ctx.guild)

        em = discord.Embed(
            description=formatter.format(
                ctx.game_config.story[1].replace(r"{money}", self.cog.currency_fmt(
                    ctx.currency,
                    ctx.game_config.rolled_reward))),
            colour=ctx.color)

        em.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        if ctx.game_config.story[0] is not None:
            em.set_footer(text=f"ID({ctx.game_config.story[0]})")

        await ctx.send(embed=em)


class MoneyType(Enum):

    cash = 0
    bank = 1


class GameResult(Enum):

    fail = 0
    success = 1


class GameResultConverter(EnumConverter):

    __qualname__ = "GameResult"

    def __init__(self):
        super().__init__(GameResult)


class MoneyTypeConverter(EnumConverter):

    __qualname__ = "MoneyType"

    def __init__(self):
        super().__init__(MoneyType)


class IncomeValue:

    __slots__ = ("amount", "is_percentage")

    def __init__(self, amount, is_percentage):
        self.amount = amount
        self.is_percentage = is_percentage

    def __str__(self):
        return f"{self.amount}%" if self.is_percentage else str(self.amount)


class IncomeValueConverter(uint):

    __qualname__ = "IncomeValue"

    async def convert(self, ctx, arg):
        if arg.endswith('%'):
            value = await super().convert(ctx, arg[:-1])
        else:
            value = await super().convert(ctx, arg)

        return IncomeValue(value, arg.endswith('%'))


class BJCard:

    __slots__ = ("emoji", "value")

    def __init__(self, emoji, value):
        self.emoji = emoji
        self.value = value


class BJHand:

    def __init__(self, cards):
        self.cards = cards

    @property
    def score(self):
        total_score = sum(map(lambda x: x.value, self.cards))

        for card in filter(lambda x: x.value == 11, self.cards):
            if total_score <= 21:
                break

            total_score -= 10

        return total_score


class BJDeck:

    def __init__(self, back, cards, multiply):
        self.back = back
        self.cards = cards * multiply

    def make_hand(self, amount_of_cards):
        return BJHand(list(
            self.get_card() for _ in range(amount_of_cards)))

    def get_card(self):
        card = random.choice(self.cards)
        self.cards.remove(card)
        return BJCard(*card)


class BJShuffle:

    def __init__(self, ctx, embed, deck):
        self.ctx = ctx
        self.embed = embed
        self.deck = deck
        self.player_hand = self.deck.make_hand(2)
        self.dealer_hand = self.deck.make_hand(2)

    @property
    def closed(self):
        return self.player_hand.score >= 21 or self.dealer_hand.score >= 21

    def winner(self):
        player_score = self.player_hand.score
        dealer_score = self.dealer_hand.score

        if player_score != dealer_score:
            if player_score > 21 and dealer_score > 21:
                return None

            if player_score > 21:
                return self.ctx.bot.user
            elif dealer_score > 21:
                return self.ctx.author

            if player_score > dealer_score:
                return self.ctx.author
            else:
                return self.ctx.bot.user
        else:
            return None

    def player_draw_card(self):
        self.player_hand.cards.append(self.deck.get_card())

        self.embed.set_field_at(
            0, 
            name=self.embed.fields[0].name, 
            value=self.embed.fields[0].value + self.player_hand.cards[-1].emoji)

    def dealer_draw_card(self):
        self.dealer_hand.cards.append(self.deck.get_card())

        self.embed.set_field_at(
            1,
            name=self.embed.fields[1].name,
            value=self.embed.fields[1].value + self.deck.back.emoji)


class BJAction(Enum):

    Pass = 0
    Draw = 1
    Double = 2


class Bet(uint):

    async def convert(self, ctx, arg):
        result = await super().convert(ctx, arg)
        
        if result > ctx.account.cash:
            raise commands.BadArgument(ctx.lang["economy"]["not_enough_cash"])

        return result


class Economy(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.eco = _Economy(bot)

    def currency_fmt(self, currency, amount):
        return "{}**{:3,}**".format(currency, amount)

    async def property_parse_dialogue(self, ctx, prop_name, timeout_delta):
        prop_type = ShopItem.properties[prop_name]
        timeout = dt.datetime.now() + timeout_delta
        convertered = None

        while convertered is None:
            if dt.datetime.now() >= timeout:
                return await ctx.abort()

            await ctx.send(ctx.lang["economy"]["item_message"].format(
                ctx.author.mention, 
                ctx.lang["economy"]["item_properties"][prop_name], 
                ctx.lang["shared"]["cancel"]))
            
            try:
                answer = (await self.bot.wait_for(
                    "message", 
                    check=lambda x: x.author == ctx.author, 
                    timeout=60.0)).content
            
                if answer.lower() == ctx.lang["shared"]["cancel"]:
                    await ctx.abort()
                    return False

                result = await prop_type.convert(ctx, answer)
                
                if isinstance(result, Enum):
                    convertered = result.value
                elif isinstance(result, discord.mixins.Hashable):
                    convertered = result.id
                else:
                    convertered = result
            except TimeoutError:
                return
            except Exception:
                if isinstance(prop_type, commands.converter.IDConverter):
                    break
                
                await ctx.answer(ctx.lang["economy"]["invalid_prop_value"].format(
                    ctx.lang["economy"]["item_properties"][prop_name]))
        
        if prop_name == "name" and await self.eco.get_item(ctx.guild, convertered):
            await ctx.answer(ctx.lang["economy"]["item_already_created"].format(
                convertered))
            return False

        return convertered

    @commands.command(aliases=["bal", "money"], cls=EconomyCommand)
    async def balance(self, ctx, *, member: Optional[discord.Member]):
        account = await self.eco.get_money(member or ctx.author)

        em = discord.Embed(colour=ctx.color)
        em.set_author(name=account.member.name, icon_url=account.member.avatar_url)
        
        em.add_field(
            name=ctx.lang["economy"]["cash"], 
            value=self.currency_fmt(ctx.currency, account.cash))
        em.add_field(
            name=ctx.lang["economy"]["bank"], 
            value=self.currency_fmt(ctx.currency, account.bank))
        em.add_field(
            name=ctx.lang["shared"]["sum"], 
            value=self.currency_fmt(ctx.currency, account.sum))

        if account.sum > 0:
            if account.saved:
                place = await self.eco.get_place(account.member)
                em.set_footer(text=ctx.lang["economy"]["balance_place"].format(place))
            else:
                await account.save()

        await ctx.send(embed=em)

    @commands.command(aliases=["dep"], cls=EconomyCommand)
    async def deposit(self, ctx, amount: Optional[uint]):
        account = await self.eco.get_money(ctx.author)

        if amount is None:
            amount = account.cash

        if amount > account.cash or amount <= 0 or account.cash <= 0:
            return await ctx.answer(ctx.lang["economy"]["not_enough_cash"])

        account.cash -= amount
        account.bank += amount

        await account.save()
    
        await ctx.answer(ctx.lang["economy"]["deposited"].format(
            self.currency_fmt(ctx.currency, amount)))

    @commands.command(aliases=["with"], cls=EconomyCommand)
    async def withdraw(self, ctx, amount: Optional[uint]):
        account = await self.eco.get_money(ctx.author)

        if amount is None:
            amount = account.bank

        if amount > account.bank or amount <= 0 or account.bank <= 0:
            return await ctx.answer(ctx.lang["economy"]["not_enough_bank"])

        account.bank -= amount
        account.cash += amount

        await account.save()

        await ctx.answer(ctx.lang["economy"]["withdrew"].format(
            self.currency_fmt(ctx.currency, amount)))

    @commands.command(cls=EconomyCommand)
    async def give(self, ctx, member: NotAuthor, amount: uint(include_zero=False)):
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
    async def add_money(self, ctx, member: discord.Member, money_type: MoneyTypeConverter, amount: uint):
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
    async def remove_money(self, ctx, member: discord.Member, money_type: MoneyTypeConverter, amount: uint):
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
        if not await ctx.accept(ctx.lang["economy"]["really_delete?"].format(
                markdown(member.name, "**"))):
            return

        await Account(self.bot, member).delete()
        await ctx.answer(ctx.lang["economy"]["lost_all_money"].format(
            member.mention))

    @commands.group(name="start-money", cls=EconomyGroup, invoke_without_command=True)
    async def start_money(self, ctx):
        start_money = await self.bot.db.execute(
            "SELECT `cash`, `bank` FROM `start_money` WHERE `start_money`.`server` = ?",
            ctx.guild.id)
        
        cash, bank = start_money or (0, 0)

        em = discord.Embed(colour=ctx.color)
        em.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
        em.add_field(
            name=ctx.lang["economy"]["cash"], 
            value=self.currency_fmt(ctx.currency, cash))
        em.add_field(
            name=ctx.lang["economy"]["bank"], 
            value=self.currency_fmt(ctx.currency, bank))
        
        await ctx.send(embed=em)

    @start_money.command(name="set", cls=EconomyCommand)
    @is_commander()
    async def start_money_set(self, ctx, money_type: MoneyTypeConverter, amount: uint(include_zero=True)):
        update_sql = """
        UPDATE `start_money` 
        SET `{}` = ? 
        WHERE `start_money`.`server` = ?
        """
        
        check = await self.bot.db.execute(
            update_sql.format(money_type.name),
            amount, ctx.guild.id, with_commit=True)

        if not check:
            await self.bot.db.execute(
                "INSERT INTO `start_money` VALUES (?, ?, ?)",
                ctx.guild.id, 
                amount if money_type == MoneyType.cash else 0, 
                amount if money_type == MoneyType.bank else 0,
                with_commit=True)

        await ctx.answer(ctx.lang["economy"]["start_money_set"].format(
            self.currency_fmt(ctx.currency, amount), money_type.name))

    @commands.command(cls=EconomyCommand)
    @is_commander()
    async def currency(self, ctx, symbol: discord.Emoji):
        check = await self.bot.db.execute(
            "UPDATE `currency` SET `symbol` = ? WHERE `currency`.`server` = ?",
            symbol.id, ctx.guild.id, with_commit=True)
        
        if not check:
            await self.bot.db.execute(
                "INSERT INTO `currency` VALUES (?, ?)",
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

        select_count_sql = """
        SELECT COUNT(*) 
        FROM `money` 
        WHERE `money`.`server` = ? AND `money`.`cash` + `money`.`bank` > 0
        """

        count = await self.bot.db.execute(select_count_sql, ctx.guild.id)

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

        await self.bot.db.execute(
            "DELETE FROM `money` WHERE `money`.`server` = ?",
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
        check = await self.bot.db.execute(
            "DELETE FROM `income` WHERE `income`.`server` = ? AND `income`.`member` = ?",
            ctx.guild.id, member.id, with_commit=True)

        if check:
            await ctx.answer(ctx.lang["economy"]["income_deleted"].format(
                member.mention))
        else:
            await ctx.answer(ctx.lang["economy"]["no_income"].format(
                member.mention))

    @commands.group(invoke_without_command=True)
    @is_commander()
    async def story(self, ctx, story_id: uint):
        sql = """
        SELECT `text`, `type`, `author`, `result_type`
        FROM `story`
        WHERE `story`.`server` = ? AND `story`.`id` = ?
        """

        check = await self.bot.db.execute(
            sql, ctx.guild.id, story_id)

        if check is None:
            return await ctx.answer(ctx.lang["economy"]["no_story"].format(
                story_id))

        result_type = discord.utils.find(
            lambda x: x.value == check[3],
            GameResult.__members__.values())

        em = discord.Embed(
            title=ctx.lang["economy"]["story"].format(check[1], result_type.name),
            description=check[0], 
            colour=ctx.color)

        author = ctx.guild.get_member(check[2])

        em.set_author(
            name=(author and str(author)) or ctx.guild.name, 
            icon_url=(author and author.avatar_url) or ctx.guild.icon_url)

        await ctx.send(embed=em)

    @story.command(name="add")
    @is_commander()
    async def story_add(self, ctx, command: CommandConverter(cls=EconomyGame), result_type: GameResultConverter, *, text: str):
        if len(text) > EconomyConstants.STORY_MAX_LEN:
            return await ctx.answer(ctx.lang["economy"]["story_too_len"])
        
        if r"{money}" not in text:
            return await ctx.answer(ctx.lang["economy"]["need_marker"])

        story_id = await self.bot.db.execute(
            "SELECT COUNT(*) + 1 FROM `story` WHERE `story`.`server` = ?",
            ctx.guild.id)

        await self.bot.db.execute(
            "INSERT INTO `story` VALUES (?, ?, ?, ?, ?, ?, ?)",
            story_id, ctx.guild.id, ctx.author.id, 
            command.qualified_name, result_type.value,
            text, ctx.lang["lang_code"], with_commit=True)

        await ctx.answer(ctx.lang["economy"]["add_story"].format(story_id))

    @story.command(name="delete", aliases=["remove"])
    @is_commander()
    async def story_delete(self, ctx, story_id: uint):
        check = await self.bot.db.execute(
            "DELETE FROM `story` WHERE `story`.`server` = ? AND `story`.`id` = ?",
            ctx.guild.id, story_id, with_commit=True)

        if not check:
            await ctx.answer(ctx.lang["economy"]["no_story"].format(story_id))
        else:
            await ctx.answer(ctx.lang["economy"]["delete_story"].format(story_id))

    @commands.command()
    @is_commander()
    async def chance(self, ctx, command: CommandConverter(cls=EconomyGame), new_chance: Optional[uint]):
        if new_chance is None:
            return await ctx.answer(ctx.lang["economy"]["current_chance"].format(
                command.qualified_name, 
                (await self.eco.get_game_config(ctx, command)).chance))

        new_chance = min(100, new_chance)
    
        await self.eco.edit_game_config(ctx.guild, command, chance=new_chance)

        await ctx.answer(ctx.lang["economy"]["chance_changed"].format(
            command.qualified_name, new_chance))

    @commands.command(cls=EconomyCommand)
    @is_commander()
    async def reward(self, ctx, command: CommandConverter(cls=EconomyGame), new_reward: Optional[uint]):
        if new_reward is None:
            return await ctx.answer(ctx.lang["economy"]["current_reward"].format(
                command.qualified_name,
                self.currency_fmt(
                    ctx.currency, 
                    (await self.eco.get_game_config(ctx, command)).reward)))

        await self.eco.edit_game_config(ctx.guild, command, reward=new_reward)

        await ctx.answer(ctx.lang["economy"]["reward_changed"].format(
            command.qualified_name, 
            self.currency_fmt(ctx.currency, new_reward)))

    @commands.command(cls=StoryGame)
    @custom_cooldown()
    async def work(self, ctx):
        await ctx.command.use(ctx)

        if ctx.game_config.game_result == GameResult.success:
            ctx.account.bank += ctx.game_config.rolled_reward
        else:
            ctx.account.bank -= ctx.game_config.rolled_reward

        await ctx.account.save()

    @commands.command(cls=StoryGame)
    @custom_cooldown()
    async def slut(self, ctx):
        await ctx.command.use(ctx)

        if ctx.game_config.game_result == GameResult.success:
            ctx.account.cash += ctx.game_config.rolled_reward
        else:
            ctx.account.cash -= ctx.game_config.rolled_reward

        await ctx.account.save()

    @commands.command(cls=StoryGame)
    @custom_cooldown()
    async def crime(self, ctx):
        await ctx.command.use(ctx)

        if ctx.game_config.game_result == GameResult.success:
            ctx.account.cash += ctx.game_config.rolled_reward
        else:
            ctx.account.cash -= ctx.game_config.rolled_reward

        await ctx.account.save()

    @commands.command(cls=StoryGame)
    @custom_cooldown()
    async def rob(self, ctx, member: NotAuthor):
        member_account = await self.eco.get_money(member)
        money = ctx.game_config.rolled_reward

        if ctx.game_config.game_result == GameResult.success:
            if member_account.cash > 0:
                money = ceil(member_account.cash / 100 * ctx.game_config.rolled_chance)

            member_account.cash -= money
            ctx.account.cash += money

            await member_account.save()
        else:
            if ctx.account.cash > 0:
                money = ceil(ctx.account.cash / 100 * ctx.game_config.rolled_chance)

            ctx.account.cash -= money

        ctx.game_config.rolled_reward = money

        await ctx.command.use(ctx)
        await ctx.account.save()

    @commands.command(aliases=["bj"], cls=EconomyGame)
    @custom_cooldown()
    async def blackjack(self, ctx, bet: Bet):
        actions = tuple(map(str.lower, BJAction.__members__.keys()))

        em = discord.Embed(
            description=human_choice(
                tuple(map(str.title, actions)), 
                second_sep=ctx.lang["shared"]["or"]),
            colour=ctx.color)
        em.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        cards = list(ctx.lang["economy"]["cards"]["all"].items())
        deck = BJDeck(BJCard(ctx.lang["economy"]["cards"]["back"], None), cards, 4)
        shuffle = BJShuffle(ctx, em, deck)

        em.add_field(
            name=ctx.lang["economy"]["your_hand"], 
            value=''.join(map(lambda x: x.emoji, shuffle.player_hand.cards)))
        em.add_field(
            name=ctx.lang["economy"]["dealer_hand"],
            value=shuffle.dealer_hand.cards[0].emoji + deck.back.emoji)

        game_message = await ctx.send(embed=em)
        player_passed = False

        while not shuffle.closed:
            if not player_passed:
                try:
                    action_message = await self.bot.wait_for(
                        "message", 
                        check=lambda x: x.author == ctx.author and x.content.lower() in actions,
                        timeout=30.0)

                    action = await EnumConverter(BJAction).convert(
                        ctx, action_message.content)
                except TimeoutError:
                    break

                if action == BJAction.Pass:
                    player_passed = True
                elif action == BJAction.Draw:
                    shuffle.player_draw_card()
                elif action == BJAction.Double:
                    bet *= 2
                    shuffle.player_draw_card()

            draw_chance = 70 if bet >= ctx.account.sum else 60

            if len(tuple(filter(
                    lambda x: shuffle.dealer_hand.score + x[1] > 21, 
                    shuffle.deck.cards))) / len(shuffle.deck.cards) * 100 >= draw_chance:
                if player_passed:
                    break
            else:
                shuffle.dealer_draw_card()
            
            em.description = ctx.lang['economy']['current_bet'].format(
                self.currency_fmt(ctx.currency, bet))
            em.set_footer(
                text=f"{ctx.lang['economy']['cards_in_deck']} {len(shuffle.deck.cards)}")

            await game_message.edit(embed=em)

        bet *= 2
        winner = shuffle.winner()
        
        if winner is not None:
            account = await self.eco.get_money(ctx.author)

            if winner == ctx.author:
                em.description = ctx.lang["economy"]["win"].format(
                    self.currency_fmt(ctx.currency, bet))
                account.cash += bet
            elif winner == ctx.bot.user:
                em.description = ctx.lang["economy"]["lose"].format(
                    self.currency_fmt(ctx.currency, bet))
                account.cash -= bet

            await account.save()
        else:
            em.description = ctx.lang["economy"]["push"]

        em.set_field_at(
            0,
            name=em.fields[0].name,
            value=(f"{''.join(map(lambda x: x.emoji, shuffle.player_hand.cards))}\n\n"
                f"{ctx.lang['economy']['total_card_value']} {shuffle.player_hand.score}"))
        em.set_field_at(
            1,
            name=em.fields[1].name,
            value=(f"{''.join(map(lambda x: x.emoji, shuffle.dealer_hand.cards))}\n\n"
                f"{ctx.lang['economy']['total_card_value']} {shuffle.dealer_hand.score}"))

        await game_message.edit(embed=em)

    @commands.command(cls=EconomyGame)
    @custom_cooldown()
    async def slot(self, ctx, bet: Bet):
        game_config = await self.eco.get_game_config(ctx)

        if game_config.game_result == GameResult.success:
            if game_config.rolled_chance < 80:
                roll = (
                    random.choices(EconomyConstants.SLOTS, k=3),
                    (random.choice(EconomyConstants.SLOTS)) * 3,
                    random.choices(EconomyConstants.SLOTS, k=3)
                )
                bet *= 2
            else:
                roll = ((random.choice(EconomyConstants.SLOTS, )) * 3, ) * 3
                bet *= 3

            ctx.account.cash += bet
        else:
            roll = tuple(random.choices(EconomyConstants.SLOTS, k=3) for _ in range(3))
            bet *= 2
            ctx.account.cash -= bet

        await ctx.account.save()

        em = discord.Embed(
            description="{}\n\n{}\n{} :arrow_left:\n{}".format(
                (ctx.lang["economy"]["win"] 
                if game_config.game_result == GameResult.success 
                else ctx.lang["economy"]["lose"]).format(
                    self.currency_fmt(ctx.currency, bet)),
                *(' | '.join(roll[i]) for i in range(3))),
            colour=ctx.color)
        em.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        
        await ctx.send(embed=em)

    @commands.command(cls=EconomyGame)
    @custom_cooldown()
    async def dice(self, ctx, bet: Bet, predicted: Optional[uint]):
        bot_roll = random.randint(1, 6)
        player_roll = random.randint(1, 6)

        if bot_roll < 6:
            game_config = await self.eco.get_game_config(ctx)

            if game_config.game_result == GameResult.fail:
                bot_roll += 1

        em = discord.Embed(colour=ctx.color)
        em.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        em.add_field(
            name=ctx.lang["economy"]["player_roll"],
            value=EconomyConstants.ROLLS[player_roll])
        em.add_field(
            name=ctx.lang["economy"]["dealer_roll"],
            value=EconomyConstants.ROLLS[bot_roll])

        if bot_roll > player_roll:
            bet *= 2
            ctx.account.cash -= bet
            em.description = ctx.lang["economy"]["lose"].format(
                self.currency_fmt(ctx.currency, bet))
        elif bot_roll < player_roll:
            bet *= 3 if predicted == player_roll else 2
            ctx.account.cash += bet
            em.description = ctx.lang["economy"]["win"].format(
                self.currency_fmt(ctx.currency, bet))
        else:
            em.description = ctx.lang["economy"]["push"]

        await ctx.send(embed=em)
        await ctx.account.save()

    @commands.group(invoke_without_command=True)
    async def item(self, ctx, *, name: str):
        name = name[:EmbedConstants.FIELD_NAME_MAX_LEN]        
        item = await self.eco.get_item(ctx.guild, name)

        if item is None:
            return await ctx.answer(ctx.lang["economy"]["no_item_with_name"].format(
                name))

        em = discord.Embed(
            description=ctx.lang["economy"]["item"], 
            colour=ctx.color)
        em.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)

        em.add_field(
            name=ctx.lang["shared"]["author"],
            value=item.author.mention if item.author else ctx.lang["shared"]["left_member"],
            inline=False)

        em.add_field(
            name=ctx.lang["economy"]["buy_count"],
            value=item.buy_count,
            inline=False)

        for prop in item.properties.keys():
            value = item.__dict__[prop]
            
            em.add_field(
                name=ctx.lang["economy"]["item_properties"][prop].capitalize(),
                value=str(value) if value is not None else ctx.lang["shared"]["no"],
                inline=False)

        await ctx.send(embed=em)

    @item.command(name="create")
    @is_commander()
    async def item_create(self, ctx):
        timeout = dt.timedelta(minutes=len(ShopItem.properties))
        item_props = []

        for prop in ShopItem.properties.keys():
            convertered = await self.property_parse_dialogue(ctx, prop, timeout)

            if convertered is False:
                return

            item_props.append(convertered)

        await ctx.answer(ctx.lang["economy"]["item_created"].format(
            item_props[0]))

        await self.bot.db.execute(
            "INSERT INTO `shop_items` VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ctx.guild.id, ctx.author.id, 0, *item_props, with_commit=True)

    @item.command(name="edit")
    @is_commander()
    async def item_edit(self, ctx, *, name: str):
        name = name[:EconomyConstants.ITEM_MAX_LEN]
        item = await self.eco.get_item(ctx.guild, name)

        if item is None:
            return await ctx.answer(ctx.lang["economy"]["no_item_with_name"].format(
                name))

        allowed_props = ctx.lang["economy"]["item_properties"].values()
        to_edit = await ctx.ask(
            ctx.lang["economy"]["property_choice"].format(
                ', '.join(map(lambda x: markdown(x, '`'), allowed_props))), 
            check=lambda x: x.author == ctx.author and x.content.lower() in allowed_props)

        if to_edit is None:
            return

        translated = {v: k for k, v in ctx.lang["economy"]["item_properties"].items()}[to_edit]
        new_value = await self.property_parse_dialogue(
            ctx, translated, dt.timedelta(seconds=30))

        if new_value is False:
            return

        await ctx.answer(ctx.lang["economy"]["property_changed"].format(
            to_edit, name))

        update_sql = """
        UPDATE `shop_items` 
        SET `{}` = ? 
        WHERE `shop_items`.`server` = ? AND `shop_items`.`name` = ?
        """

        await self.bot.db.execute(update_sql.format(translated), 
            new_value, ctx.guild.id, name, with_commit=True)

    @item.command(name="delete")
    @is_commander()
    async def item_delete(self, ctx, *, name: str):
        delete_sql = """
        DELETE FROM `shop_items` 
        WHERE `shop_items`.`server` = ? AND `shop_items`.`name` = ?
        """

        check = await self.bot.db.execute(
            delete_sql, ctx.guild.id, name, with_commit=True)

        if check:
            await ctx.answer(ctx.lang["economy"]["item_deleted"].format(name))
        else:
            await ctx.answer(ctx.lang["economy"]["no_item_with_name"].format(
                name))
    
    @commands.command(cls=EconomyCommand, aliases=["store"])
    async def shop(self, ctx, page: Optional[IndexConverter] = Index(0)):
        select_sql = """
        SELECT `author`, `name`, `description`, `price`, `buy_count`, `stock`
        FROM `shop_items`
        WHERE `shop_items`.`server` = ?
        ORDER BY `shop_items`.`price`
        LIMIT ? OFFSET ?
        """
        
        check = await self.bot.db.execute(
            select_sql, ctx.guild.id,
            EconomyConstants.SHOP_PAGE_MAX_LEX,
            EconomyConstants.SHOP_PAGE_MAX_LEX * page.value, 
            fetch_all=True)

        if not len(check):
            return await ctx.answer(ctx.lang["economy"]["no_items_on_page"].format(
                page.humanize()))

        count = await self.bot.db.execute(
            "SELECT COUNT(*) FROM `shop_items` WHERE `shop_items`.`server` = ?",
            ctx.guild.id)

        em = discord.Embed(
            title=ctx.lang["economy"]["shop"].format(ctx.guild.name), 
            colour=ctx.color)

        context_item = namedtuple("item", ("name", "price", "buy_count", "stock"))
        formatter = ContextFormatter(
            "author", "price", "buy_count", "stock", 
            guild=ctx.guild, member=ctx.author, currency=ctx.currency)

        for author_id, name, desc, price, buy_count, stock in check:
            formatter.ctx["item"] = context_item( 
                name, self.currency_fmt(ctx.currency, price), 
                buy_count, stock)
            
            formatter.ctx["author"] = ctx.guild.get_member(author_id) or ctx.lang["shared"]["left_member"]

            em.add_field(
                name=(f"{name} " 
                    f"({f'{buy_count}/{stock}' if stock > 0 else StringConstants.INFINITY}) "
                    f"{StringConstants.DOT_SYMBOL} " 
                    f"{self.currency_fmt(ctx.currency, price)}"),
                value=formatter.format(desc),
                inline=False)

        em.set_footer(text=(
            f'{ctx.lang["shared"]["page"]} '
            f"{page.humanize()}/{ceil(count / EconomyConstants.SHOP_PAGE_MAX_LEX)}"))

        await ctx.send(embed=em)

    # TODO:
    #   item edit command
    # await bot.db.execute("""create table `shop_items` (
    #     `server` bigint,
    #     `author` bigint,
    #     `buy_count` bigint,
    #     `name` TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    #     `price` bigint,
    #     `description` TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    #     `role` bigint,
    #     `stock` bigint,
    #     `message_type` int,
    #     `message` TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci)""")

def setup(bot):
    bot.add_cog(Economy(bot))
