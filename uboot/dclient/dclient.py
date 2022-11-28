import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
import discord
from discord import RawReactionActionEvent
from discord.ext import commands, tasks

from utils import Log
from config import DiscordConfig
from managers import settings, users, react_roles
from db import SqliteDb
from .helper import thread_close, react_processor, get_channel


intents = discord.Intents.default()
intents.message_content = True  # pylint: disable=assigning-non-slot
intents.reactions = True  # pylint: disable=assigning-non-slot
intents.members = True  # pylint: disable=assigning-non-slot

member_cache = discord.MemberCacheFlags(joined=True)


class DiscordBot(commands.Bot):
    def __init__(self, prefix: str) -> None:
        super().__init__(command_prefix=commands.when_mentioned_or(prefix),
                         intents=intents,
                         member_cache_flags=member_cache)
        self.prefix = prefix
        self._extensions: list[str] = ['dclient.cogs.general',
                                       'dclient.cogs.threads',
                                       'dclient.cogs.gamble',
                                       'dclient.cogs.admin',
                                       'dclient.cogs.button']
        self._db = SqliteDb("test")
        self._db.role.load_many()
        self._db.user.load_many()
        self._db.guild.load_many()

    def add_react_role(self, react: str, role_id: int,
                       guild_id: int, reverse: bool) -> bool:
        react_role = react_roles.Manager.find(guild_id, react)
        if react_role and (react_role.reaction == react or react_role.role_id):
            return False

        raw = (role_id, guild_id, react, reverse)
        react_role = react_roles.Manager.add(react_roles.ReactRole(raw))
        self._db.role.update(react_role)
        return True

    def rm_react_role(self, react: str, role_id: int) -> bool:
        react_role = react_roles.Manager.get(role_id)
        if not react_role:
            return False

        # Remove the role from the tracked.
        react_roles.Manager.remove(react_role)
        self._db.role.delete_one(react_role)
        return True

    @tasks.loop(minutes=1)
    async def status_update(self) -> None:
        if not self.user:
            return
        user = users.Manager.get(self.user.id)
        win_rate = 0
        if user.gambles > 0:
            win_rate = (1 + (user.gambles_won - user.gambles) /
                        user.gambles) * 100
        activity = discord.Game(f"win-rate: {win_rate:0.2f}%")
        await self.change_presence(activity=activity)

    @tasks.loop(minutes=15)
    async def archiver(self) -> None:
        for guild in self.guilds:
            setting = settings.Manager.get(guild.id)
            if 0 in (setting.market_channel_id, setting.expiration_days):
                continue
            market_ch = await get_channel(self, setting.market_channel_id)
            if not market_ch or not isinstance(
                    market_ch, discord.ForumChannel):
                return

            reason = "post expired."
            for thread in market_ch.threads:
                if thread.archived or not thread.created_at:
                    continue

                msg = f"Your post '{thread.name}' expired."
                elapsed = datetime.now(timezone.utc) - thread.created_at
                if elapsed > timedelta(days=setting.expiration_days):
                    # Expired, update the name.
                    if "[expired]" not in thread.name.lower():
                        await thread.edit(name=f"[EXPIRED] {thread.name}")

                    # Close the thread.
                    await thread_close('none', 'expired', thread, reason, msg)

    @status_update.before_loop
    async def status_update_wait_on_login(self) -> None:
        await self.wait_until_ready()

    @archiver.before_loop
    async def archiver_wait_on_login(self) -> None:
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()
        for ext in self._extensions:
            await self.load_extension(ext)
        self.archiver.start()  # pylint: disable=no-member
        self.status_update.start()  # pylint: disable=no-member

    async def on_ready(self) -> None:
        Log.debug(f"Logged in as {self.user}")

    async def close(self) -> None:
        await super().close()
        await self.session.close()

    async def on_message(self, msg: discord.Message) -> None:
        await self.process_commands(msg)
        if not self.user or msg.author == self.user:
            return
        if self.user in msg.mentions or msg.content.startswith(self.prefix):
            return

        # Add to user gold count.
        user = users.Manager.get(msg.author.id)
        user.add_message()
        self._db.user.update(user)

    async def on_thread_create(self, thread: discord.Thread) -> None:
        if not isinstance(thread.parent, discord.ForumChannel):
            return

        open_tag: Optional[discord.ForumTag] = None
        for tag in thread.parent.available_tags:
            if tag.name.lower() == "open":
                open_tag = tag
                break
        if not open_tag:
            return

        if open_tag not in thread.applied_tags:
            await thread.add_tags(open_tag)

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        values = await react_processor(self, payload)
        if not values:
            return

        if values[2]:
            await values[0].remove_roles(values[1])
        else:
            await values[0].add_roles(values[1])

    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        values = await react_processor(self, payload)
        if not values:
            return

        if values[2]:
            await values[0].add_roles(values[1])
        else:
            await values[0].remove_roles(values[1])

    @staticmethod
    def init_run(config: DiscordConfig) -> None:
        try:
            handler = logging.FileHandler(filename='discord.log',
                                          encoding='utf-8',
                                          mode='w')
            dbot: DiscordBot = DiscordBot(config.prefix)
            dbot.run(config.token, log_handler=handler,
                     log_level=logging.DEBUG)
        except KeyboardInterrupt:
            Log.print("Discord Bot killing self globally.")
