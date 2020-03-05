from discord.ext.commands import Context
from discord import Embed
from cogs.utils.constants import EmbedConstants
from asyncio import TimeoutError

import logging


class WardenContext(Context):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.lang = None
        self.color = None

    async def send(self, content: str=None, **kwargs) -> None:
        try:
            msg = await super().send(content, **kwargs)
        except Exception as e:
            logging.error(str(e))
            msg = await super().send(self.lang["errors"]["send_error"])

        return msg

    async def answer(self, message: str, **kwargs) -> None:
        em = Embed(colour=self.color, description=message)
        em.set_author(name=self.message.author.name, icon_url=self.message.author.avatar_url)

        await self.send(embed=em, **kwargs)

    async def ask(self, text: str, *, with_attachments=False, **kwargs) -> str:
        await self.send(f"{self.message.author.mention}, {text}")

        content = None

        try:
            check = kwargs.pop("check", lambda m: m.author == self.author)
            timeout = kwargs.pop("timeout", 30.0)

            msg = await self.bot.wait_for("message", **kwargs, check=check, timeout=timeout)

            content = msg.content
            
            if with_attachments:
                content += '\n'.join(
                    attach.url for attach in msg.attachments
                    if (attach.width or attach.height))
        finally:
            return content