"""The core of the Discord Bot and Client."""
import logging
import time
import random
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import aiohttp
import discord
from discord import RawReactionActionEvent
from discord.ext import commands, tasks

from utils import Log
from config import DiscordConfig
from managers import settings, users, react_roles, tickets, subguilds
from .helper import thread_close, react_processor, get_channel, find_tag
from .views.generic_panels import SuggestionView, BasicThreadView


intents = discord.Intents.default()
intents.message_content = True  # pylint: disable=assigning-non-slot
intents.reactions = True  # pylint: disable=assigning-non-slot
intents.members = True  # pylint: disable=assigning-non-slot

member_cache = discord.MemberCacheFlags(joined=True)

defaultHelp = commands.DefaultHelpCommand(no_category="HELP")


class ViewCategory(Enum):
    """Categories for DesctructableViews"""
    OTHER = 'other'
    GAMBLE = 'gamble'


class DestructableView():
    """A Destructable View that has a temporary life. Upon expiration it is
    destroyed and removed from Discord.
    """

    def __init__(self, msg: discord.Message, category: ViewCategory,
                 user_id: int, length: int) -> None:
        self.msg = msg
        self.category = category
        self.user_id = user_id
        self.length = length
        self.timestamp = datetime.now()

    def isexpired(self) -> bool:
        """Checks if the view has expired and should be removed."""
        now = datetime.now()
        return now - self.timestamp > timedelta(seconds=self.length)

    async def remove(self) -> None:
        """Removes the view, deleting if the message has no content."""
        try:
            # If it is an empty message without the view, just remove it.
            if len(self.msg.content) == 0 and len(self.msg.embeds) == 0:
                return await self.msg.delete()
            self.msg = await self.msg.edit(view=None)
        except BaseException:
            Log.debug("Could not remove the destructable view.")


class Sudoer():
    """Sudoer is a person with temporary elevated roles. This class manages
    the length of time to hold the role, removing the role upon expiration.
    """

    def __init__(self, user: discord.Member, role: discord.Role,
                 length: int) -> None:
        self.user = user
        self.role = role
        self.length = length
        self.timestamp = datetime.now()

    def isexpired(self) -> bool:
        """Checks if the time has elapsed and the role should be removed."""
        now = datetime.now()
        return now - self.timestamp > timedelta(seconds=self.length)

    async def remove(self) -> None:
        """Removes the role from the user."""
        try:
            await self.user.remove_roles(self.role)
        except BaseException:
            Log.debug("Could not remove the role from the sudoer.")


