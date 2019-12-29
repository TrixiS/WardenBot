from discord.ext.commands import Context
from discord import Embed

from asyncio import TimeoutError


class WardenContext(Context):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.lang = None
        self.color = None

    async def answer(self, message: str) -> None:
        em = Embed(colour=self.color, description=message)
        em.set_author(name=self.message.author.name, icon_url=self.message.author.avatar_url)

        await self.send(embed=em)

    async def ask(self, text: str, **kwargs) -> str:
        await self.send(f"{self.message.author.mention}, {text}")

        content = ""

        try:
            check = kwargs.pop("check", lambda m: m.author == self.author)

            content = (await self.bot.wait_for("message", **kwargs, check=check)).content
        finally:
            return content