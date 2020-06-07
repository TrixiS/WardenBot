import re

from itertools import chain
from asyncio import TimeoutError

from .constants import StringConstants


class PseudoMember:

    __slots__ = ("id", "guild")

    def __init__(self, id, guild):
        self.id = id
        self.guild = guild


class ContextFormatter:

    pattern = re.compile(r"\{([a-zA-Z_\.]+?)\}")

    def __init__(self, *extra_fields, **context):
        self.ctx = context
        self.extra_fields = extra_fields

    @property
    def allowed_fields(self):
        return set(StringConstants.ALLOWED_FMT_FIELDS + self.extra_fields)

    def make_tag(self, *tokens):
        return '{' + '.'.join(tokens) + '}'

    # TODO: optimize this
    def get_value(self, value_str):
        try:
            result = eval(value_str, self.ctx, self.ctx)
            return str(result)
        except Exception as e:
            return "None"

    def format(self, string):
        allowed_fields = self.allowed_fields

        for match in set(self.pattern.findall(string)):
            match = match.split('.')

            if len(match) == 0:
                continue

            name, *values = match

            if name not in self.ctx or any(value not in allowed_fields for value in values):
                continue
            
            tag = self.make_tag(name, *values)
            string = string.replace(tag, self.get_value(tag[1:-1]))

        return string


class PaginateError(BaseException):
    pass


class Pages:

    first_page = '↩️'
    prev_page = '⬅️'
    next_page = '➡️'
    last_page = '↪️'

    def __init__(self, ctx, pages):
        if len(pages) < 2:
            raise PaginateError("Length of pages should be > 1.")
 
        def reaction_check(r, u):
            return (u == self.user and 
                    str(r) in (self.first_page, self.prev_page, self.next_page, self.last_page) and
                    r.message.id == self.message.id)

        self.ctx = ctx
        self.bot = ctx.bot
        self.user = ctx.author
        self.check = reaction_check
        self.pages = pages
        self.channel = ctx.message.channel
        self.message = None
        self._current_page_index = 0

    @property
    def current_page(self):
        return self.pages[self.current_page_index]

    @property
    def current_page_index(self):
        return self._current_page_index

    @current_page_index.setter
    def current_page_index(self, value):
        if value >= len(self.pages):
            value = 0
        elif value < 0:
            value = len(self.pages) - 1

        self._current_page_index = value

    def add_page(self, page):
        self.pages.append(page)

    async def show_embed(self):
        embed = self.current_page
        embed.set_footer(
            text=f"{self.ctx.lang['shared']['page']} {self.current_page_index + 1}/{len(self.pages)}")

        if self.message is not None:
            return await self.message.edit(embed=embed)
            
        message = await self.channel.send(embed=embed)

        if len(self.pages) > 2:
            await message.add_reaction(self.first_page)

        await message.add_reaction(self.prev_page)
        await message.add_reaction(self.next_page)

        if len(self.pages) > 2:
            await message.add_reaction(self.last_page)

        self.message = message

    async def paginate(self):
        await self.show_embed()

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add",
                    check=self.check,
                    timeout=120.0)
            except TimeoutError:
                return
            else:
                await self.message.remove_reaction(reaction, self.user)
                reaction = str(reaction)

                if reaction == self.first_page:
                    if self.current_page_index == 0:
                        continue

                    self.current_page_index = 0
                elif reaction == self.prev_page:
                    self.current_page_index -= 1
                elif reaction == self.next_page:
                    self.current_page_index += 1
                elif reaction == self.last_page:
                    last_index = len(self.pages) - 1

                    if self.current_page_index == last_index:
                        continue
                    
                    self.current_page_index = last_index

                await self.show_embed()
