import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

import aiohttp
import discord
from discord import RawReactionActionEvent
from discord.ext import commands, tasks

from utils import Log
from config import DiscordConfig
from .helper import thread_close


intents = discord.Intents.default()
intents.message_content = True  # pylint: disable=assigning-non-slot
intents.reactions = True  # pylint: disable=assigning-non-slot
intents.members = True  # pylint: disable=assigning-non-slot

member_cache = discord.MemberCacheFlags(joined=True)


class DiscordBot(commands.Bot):
    def __init__(self, config: DiscordConfig) -> None:
        super().__init__(command_prefix=config.prefix, intents=intents,
                         member_cache_flags=member_cache)
        self._extensions: list[str] = ['dclient.cogs.general',
                                       'dclient.cogs.threads']
        self._config = config

    @tasks.loop(minutes=15)
    async def archiver(self) -> None:
        market = await self.fetch_channel(self._config.market_id)
        if not isinstance(market, discord.ForumChannel):
            return

        reason = "post expired."
        for thread in market.threads:
            if thread.archived or thread.created_at is None:
                continue

            msg = f"Your post '{thread.name}' expired."
            elapsed = datetime.now(timezone.utc) - thread.created_at
            if elapsed > timedelta(days=self._config.market_expiration):
                # Expired, update the name.
                name = thread.name
                if "[expired]" not in thread.name.lower():
                    await thread.edit(name=f"[EXPIRED] {thread.name}")

                # Close the thread.
                await thread_close('none', 'expired', thread, reason, msg)

    @archiver.before_loop
    async def wait_on_login(self) -> None:
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()
        for ext in self._extensions:
            await self.load_extension(ext)
        self.archiver.start()  # pylint: disable=no-member

    async def on_ready(self) -> None:
        Log.debug(f"Logged in as {self.user}")

    async def close(self) -> None:
        await super().close()
        await self.session.close()

    async def on_thread_create(self, thread: discord.Thread) -> None:
        if type(thread.parent) is not discord.ForumChannel:
            return

        open_tag: Optional[discord.ForumTag] = None
        for tag in thread.parent.available_tags:
            if tag.name.lower() == "open":
                open_tag = tag
                break
        if open_tag is None:
            return

        if open_tag not in thread.applied_tags:
            await thread.add_tags(open_tag)

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        user = self.get_user(payload.user_id)
        if user is None:
            user = await self.fetch_user(payload.user_id)
        if user is None:
            return

        print(f"{user} added {payload.emoji}")

    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        user = self.get_user(payload.user_id)
        if user is None:
            user = await self.fetch_user(payload.user_id)
        if user is None:
            return

        print(f"{user} removed {payload.emoji}")

    @staticmethod
    def init_run(config: DiscordConfig) -> None:
        try:
            handler = logging.FileHandler(filename='discord.log',
                                          encoding='utf-8',
                                          mode='w')
            dbot: DiscordBot = DiscordBot(config)
            dbot.run(config.token, log_handler=handler,
                     log_level=logging.DEBUG)
        except KeyboardInterrupt:
            Log.print("Discord Bot killing self globally.")
