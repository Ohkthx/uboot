import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
import discord
from discord import RawReactionActionEvent
from discord.ext import commands, tasks

from utils import Log
from config import DiscordConfig
from settings import SettingsManager
from db import SqliteDb
from react_role import ReactRole
from .helper import thread_close, react_processor, get_channel


intents = discord.Intents.default()
intents.message_content = True  # pylint: disable=assigning-non-slot
intents.reactions = True  # pylint: disable=assigning-non-slot
intents.members = True  # pylint: disable=assigning-non-slot

member_cache = discord.MemberCacheFlags(joined=True)


@commands.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: commands.Context) -> None:
    """Syncs the current slash commands with the guild."""
    if not ctx.guild:
        return
    synced = await ctx.bot.tree.sync()
    await ctx.send(f"Synced {len(synced)} commands to the current guild.")


class DiscordBot(commands.Bot):
    def __init__(self, prefix: str) -> None:
        super().__init__(command_prefix=commands.when_mentioned_or(prefix),
                         intents=intents,
                         member_cache_flags=member_cache)
        self._extensions: list[str] = ['dclient.cogs.general',
                                       'dclient.cogs.threads',
                                       'dclient.cogs.react_role',
                                       'dclient.cogs.settings']
        self.add_command(sync)
        self._db = SqliteDb("test")
        self.react_roles = self._db.role.load_many()
        self.all_users = self._db.user.load_many()
        self._db.guild.load_many()

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
        if not react_role:
            return False

        # Remove the role from the tracked.
        self.react_roles = [r for r in self.react_roles if r.role_id != role]

        self._db.role.delete_one(react_role)
        return True

    @tasks.loop(minutes=15)
    async def archiver(self) -> None:
        for guild in self.guilds:
            setting = SettingsManager.get(guild.id)
            if 0 in (setting.market_channel_id, setting.expiration_days):
                continue
            market_ch = await get_channel(self, setting.market_channel_id)
            if not market_ch or not isinstance(market_ch, discord.ForumChannel):
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
        pair = await react_processor(self, self.react_roles, payload)
        if not pair:
            return

        await pair[0].add_roles(pair[1])

    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        pair = await react_processor(self, self.react_roles, payload)
        if not pair:
            return

        await pair[0].remove_roles(pair[1])

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
