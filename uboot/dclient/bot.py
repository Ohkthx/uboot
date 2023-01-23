"""The core of the Discord Bot and Client."""
import logging
import time
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
import discord
from discord import RawReactionActionEvent
from discord.ext import commands, tasks
from dclient.views.dm import DMDeleteView

from config import DiscordConfig
from managers import (settings, users, react_roles, tickets, subguilds,
                      entities, aliases, images, banks)
from managers.logs import Log
from .views.generic_panels import SuggestionView, BasicThreadView
from .views.entity import EntityView, HelpMeView
from .ccserver import CCServer
from .destructable import DestructableManager, Destructable
from .helper import (get_guild, get_member, get_user, thread_close, react_processor, get_channel,
                     find_tag, get_role)


intents = discord.Intents.default()
intents.message_content = True  # pylint: disable=assigning-non-slot
intents.reactions = True  # pylint: disable=assigning-non-slot
intents.members = True  # pylint: disable=assigning-non-slot
intents.guilds = True  # pylint: disable=assigning-non-slot

member_cache = discord.MemberCacheFlags(joined=True)

defaultHelp = commands.DefaultHelpCommand(no_category="HELP")


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
            Log.error("Could not remove the role from the sudoer.")


class Powerhour():
    """Powerhour is a single hour in which gold generation is increased."""

    def __init__(self, guild_id: int, channel_id: int,
                 multiplier: float, length: int) -> None:
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.multiplier = multiplier
        self.length = length
        self.timestamp = datetime.now()

    def isexpired(self) -> bool:
        """Checks if the time has elapsed and powerhour should be removed."""
        now = datetime.now()
        return now - self.timestamp > timedelta(hours=(1 * self.length))

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
                             'dclient.cogs.user',
                             'dclient.cogs.admin',
                             'dclient.cogs.private_guild',
                             'dclient.cogs.panel',
                             'dclient.cogs.test',
                             'dclient.views.test',
                             'dclient.views.dm',
                             'dclient.views.support_request',
                             'dclient.views.support_thread',
                             'dclient.views.red_button',
                             'dclient.views.private_guild_signup',
                             'dclient.views.private_guild_panel',
                             'dclient.views.user']


