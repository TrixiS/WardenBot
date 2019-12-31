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

    async def ask(self, text: str, *, with_attachments=False, **kwargs) -> str:
        await self.send(f"{self.message.author.mention}, {text}")

        content = ""

        try:
            check = kwargs.pop("check", lambda m: m.author == self.author)

            msg = await self.bot.wait_for("message", **kwargs, check=check)

            content = msg.content
            
            if with_attachments:
                content += '\n'.join(
                attach.url for attach in msg.attachments
                if (attach.width or attach.height)
            )
        finally:
            return content