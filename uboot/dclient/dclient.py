import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

import aiohttp
import discord
from discord import RawReactionActionEvent
from discord.ext import commands, tasks

from utils import Log
from config import DiscordConfig
from db import SqliteDb
from react_role import ReactRole
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
                                       'dclient.cogs.threads',
                                       'dclient.cogs.react_role']
        self._db = SqliteDb("test")
        self.react_roles = self._db.role.load_many()
        self._config = config

    def add_react_role(self, react: str, role: int, guild_id: int) -> bool:
        for pair in self.react_roles:
            if pair.reaction == react or pair.role_id == role:
                return False

        self.react_roles.append(ReactRole(react, role, guild_id))
        self._db.role.save_many(self.react_roles)
        return True

    def rm_react_role(self, react: str, role: int, guild_id: int) -> bool:
        react_role: Optional[ReactRole] = None
        for pair in self.react_roles:
            if pair.reaction == react or pair.role_id == role:
                react_role = pair
                break
        if react_role is None:
            return False

        # Remove the role from the tracked.
        self.react_roles = [r for r in self.react_roles if r.role_id != role]

        self._db.role.delete_one(react_role)
        return True

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

    async def react_proc(self, payload: RawReactionActionEvent):
        if payload.guild_id is None:
            return None

        # Validate the guild for the reaction.
        guild = self.get_guild(payload.guild_id)
        if guild is None:
            return None

        # Check if it is a react-role.
        react_role: Optional[ReactRole] = None
        for pair in self.react_roles:
            if (pair.reaction == payload.emoji.name
                    and pair.guild_id == guild.id):
                react_role = pair
                break
        if react_role is None:
            return None

        # Validate the member/user exists.
        user = guild.get_member(payload.user_id)
        if user is None:
            user = await guild.fetch_member(payload.user_id)
        if user is None or user.bot:
            return None

        # Get the role related to the reaction.
        guild_role = guild.get_role(react_role.role_id)
        if guild_role is None:
            return None

        return (user, guild_role)

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        pair = await self.react_proc(payload)
        if pair is None:
            return

        await pair[0].add_roles(pair[1])

    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        pair = await self.react_proc(payload)
        if pair is None:
            return

        await pair[0].remove_roles(pair[1])

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
