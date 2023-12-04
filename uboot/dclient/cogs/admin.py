"""Admin and Staff commands for managing the server."""
from datetime import datetime
import os
import html

import discord
from discord.ext import commands
from discord.ext.commands import param

from managers import settings, react_roles, users
from managers.logs import Log, LogType, Manager as LogManager
from dclient.bot import DiscordBot
from dclient.helper import get_channel, get_message, get_member, get_role, get_role_by_name, convert_age


async def convert_logs(ctx: commands.Context,
                       logs: list[Log],
                       ) -> str:
    """Takes a list of logs and makes it pretty."""
    log_res: list[str] = []
    for log in logs:
        log_res.append(f"> [{log.timestamp}] {log.message}")

    log_full: str = "> none"
    if len(log_res) > 0:
        log_full = '\n'.join(log_res)

    if len(log_full) > 2000:
        await ctx.send("Too large of a request of logs.",
                       delete_after=30)
        return ''
    return log_full


def parse_recent_timestamp(filename: str):
    """Function to parse the most recent timestamp from the file."""
    recent = None
    if not os.path.exists(filename):
        return recent

    with open(filename, 'r') as file:
        for line in file:
            try:
                # Extract the timestamp from each line.
                items: list[str] = line.split(",")
                timestamp: datetime = datetime.fromisoformat(items[0])
                source: str = items[1]

                # Update the most recent timestamp.
                if recent is None or (source == "discord" and timestamp > recent):
                    recent = timestamp
            except Exception:
                # Ignore lines that do not contain a valid timestamp
                continue

    return recent


def sanitize_text(text: str) -> str:
    """Sanitizes text for CSV format."""
    if text is None:
        return ""

    # Decode HTML entities, replace special characters.
    text = html.unescape(text).replace('\r', "").strip()
    text = text.replace('​', '').replace('’', '\'')
    text = text.replace('"', "\"\"")

    # Remove whitespace and double quote on special characters..
    text = " ".join(line.strip() for line in text.split("\n") if line.strip())
    if ',' in text or '\n' in text or '\"' in text:
        text = f'"{text}"'

    return text


def to_csv(timestamp: datetime, level: int, channel_id: int, id: int, message: str):
    """Converts into proper CSV format."""
    ts = f"{timestamp.isoformat()}".split(".")[0].split("+")[0]
    return f'{ts},discord,{level},{channel_id},{id},{sanitize_text(message)}'