class Powerhour():
    """Powerhour is a single hour in which gold generation is increased."""

    def __init__(self, guild_id: int, channel_id: int, multiplier: float):
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.multiplier = multiplier
        self.timestamp = datetime.now()

    def isexpired(self) -> bool:
        """Checks if the time has elapsed and powerhour should be removed."""
        now = datetime.now()
        return now - self.timestamp > timedelta(hours=1)

    async def send_end(self, bot: 'DiscordBot') -> None:
        """Notifies the channel that the powerhour has ended."""
        embed = discord.Embed()
        embed.description = "__**Message POWERHOUR ended!**__\n"\
            "> └ Gold generation per message returned to normal."
        embed.color = discord.Colour.from_str("#ff0f08")

        channel = await get_channel(bot, self.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return
        await channel.send(embed=embed)


# All of the cogs and views that should be loaded. Views are Persistent.
cog_extensions: list[str] = ['dclient.cogs.general',
                             'dclient.cogs.threads',
                             'dclient.cogs.gamble',
                             'dclient.cogs.admin',
                             'dclient.cogs.private_guild',
                             'dclient.cogs.test',
                             'dclient.views.test',
                             'dclient.views.support_request',
                             'dclient.views.support_thread',
                             'dclient.views.red_button',
                             'dclient.views.private_guild_signup',
                             'dclient.views.private_guild_panel']


class DiscordBot(commands.Bot):
    """The core of the Discord Bot and Client."""

    def __init__(self, prefix: str, owner_id: Optional[int]) -> None:
        super().__init__(command_prefix=commands.when_mentioned_or(prefix),
                         owner_id=owner_id,
                         intents=intents,
                         member_cache_flags=member_cache,
                         help_command=defaultHelp)
        self.prefix = prefix
        self._extensions = cog_extensions
        self.session: Optional[aiohttp.ClientSession] = None

        # Initialize all of the managers and their databases.
        tickets.Manager.init("uboot.sqlite3")
        users.Manager.init("uboot.sqlite3")
        settings.Manager.init("uboot.sqlite3")
        react_roles.Manager.init("uboot.sqlite3")
        subguilds.Manager.init("uboot.sqlite3")

        self.sudoer: Optional[Sudoer] = None
        self.destructables: dict[int, DestructableView] = {}
        self.last_button: Optional[discord.Message] = None
        self.powerhours: dict[int, Powerhour] = {}

    def set_sudoer(self, user: discord.Member, role: discord.Role,
                   length: int) -> None:
        """Sets the sudoer temporarily."""
        self.sudoer = Sudoer(user, role, length)

    def add_destructable(self, destructable: DestructableView) -> None:
        """Adds a desctructable view to be managed and eventually destroyed."""
        self.destructables[destructable.msg.id] = destructable

    async def rm_user_destructable(self, user_id: int, category: ViewCategory):
        """Removes all destructables tied to a specific user. If they are not
        expired, that will be destroyed and removed anyways.
        """
        # Remove them via the API first.
        delete: list[int] = []
        for msgid, destruct in self.destructables.items():
            if destruct.user_id == user_id and destruct.category == category:
                await destruct.remove()
                delete.append(msgid)

        # Remove them from memory.
        for i in delete:
            destruct = self.destructables[i]
            if len(destruct.msg.components) > 0:
                Log.print(f"[{i}] has too many components still.")
                continue
            del self.destructables[i]

    def start_powerhour(self, guild_id: int, channel_id: int,
                        multiplier: float) -> None:
        """Starts a powerhour for the selected guild."""
        self.powerhours[guild_id] = Powerhour(guild_id, channel_id, multiplier)

    async def setup_hook(self) -> None:
        """Overrides the setup hook, loading all extensions (views/cogs) and
        sets additional persistent views. Initializes the loops that checks
        for updates.
        """
        self.session = aiohttp.ClientSession()
        for ext in self._extensions:
            await self.load_extension(ext)

        # Persistent Views
        self.add_view(BasicThreadView())
        self.add_view(SuggestionView())

        # Starts the updating loops.
        self.archiver.start()  # pylint: disable=no-member
        self.status_update.start()  # pylint: disable=no-member

    async def on_ready(self) -> None:
        """Triggered on 'on_ready' event, sets the bot user."""
        if not self.user:
            return
        Log.debug(f"Logged in as {self.user}")
        users.Manager.get(self.user.id).isbot = True

    async def close(self) -> None:
        """This is called to close the bot in a clean manner."""
        await super().close()
        if self.session:
            await self.session.close()

    def add_react_role(self, react: str, role_id: int,
                       guild_id: int, reverse: bool) -> bool:
        """Adds a Reaction and Role pair if it does not already exist or
        conflict. Saves it memory and database.
        """
        # Check if the pair already exists.
        react_role = react_roles.Manager.find(guild_id, react)
        if react_role and (react_role.reaction == react or react_role.role_id):
            return False

        # Add the pair and save it if it does not exist.
        raw = (role_id, guild_id, react, reverse)
        react_role = react_roles.Manager.add(react_roles.ReactRole(raw))
        react_role.save()
        return True

    def rm_react_role(self, react: str, role_id: int) -> bool:
        """Removes a Reaction and Role pair if it does exist
        Removes it memory and database.
        """
        # Try to find the pair.
        react_role = react_roles.Manager.get(role_id)
        if not react_role:
            return False

        # Remove the role from the tracked and delete from database.
        react_roles.Manager.remove(react_role)
        react_role.delete()
        return True

    @tasks.loop(seconds=15)
    async def status_update(self) -> None:
        """Checks destructable views, sudoers, and updates the presence for
        the Discord Bot.
        """
        # Manages the 'Red Button', randomly deleting it.
        if self.last_button:
            if random.randint(0, 9) == 0:
                try:
                    await self.last_button.delete()
                except BaseException:
                    pass
                finally:
                    self.last_button = None

        # Check powerhours, if they are expired they will be removed.
        delete: list[int] = []
        for guild_id, powerhour in self.powerhours.items():
            if powerhour.isexpired():
                await powerhour.send_end(self)
                delete.append(guild_id)
        # Remove from memory.
        for i in delete:
            del self.powerhours[i]

        # Check destructable views, if they are expired they will be removed.
        delete: list[int] = []
        for view_id, destruct in self.destructables.items():
            if destruct.isexpired():
                await destruct.remove()
                delete.append(view_id)
        # Remove from memory.
        for i in delete:
            del self.destructables[i]

        # Check if sudoer needs to have their role removed.
        if self.sudoer and self.sudoer.isexpired():
            await self.sudoer.remove()
            await self.sudoer.user.send("Sudo status expired.")
            self.sudoer = None

        if not self.user:
            return

        # Update the prescence / status with the current help and win-rate.
        user = users.Manager.get(self.user.id)
        activity = discord.Game(
            f"{self.prefix}help | win-rate: {user.win_rate():0.1f}%",
        )
        await self.change_presence(activity=activity)

    @tasks.loop(minutes=15)
    async def archiver(self) -> None:
        """Check if there is an market posts that have expired and need
        to be closed.
        """
        for guild in self.guilds:
            setting = settings.Manager.get(guild.id)
            if 0 in (setting.market_channel_id, setting.expiration_days):
                continue

            # Get the market channel and make sure it is a forum channel.
            market_ch = await get_channel(self, setting.market_channel_id)
            if not market_ch or not isinstance(
                    market_ch, discord.ForumChannel):
                return

            reason = "post expired."
            for thread in market_ch.threads:
                if thread.archived or not thread.created_at:
                    # Ignore archived or errored posts.
                    continue

                # Calculate if it is expired.
                msg = f"Your post '{thread.name}' expired."
                elapsed = datetime.now(timezone.utc) - thread.created_at
                if elapsed < timedelta(days=setting.expiration_days):
                    # Not expired, continue.
                    continue

                # Expired, update the name.
                if "[expired]" not in thread.name.lower():
                    await thread.edit(name=f"[EXPIRED] {thread.name}")

                # Close the thread.
                await thread_close(['none'], 'expired', thread, reason, msg)

    @status_update.before_loop
    async def status_update_wait_on_login(self) -> None:
        """Pauses the update thread until the bot has authenticated."""
        await self.wait_until_ready()

    @archiver.before_loop
    async def archiver_wait_on_login(self) -> None:
        """Pauses the update thread until the bot has authenticated."""
        await self.wait_until_ready()

    async def on_message(self, msg: discord.Message) -> None:
        """Triggered on 'on_message' event. Used to process commands and
        add message and gold to users. Also logs DMs sent to the bot.
        """
        # Process the commands if not from a bot.
        if not msg.author.bot:
            await self.process_commands(msg)

        # Do not add messages or gold if the user is the bot.
        if not self.user or msg.author == self.user or msg.author.bot:
            return
        if self.user in msg.mentions or msg.content.startswith(self.prefix):
            return

        # Set the 'owner' for the bot.
        if not self.owner_id:
            await self.is_owner(msg.author)

        # Add message and gold to user, saving to database.
        user = users.Manager.get(msg.author.id)
        if msg.guild:
            powerhour = self.powerhours[msg.guild.id]
            multiplier: float = 1.0
            if powerhour:
                multiplier = powerhour.multiplier
            user.add_message(multiplier)
            return user.save()

        if not self.owner_id or user.id == self.owner_id:
            return

        # Log all DMs sent to the bot.
        if isinstance(msg.channel, discord.DMChannel):
            embed = discord.Embed(title="DM Detected",
                                  description=msg.content)
            embed.set_footer(text=msg.author)
            embed.set_thumbnail(url=msg.author.display_avatar.url)
            owner = self.get_user(self.owner_id)
            if not owner:
                try:
                    owner = await self.fetch_user(self.owner_id)
                except BaseException:
                    pass
            if owner:
                await owner.send(embed=embed)

    async def on_thread_create(self, thread: discord.Thread) -> None:
        """Triggered on the 'on_thread_create' event. Used to appropriately
        label threads as 'open' or their proper equivalent. Creates the panel
        if it has an assigned one.
        """
        if not thread.guild:
            # Ignore if the guild cannot be identified.
            return

        if not isinstance(thread.parent, discord.ForumChannel):
            # Ignore if it isn't a forum channel thread.
            return

        setting = settings.Manager.get(thread.guild.id)

        # If it is a suggestion channel... add the panel.
        c_id = setting.suggestion_channel_id
        if c_id != 0 and c_id == thread.parent.id:
            time.sleep(1)
            # Send the view for a suggestion channel.
            embed = await SuggestionView.get_panel(self, thread.guild.id)
            await thread.send(embed=embed, view=SuggestionView())
        elif find_tag('closed', thread.parent):
            # If it could not be resolved but can be closed, add a basic panel.
            time.sleep(1)
            embed = await BasicThreadView.get_panel(self, thread.guild.id)
            await thread.send(embed=embed, view=BasicThreadView())

        # If it can be labeled as open, do so.
        open_tag = find_tag('open', thread.parent)
        if not open_tag:
            return

        if open_tag not in thread.applied_tags:
            await thread.add_tags(open_tag)

    async def on_thread_member_join(self, member: discord.ThreadMember):
        """Triggered on 'on_thread_member_join' event. Checks if the user is
        banned from the private thread, removing them as they join.
        """
        thread = member.thread
        subguild = subguilds.Manager.by_thread(thread.guild.id, thread.id)
        if not subguild:
            return

        # Remove user from the thread if they are banned.
        if member.id in subguild.banned:
            await thread.remove_user(member)

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        """Triggered on 'on_raw_reaction_add' event. If is a bound Reaction
        and Role pair, give the user the role if it is normal. If the pair is
        reversed, it will remove the role.
        """
        values = await react_processor(self, payload)
        if not values:
            return

        if values[2]:
            await values[0].remove_roles(values[1])
        else:
            await values[0].add_roles(values[1])

    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        """Triggered on 'on_raw_reaction_remove' event. If is a bound Reaction
        and Role pair, remove the role from the user if it is normal. If the
        pair is reversed, it will add the role.
        """
        values = await react_processor(self, payload)
        if not values:
            return

        if values[2]:
            await values[0].add_roles(values[1])
        else:
            await values[0].remove_roles(values[1])

    @staticmethod
    def init_run(config: DiscordConfig) -> None:
        """Initialized the Discord Bot."""
        try:
            # Set the logging.
            handler = logging.FileHandler(filename='discord.log',
                                          encoding='utf-8',
                                          mode='w')

            # Try to resolve the owner.
            owner_id: Optional[int] = None
            if config.owner_id > 0:
                owner_id = config.owner_id

            # Initialize the Discord Bot.
            dbot: DiscordBot = DiscordBot(config.prefix, owner_id)
            dbot.run(config.token, log_handler=handler,
                     log_level=logging.DEBUG)
        except KeyboardInterrupt:
            Log.print("Discord Bot killing self globally.")
