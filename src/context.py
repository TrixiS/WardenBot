from discord.ext.commands import Context
from discord import Embed

import logging


class WardenContext(Context):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.lang = None
        self.color = None

    async def answer(self, message: str) -> None:
        em = Embed(colour=self.color, description=message)
        em.set_author(name=self.message.author.name, icon_url=self.message.author.avatar_url)

        await self.send(embed=em)