class Admin(commands.Cog):
    """Grouped administrative commands for managing a server.
    Additional 'help' information on subgroups:
        (prefix)help server
        (prefix)help server settings
        (prefix)help server react-role
    """

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot

    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    @commands.group(name='server')
    async def server(self, ctx: commands.Context) -> None:
        """Grouped administrative commands for managing a server.
        Additional 'help' information on subgroups:
            (prefix)help server settings
            (prefix)help server react-role
        """
        if not ctx.invoked_subcommand:
            await ctx.send('invalid server command.')

    @server.command(name="info")
    async def info(self, ctx: commands.Context) -> None:
        """Pulls basic server statistics along with links to all images.

        examples:
            (prefix)server info
        """
        guild = ctx.guild
        if not guild:
            return

        # Get the URLs for images.
        banner = f" [banner]({guild.banner.url})" if guild.banner else ""
        icon = f" [icon]({guild.icon.url})" if guild.icon else ""

        # Calculate the member count.
        members: int = -1
        if guild.member_count and guild.approximate_member_count:
            true, approx = guild.member_count, guild.approximate_member_count
            members = true if true > approx else approx
        elif guild.member_count:
            members = guild.member_count
        elif guild.approximate_member_count:
            members = guild.approximate_member_count

        embed = discord.Embed(color=discord.Color.blurple())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.description = f"**server name**: {guild.name}\n" \
                            f"**id**: {guild.id}\n" \
                            f"**age**: {convert_age(guild.created_at)}\n\n" \
                            f"**images**: {banner}{icon}\n" \
                            f"**members**: {members}\n" \
                            f"**channels**: {len(guild.channels)}\n" \
                            f"**roles**: {len(guild.roles)}\n"

        await ctx.reply(embed=embed)

    @server.command(name="extract")
    async def extract(self, ctx: commands.Context,
                      user_id: int = param(
                          description="Id of the user to pull messages from."),
                      amount: int = param(
                          description="Amount of messages to obtain."),
                      channel_id: int = param(
                          description="Optional Channel Id to search.", default=None),
                      ) -> None:
        """Pulls 'n' messages from the user specified.

        example:
            (prefix)server extract @Gatekeeper 10
        """
        if not ctx.guild or amount < 1:
            return

        await ctx.message.delete()
        await ctx.send(f"Starting extraction.", delete_after=5)

        # Initialze where to store the results.
        directory: str = "extracted"
        filename: str = f"{directory}/{user_id}.csv"
        if not os.path.exists(directory):
            os.makedirs(directory)

        timestamp = None
        try:
            timestamp = parse_recent_timestamp(filename)
        except BaseException:
            timestamp = None

        messages: list[str] = []

        channels: list[discord.TextChannel] = []
        if channel_id:
            channel = ctx.guild.get_channel(channel_id)
            if channel:
                channels = [channel]
        else:
            channels = ctx.guild.text_channels

        print(f"Starting search.")
        for channel in channels:
            total = 0
            try:
                async for msg in channel.history(limit=amount, after=timestamp):
                    total += 1
                    print(
                        f"  Search: {channel.name}, {channel.id} ({total})", end="\r")
                    if msg.author.id != user_id:
                        continue
                    elif not msg.content or msg.content == "":
                        continue

                    line = to_csv(msg.created_at, 0, channel.id,
                                  msg.id, msg.content)
                    messages.append(line)
            except discord.Forbidden:
                # Skip channels where the bot does not have permission to view message history
                continue
            print(f"  Finished: {channel.name}, {channel.id} ({total})")
        print(f"Finished search, {len(messages)} messages.")

        if len(messages) > 0:
            # Add header if new file.
            if not os.path.exists(filename):
                messages.insert(
                    0, "timestamp,platform,level,parent_id,id,text")

            # Write the changes to file.
            with open(filename, "a") as file:
                file.write("\n".join(messages) + "\n")

        if not os.path.exists(filename):
            await ctx.author.send("No messages exist.")
            return

        try:
            await ctx.author.send(file=discord.File(
                filename, description=f"{user_id} log."))
        except BaseException:
            await ctx.author.send("Could not send file.")

    @commands.is_owner()
    @server.command(name="sudo")
    async def sudo(self, ctx: commands.Context,
                   length: int = param(description="Amount of time to "
                                                   "hold the role.",
                                       default=5)):
        """Elevates permissions."""
        await ctx.message.delete()
        if not self.bot.user or not ctx.guild:
            return

        # Get the users Member account.
        user = await get_member(self.bot, ctx.guild.id, ctx.author.id)
        if not user:
            return

        # Get the role the bot belongs to.
        bot_role = await get_role_by_name(self.bot, ctx.guild.id,
                                          self.bot.user.name)
        if not bot_role:
            return

        try:
            # Check all roles, trying to find the lowest ranked role with
            # enough permissions to move the user.
            for role in ctx.guild.roles:
                if role.position >= bot_role.position or role.is_bot_managed():
                    continue

                # Give the role to the user and set the expiration timer.
                if role.permissions.administrator:
                    await user.add_roles(role)
                    await ctx.author.send(f"Given the {role.name} role.")
                    self.bot.set_sudoer(user, role, length * 60)
                    return
        except BaseException as err:
            Log.error(f"Error happened while performing SUDO, {err}",
                      guild_id=ctx.guild.id, user_id=user.id)

    @server.group(name="twitch", aliases=("tw",))
    async def twitch(self, ctx: commands.Context) -> None:
        """Manages twitch integration.

        examples:
            (prefix)server twitch show
            (prefix)server twitch add 123456789 gatekeeper
            (prefix)server twitch rm 123456789
        """
        if ctx.invoked_subcommand is None:
            await ctx.send('invalid twitch command.')

    @twitch.command(name="show", aliases=("list",))
    async def twitch_show(self, ctx: commands.Context) -> None:
        """Shows all currently assigned streamers.

        example:
            (prefix)server twitch show
        """
        if not ctx.guild:
            return

        setting = settings.Manager.get(ctx.guild.id)
        if not setting:
            await ctx.send("Guild settings could not be found.")
            return

        all_users = users.Manager.get_all()
        streamers = [u for u in all_users if u.is_streamer]

        streamer_text = []
        for s in streamers:
            # Get the users Member account.
            streamer_text.append(f"<@{s.id}>: {s.id} => {s.stream_name}")

        if len(streamer_text) == 0:
            streamer_text = ["None"]

        # Build the description to display.
        full_text = "\n".join(streamer_text)
        titles_str = "\n".join(setting.twitch.titles)
        titles = f"**Stream Titles:**\n{titles_str}"
        desc = f"{titles}\n\n**Users:**\n{full_text}"

        embed = discord.Embed(title=f"Current Streamers")
        embed.colour = discord.Colour.blurple()
        embed.description = desc
        await ctx.send(embed=embed)

    @twitch.command(name="add")
    async def twitch_add(self, ctx: commands.Context,
                         user: discord.User = param(
                             description="Id of the user to make a streamer.",
                         ),
                         name: str = param(
                             description="Twitch username."),
                         ) -> None:
        """Add a user as a streamer.

        example:
            (prefix)server twitch add 1234567890 gatekeeper
        """
        if not ctx.guild:
            return

        user_l = users.Manager.get(user.id)
        if not user_l:
            await ctx.send("could not identify the user.")
            return

        setting = settings.Manager.get(ctx.guild.id)
        if not setting:
            await ctx.send("Guild settings could not be found.")
            return

        # Get the role to assign to the new streamer.
        twitch_role = await get_role(self.bot, ctx.guild.id, setting.twitch.role_id)
        if not twitch_role:
            await ctx.send("Twitch role could not be found.")
            return

        # Get the member profile to pull current roles.
        member = await get_member(self.bot, ctx.guild.id, user.id)
        if not member:
            await ctx.send("Member could not be found.")
            return

        if twitch_role in member.roles:
            await ctx.send("Twitch role already added.")
            return

        # Add the role.
        try:
            await member.add_roles(twitch_role)
        except BaseException as exc:
            Log.error(f"Could not add {user} to twitch role.\n{exc}",
                      guild_id=ctx.guild.id, user_id=user.id)
            await ctx.send("Could not update the role of the user.")
            return

        # Update the user to a streamer.
        user_l.is_streamer = True
        user_l.stream_name = name
        user_l.save()

        await ctx.send("User has been added as a streamer.")

    @twitch.command(name="remove", aliases=("rm",))
    async def twitch_remove(self, ctx: commands.Context,
                            user: discord.User = param(
                                description="Id of the user to make a streamer.",
                            )) -> None:
        """Remove a user as a streamer.

        example:
            (prefix)server twitch remove 1234567890
        """
        if not ctx.guild:
            return

        user_l = users.Manager.get(user.id)
        if not user_l:
            await ctx.send("could not identify the user.")
            return

        setting = settings.Manager.get(ctx.guild.id)
        if not setting:
            await ctx.send("Guild settings could not be found.")
            return

        # Get the role to remove from the streamer.
        twitch_role = await get_role(self.bot, ctx.guild.id, setting.twitch.role_id)
        if not twitch_role:
            await ctx.send("Twitch role could not be found.")
            return

        # Get the member profile to pull current roles.
        member = await get_member(self.bot, ctx.guild.id, user.id)
        if not member:
            await ctx.send("Member could not be found.")
            return

        # Remove the role.
        roles = [r for r in member.roles if r != twitch_role]
        try:
            await member.remove_roles(twitch_role)
        except BaseException as exc:
            Log.error(f"Could not remove {user} from twitch role.\n{exc}",
                      guild_id=ctx.guild.id, user_id=user.id)
            await ctx.send("Could not update the role of the user.")
            return

        # Remove the user from being a streamer.
        user_l.is_streamer = False
        user_l.save()

        await ctx.send("User has been removed as a streamer.")

    @server.group(name="log", aliases=("logs",))
    async def logs(self, ctx: commands.Context) -> None:
        """Gets various logs based on its type or the user id provided.

        examples:
            (prefix)server logs type 1 20
            (prefix)server logs user 123456789 20
        """
        if ctx.invoked_subcommand is None:
            await ctx.send('invalid logs command.')

    @logs.command(name="type")
    async def logs_type(self, ctx: commands.Context,
                        logtype: int = param(
                            description="Type of log to display."),
                        amount: int = param(
                            description="Amount of logs to display."),
                        ) -> None:
        """Shows logs for the server based on type.
        Types are numeric values:
            1: INFO
            2: DEBUG
            3: ERROR
            4: COMMAND
            5: ACTION
            6: PLAYER

        example:
            (prefix)server logs type 1 10
        """
        if not ctx.guild or amount < 1:
            return

        try:
            tlog = LogType(logtype)
        except BaseException:
            await ctx.send(f"Invalid log type of '{logtype}'", delete_after=30)
            return

        logs = LogManager.get_guild_type(ctx.guild.id, tlog, amount)
        log_full = await convert_logs(ctx, logs)
        if log_full == '':
            return

        embed = discord.Embed(title=f"Server {tlog.name} Logs")
        embed.colour = discord.Colour.blurple()
        embed.description = log_full
        await ctx.send(embed=embed)

    @logs.command(name="user")
    async def logs_user(self, ctx: commands.Context,
                        user_id: int = param(
                            description="Id of the user to pull logs for."),
                        amount: int = param(
                            description="Amount of logs to display."),
                        ) -> None:
        """Shows logs for the server based on the user id provided.

        example:
            (prefix)server logs user 1234567890 10
        """
        if not ctx.guild or amount < 1:
            return

        logs = LogManager.get_guild_user(ctx.guild.id, user_id, amount)
        log_full = await convert_logs(ctx, logs)
        if log_full == '':
            return

        embed = discord.Embed(title=f"Server Logs for User: {user_id}")
        embed.colour = discord.Colour.blurple()
        embed.description = log_full
        await ctx.send(embed=embed)

    @server.command(name='remove', aliases=("rm",))
    async def rm(self, ctx: commands.Context,
                 limit: int = param(
                     description="Amount of messages to delete.")) -> None:
        """Removes 'n' amount of messages.
        example:
            (prefix)server remove 10
        """
        channel = ctx.channel
        if isinstance(channel, (discord.Thread, discord.TextChannel)):
            await channel.purge(limit=limit + 1)

    @server.command(name='add-role-all')
    async def add_role_all(self, ctx: commands.Context,
                           role_id: int = param(
                               description="Id of the role to add to every "
                                           "member.")):
        """Adds a specified role by ID to all current guild members.

        example:
            (prefix)server add-role-all 1234567890
        """
        if not ctx.guild:
            return

        if role_id <= 0:
            await ctx.send("role id cannot be <= 0.")
            return

        # Check if the role exists.
        guild_role = ctx.guild.get_role(role_id)
        if not guild_role:
            await ctx.send("could not identify the targeted role.")
            return

        # Give the role to all the members.
        added: int = 0
        async for member in ctx.guild.fetch_members(limit=None):
            if member.bot or guild_role in member.roles:
                continue
            added += 1
            await member.add_roles(guild_role)

        await ctx.send(f"**{guild_role.name}** role added to {added} members.")

    @server.group(name="settings", aliases=("setting",))
    async def settings(self, ctx: commands.Context) -> None:
        """Set various server specific settings for the discord bot.
        Information on specific settings:
            (prefix)help server settings [command]

        examples:
            (prefix)server settings market-channel #auction-house
            (prefix)server settings expiration 10
        """
        if ctx.invoked_subcommand is None:
            await ctx.send('invalid setting command.')

    @settings.command(name='upload', aliases=("ul",))
    async def upload(self, ctx: commands.Context) -> None:
        """Upload a file for the settings for your server.
        Not implemented yet.

        example:
            (prefix)settings upload [file]
        """
        guild = ctx.guild
        if not guild:
            return

        if len(ctx.message.attachments) == 0:
            await ctx.send("No file attached.", delete_after=30)
            return

        for attachment in ctx.message.attachments:
            if not os.path.exists("configs"):
                os.makedirs("configs")

            try:
                with open(f"configs/temp_{guild.id}.ini", mode='wb') as bfile:
                    bfile.write(await attachment.read())
                settings.Manager.get(guild.id).update_config()
            except BaseException as exc:
                msg = f"Could not complete upload command, {exc}"
                await ctx.send(msg, delete_after=30)
                return Log.error(msg, guild_id=guild.id)
        await ctx.send("Guild settings updated successfully.")

    @settings.command(name='show')
    async def settings_show(self, ctx: commands.Context) -> None:
        """Shows all the current settings for the server."""
        if ctx.guild is None:
            return
        setting = settings.Manager.get(ctx.guild.id)

        file = discord.File(setting.filename, f"{setting.guild_id}.ini")
        # url = f"attachment://{setting.filename}"
        await ctx.send(file=file)

    @server.group(name="react-role")
    async def react_role(self, ctx: commands.Context) -> None:
        """Used to bind or unbind emoji reactions to roles.

        examples:
            (prefix)server react-role bind 😄 1234567890
            (prefix)server react-role bind 😄 1234567890 True
            (prefix)server react-role unbind 😄 1234567890
        """
        if not ctx.invoked_subcommand:
            await ctx.send('invalid react-role command.')

    @react_role.command(name='verify')
    async def verify(self,
                     ctx: commands.Context,
                     emoji: str = param(description="Emoji assigned to role.")):
        """Checks all of those who have reacted and ensures if they have the
        appropriate role or not.

        examples:
            (prefix)server react-role verify 😄
        """
        if not ctx.guild:
            return await ctx.send("not currently in a guild.")

        # Get the settings for the server.
        setting = settings.Manager.get(ctx.guild.id)
        channel_id = setting.reactrole.channel_id
        message_id = setting.reactrole.msg_id

        if channel_id <= 0:
            await ctx.send("react-role channel id is unset, please set it "
                           "with settings command.")
            return
        if message_id <= 0:
            await ctx.send("react-role message id is unset, please set it "
                           "with settings command.")
            return

        # Verify the channel exists.
        react_ch = await get_channel(self.bot, channel_id)
        if not react_ch or not isinstance(react_ch, discord.TextChannel):
            await ctx.send("invalid channel id provided or channel type.")
            return

        # Get the message the reactions are attached to.
        react_msg = await get_message(self.bot, channel_id, message_id)
        if not react_msg:
            await ctx.send("could not identify the reaction-role message.")
            return

        react_role = react_roles.Manager.find(ctx.guild.id, emoji)
        if not react_role:
            await ctx.send("that emoji is not current bound.", delete_after=15)
            return

        # Get the reaction from the message.
        reactions = react_msg.reactions
        reaction = next((x for x in reactions if x.emoji == emoji), None)
        if not reaction:
            await ctx.send("reaction could not be found.", delete_after=15)
            return

        # Check those who are missing the role but should have it.
        missing_role: list[str] = []
        users: list[discord.Member] = []
        async for user in reaction.users():
            if user.bot or not isinstance(user, discord.Member):
                continue
            users.append(user)
            if not user.get_role(react_role.role_id):
                missing_role.append(f"> **{user}** ({user.id})")

        # Check those who have the role but should not.
        role = await get_role(self.bot, ctx.guild.id, react_role.role_id)
        if not role:
            await ctx.send("role no longer exists it appears.", delete_after=15)
            return

        has_role: list[str] = []
        for member in role.members:
            if member not in users:
                has_role.append(f"> **{member}** ({member.id})")

        # Build the text.
        total_missing = "> none"
        total_has = "> none"
        if len(missing_role) > 0:
            total_missing = '\n'.join(missing_role)
        if len(has_role) > 0:
            total_has = '\n'.join(has_role)

        embed = discord.Embed(title="Reaction Role Verification")
        embed.colour = discord.Colour.blurple()
        embed.set_footer(text="Output above are potential errors.")
        embed.description = f"**Users who reacted**: {len(users)}\n" \
                            f"**Users in role**: {len(role.members)}\n\n" \
                            "__**Has reacted, no role**__:\n" \
                            f"{total_missing}\n\n" \
                            f"__**Has role, no reaction**__:\n{total_has}"
        await ctx.send(embed=embed)

    @react_role.command(name='bind')
    async def bind(self,
                   ctx: commands.Context,
                   emoji: str = param(description="Emoji to represent role."),
                   role_id: int = param(description="Numeric Id of the role."),
                   reverse: bool = param(description="Reverse assignment, "
                                                     "selecting reaction removes role.",
                                         default=False)):
        """Binds an emoji that can be reacted to for role assignment.
        Only built-in emojis are currently supported.

        Default behaviour is 'reverse' being false, which means that
        reacting to the message GRANTS the role. If 'reverse' is set to
        'True' then selecting a reaction will REMOVE the bound role.

        examples:
            (prefix)server react-role bind 😄 1234567890
            (prefix)server react-role bind 😄 1234567890 True
        """
        if not ctx.guild or role_id <= 0:
            return await ctx.send("role id cannot be <= 0.")

        # Get the settings for the server.
        setting = settings.Manager.get(ctx.guild.id)
        channel_id = setting.reactrole.channel_id
        message_id = setting.reactrole.msg_id

        if channel_id <= 0:
            await ctx.send("react-role channel id is unset, please set it "
                           "with settings command.")
            return
        if message_id <= 0:
            await ctx.send("react-role message id is unset, please set it "
                           "with settings command.")
            return

        # Verify the channel exists.
        react_ch = await get_channel(self.bot, channel_id)
        if not react_ch or not isinstance(react_ch, discord.TextChannel):
            await ctx.send("invalid channel id provided or channel type.")
            return

        # Get the message the reactions are attached to.
        react_msg = await get_message(self.bot, channel_id, message_id)
        if not react_msg:
            await ctx.send("could not identify the reaction-role message.")
            return

        # Check if the role exists.
        guild_role = ctx.guild.get_role(role_id)
        if not guild_role:
            return await ctx.send("could not identify the targeted role.")

        # Add the base reaction to the message to represent the role.
        try:
            await react_msg.add_reaction(emoji)
        except BaseException:
            await ctx.send("could not add emoji, may be custom or invalid.")
            return

        msg = "role may already be bound."
        added = self.bot.add_react_role(emoji, role_id, ctx.guild.id, reverse)
        if added:
            msg = f"reaction bound to **{guild_role.name}**."
        await ctx.send(msg)

    @react_role.command(name='unbind')
    async def unbind(self,
                     ctx: commands.Context,
                     emoji: str = param(description="Emoji to unbind."),
                     role_id: int = param(description="Numeric Id of the role.")):
        """Unbinds an emoji from role assignment.

        example:
            (prefix)server react-role unbind 😄 1234567890
        """
        if not ctx.guild:
            return

        setting = settings.Manager.get(ctx.guild.id)
        channel_id = setting.reactrole.channel_id
        message_id = setting.reactrole.msg_id

        # Get the message the reactions are attached to.
        react_msg = await get_message(self.bot, channel_id, message_id)
        if react_msg and self.bot.user:
            # Remove the base reaction to the message to represent the role.
            await react_msg.remove_reaction(emoji, self.bot.user)

        # Remove the role locally.
        msg = "role may already be unbound."
        added = self.bot.rm_react_role(role_id)
        if added:
            msg = "reaction unbound from role."
        await ctx.send(msg)

    @react_role.command(name='show')
    async def react_role_show(self, ctx: commands.Context):
        """Shows a list of currently bound emojis to roles."""
        # Make sure the guild is valid.
        if not ctx.guild:
            await ctx.send("could not identify the guild.")
            return

        # Iterate all the react-roles for the server and combine them.
        res: list[str] = []
        for react_role in react_roles.Manager.guild_roles(ctx.guild.id):
            role = ctx.guild.get_role(react_role.role_id)
            react = react_role.reaction
            if not role:
                continue
            res.append(f"{react} => {role.name} ({role.id})")
        if len(res) == 0:
            await ctx.send('no bound reactions to roles.')
            return
        text = '\n'.join(res)
        await ctx.send(f"```{text}```")


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    await bot.add_cog(Admin(bot))
