import logging

import aiohttp
import discord
from discord.ext import commands

from utils import Log


intents = discord.Intents.default()
intents.message_content = True  # pylint: disable=assigning-non-slot


class DiscordBot(commands.Bot):
    def __init__(self, prefix: str) -> None:
        super().__init__(command_prefix=prefix, intents=intents)
        self._extensions: list[str] = ['dclient.cogs.general']

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()
        for ext in self._extensions:
            await self.load_extension(ext)

    async def close(self) -> None:
        await super().close()
        await self.session.close()

    @staticmethod
    def init_run(prefix: str, token: str) -> None:
        try:
            handler = logging.FileHandler(filename='discord.log',
                                          encoding='utf-8',
                                          mode='w')
            dbot: DiscordBot = DiscordBot(prefix)
            dbot.run(token, log_handler=handler, log_level=logging.DEBUG)
        except KeyboardInterrupt:
            Log.print("Discord Bot killing self globally.")