class DiscordBot(commands.Bot):
    """The core of the Discord Bot and Client."""

    def __init__(self, config: DiscordConfig) -> None:
        prefix = config.prefix
        owner_id: Optional[int] = None
        if config.owner_id > 0:
            owner_id = config.owner_id

        super().__init__(command_prefix=commands.when_mentioned_or(prefix),
                         owner_id=owner_id,
                         intents=intents,
                         member_cache_flags=member_cache,
                         help_command=defaultHelp)

        self.conf = config
        self.prefix = prefix
        self._extensions = cog_extensions
        self.session: Optional[aiohttp.ClientSession] = None
        self.owner: Optional[discord.User] = None
        self.ccserver: Optional[CCServer] = None

        # Initialize all of the managers and their databases.
        tickets.Manager.init("uboot.sqlite3")
        banks.Manager.init("uboot.sqlite3")
        users.Manager.init("uboot.sqlite3")
        react_roles.Manager.init("uboot.sqlite3")
        subguilds.Manager.init("uboot.sqlite3")
        aliases.Manager.init("uboot.sqlite3")
        entities.Manager.init()
        images.Manager.init()

        self.sudoer: Optional[Sudoer] = None
        self.last_button: Optional[discord.Message] = None
        self.powerhours: dict[int, Powerhour] = {}

    def set_sudoer(self, user: discord.Member, role: discord.Role,
                   length: int) -> None:
        """Sets the sudoer temporarily."""
        self.sudoer = Sudoer(user, role, length)

    def start_powerhour(self, guild_id: int, channel_id: int,
                        multiplier: float, length: int = 1) -> None:
        """Starts a powerhour for the selected guild."""
        self.powerhours[guild_id] = Powerhour(guild_id, channel_id,
                                              multiplier,
                                              length)

    async def add_entity(self, msg: discord.Message, user: discord.Member,
                         mob: entities.Entity) -> None:
        """Adds an entity that will be tracked by a destructable view."""
        if not isinstance(user, discord.Member):
            return

        # Checks if the user is in combat or not.
        user_l = users.Manager.get(user.id)
        if user_l.incombat:
            return

        user_l.set_combat(True)

        # Remove all old entities for the user.
        category = Destructable.Category.MONSTER
        await DestructableManager.remove_many(user.id, True, category)

        timeout: int = 30
        entity_view = EntityView(user, mob)
        if user_l.isbot or self.user == user or mob.isboss:
            timeout = 3600
            exp = mob.get_exp(user_l.level)
            entity_view = HelpMeView(user, mob, exp, 0)

        embed = entity_view.get_panel()

        file: Optional[discord.File] = None
        if mob.image:
            file = images.Manager.get(mob.image)
            if file:
                url = f"attachment://{mob.image}"
                embed.set_thumbnail(url=url)

        new_msg = await msg.reply(embed=embed, view=entity_view, file=file)

        # Create a destructable view for the entity.
        destruct = Destructable(category, user.id, timeout, True)
        destruct.set_message(message=new_msg)
        destruct.set_callback(entity_view.loss_callback)

        user_l.monsters += 1
        user_l.save()

        Log.info(f"Spawned {mob.name} on {user}.",
                 guild_id=user.guild.id, user_id=user.id)

    async def setup_hook(self) -> None:
        """Overrides the setup hook, loading all extensions (views/cogs) and
        sets additional persistent views. Initializes the loops that checks
        for updates.
        """
        self.session = aiohttp.ClientSession()
        for ext in self._extensions:
            await self.load_extension(ext)

        if self.owner_id:
            self.owner = await get_user(self, self.owner_id)

        for guild in self.guilds:
            settings.Manager.init(guild.id)

        # Set up the CCServer
        if self.owner:
            dmchannel = await get_channel(self, self.conf.ccdm_id)
            if dmchannel and isinstance(dmchannel, discord.TextChannel):
                # Make sure we have cached all of the guild threads.
                for thread in await dmchannel.guild.active_threads():
                    dmchannel.guild._add_thread(thread)
                self.ccserver = CCServer(self, self.owner, dmchannel)

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

    def rm_react_role(self, role_id: int) -> bool:
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
            if random.randint(0, 34) == 0:
                try:
                    await self.last_button.delete()
                except BaseException:
                    pass
                finally:
                    self.last_button = None

        # Purge all expired destructables.
        await DestructableManager.purge()

        # Check powerhours, if they are expired they will be removed.
        delete: list[int] = []
        for guild_id, powerhour in self.powerhours.items():
            if powerhour.isexpired():
                await powerhour.send_end(self)
                delete.append(guild_id)
        # Remove from memory.
        for i in delete:
            del self.powerhours[i]

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
            if 0 in (setting.market.channel_id, setting.market.expiration):
                continue

            # Get the market channel and make sure it is a forum channel.
            market_ch = await get_channel(self, setting.market.channel_id)
            if not market_ch or not isinstance(
                    market_ch, discord.ForumChannel):
                return

            reason = "post expired."
            for thread in market_ch.threads:
                if thread.archived or not thread.created_at:
                    # Ignore archived or errored posts.
                    continue

                # Calculate if it is expired.
                elapsed = datetime.now(timezone.utc) - thread.created_at
                if elapsed < timedelta(days=setting.market.expiration):
                    # Not expired, continue.
                    continue

                # Expired, update the name.
                if "[expired]" not in thread.name.lower():
                    await thread.edit(name=f"[EXPIRED] {thread.name}")

                # Close the thread.
                await thread_close(['none'], 'expired', thread, reason)

                msg = f"Your post '{thread.name}' expired."
                owner = await get_member(self, guild.id, thread.owner_id)
                if not owner:
                    continue

                view = DMDeleteView(self)
                await owner.send(content=msg, view=view)

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
        # Do not add messages or gold if the user is the bot.
        if not self.user or msg.author == self.user or msg.author.bot:
            return

        # Process if it is a command.
        ctx = await self.get_context(msg)
        if ctx.command:
            await self.invoke(ctx)

            result: str = "failed" if ctx.command_failed else "called"
            guild_id = 0 if not msg.guild else msg.guild.id
            cmd = ctx.command.qualified_name
            return Log.command(f"{msg.author} {result} the ({cmd}) command.",
                               guild_id=guild_id, user_id=msg.author.id)

        # Set the 'owner' for the bot.
        if not self.owner_id:
            await self.is_owner(msg.author)

        user = users.Manager.get(msg.author.id)

        # Log all DMs sent to the bot.
        if self.ccserver and self.ccserver.is_dm(msg):
            if not self.owner_id or user.id == self.owner_id:
                return

            return await self.ccserver.dmlog(msg)

        # Process DM responses.
        if self.ccserver and self.ccserver.is_response(msg):
            await self.ccserver.process(msg)
            return

        # Add message and gold to user, saving to database.
        if not msg.guild or not isinstance(msg.author, discord.Member):
            return

        last_message: datetime = user.last_message
        powerhour = self.powerhours.get(msg.guild.id)
        multiplier: float = 1.0 if not powerhour else powerhour.multiplier
        user.add_message(multiplier)
        user.save()

        # Check that the user has the minigame role.
        role_id = settings.Manager.get(msg.guild.id).minigame.role_id
        minigame_role = await get_role(self, msg.guild.id, role_id)
        if not minigame_role or minigame_role not in msg.author.roles:
            return

        if user.incombat:
            return

        loc = user.c_location
        difficulty = user.difficulty

        # Check passive taunt.
        entity: Optional[entities.Entity] = None
        if datetime.now() - last_message >= timedelta(hours=12):
            entity = entities.Manager.check_spawn(loc, difficulty,
                                                  False, False, True)
        else:
            # Try to spawn natural entity..
            entity = entities.Manager.check_spawn(loc, difficulty,
                                                  powerhour is not None,
                                                  user.powerhour is not None,
                                                  False)
        if entity:
            await self.add_entity(msg, msg.author, entity)

    async def on_thread_create(self, thread: discord.Thread) -> None:
        """Triggered on the 'on_thread_create' event. Used to appropriately
        label threads as 'open' or their proper equivalent. Creates the panel
        if it has an assigned one.
        """
        if not thread.guild:
            # Ignore if the guild cannot be identified.
            return

        if not isinstance(thread.parent, discord.ForumChannel):
            # Either a private or public text channel thread.
            if self.ccserver:
                self.ccserver.add_thread(thread)
            return

        setting = settings.Manager.get(thread.guild.id)

        # If it is a suggestion channel... add the panel.
        c_id = setting.suggestion.channel_id
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

    async def on_thread_delete(self, thread: discord.Thread) -> None:
        """Triggered on 'on_thread_delete' event."""
        if not isinstance(thread.parent, discord.ForumChannel):
            # Either a private or public text channel thread.
            if self.ccserver:
                self.ccserver.remove_thread(thread)

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        """Triggered on 'on_raw_reaction_add' event. If is a bound Reaction
        and Role pair, give the user the role if it is normal. If the pair is
        reversed, it will remove the role.
        """
        values = await react_processor(self, payload)
        if not values:
            return

        user, role, reverse = values

        try:
            if reverse:
                Log.action(f"Removing {role.name} role from {user}.",
                           guild_id=role.guild.id, user_id=user.id)
                await user.remove_roles(role)
            else:
                Log.action(f"Adding {role.name} role to {user}.",
                           guild_id=role.guild.id, user_id=user.id)
                await user.add_roles(role)
        except BaseException as exc:
            action = 'add' if not reverse else 'remove'
            Log.error(f"Could not {action} {role.name} role to {str(user)}.\n"
                      f"{exc}",
                      guild_id=role.guild.id, user_id=user.id)

    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        """Triggered on 'on_raw_reaction_remove' event. If is a bound Reaction
        and Role pair, remove the role from the user if it is normal. If the
        pair is reversed, it will add the role.
        """
        values = await react_processor(self, payload)
        if not values:
            return

        user, role, reverse = values

        try:
            if reverse:
                Log.action(f"Adding {role.name} role to {user}.",
                           guild_id=role.guild.id, user_id=user.id)
                await user.add_roles(role)
            else:
                Log.action(f"Removing {role.name} role from {user}.",
                           guild_id=role.guild.id, user_id=user.id)
                await user.remove_roles(role)
        except BaseException as exc:
            action = 'add' if not reverse else 'remove'
            Log.error(f"Could not {action} {role.name} role to {str(user)}.\n"
                      f"{exc}",
                      guild_id=role.guild.id, user_id=user.id)

    @staticmethod
    def init_run(config: DiscordConfig) -> None:
        """Initialized the Discord Bot."""
        try:
            # Set the logging.
            handler = logging.FileHandler(filename='discord.log',
                                          encoding='utf-8',
                                          mode='w')

            # Initialize the Discord Bot.
            dbot: DiscordBot = DiscordBot(config)
            dbot.run(config.token, log_handler=handler,
                     log_level=logging.DEBUG)
        except KeyboardInterrupt:
            Log.debug("Discord Bot killing self globally.")
