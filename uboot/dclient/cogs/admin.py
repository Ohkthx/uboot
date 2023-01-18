"""Admin and Staff commands for managing the server."""
import os
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord.ext.commands import param

from managers import settings, react_roles
from managers.logs import Log, LogType, Manager as LogManager
from dclient import DiscordBot
from dclient.helper import get_channel, get_message, get_member, get_role, get_role_by_name


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

        # Calculate the servers age based on when they joined Discord.
        age = datetime.now(timezone.utc) - guild.created_at
        year_str = '' if age.days // 365 < 1 else f"{age.days//365} year(s), "
        day_str = '' if age.days % 365 == 0 else f"{int(age.days%365)} day(s)"

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

        embed.description = f"**server name**: {guild.name}\n"\
            f"**id**: {guild.id}\n"\
            f"**age**: {year_str}{day_str}\n\n"\
            f"**images**: {banner}{icon}\n"\
            f"**members**: {members}\n"\
            f"**channels**: {len(guild.channels)}\n"\
            f"**roles**: {len(guild.roles)}\n"

        await ctx.reply(embed=embed)

    @commands.is_owner()
    @server.command(name="sudo")
    async def sudo(self, ctx: commands.Context,
                   length: int = param(description="Amount of time to "
                                       "hold the role.",
                                       default=5)):
        """Elevatates permissions."""
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

        tlog: LogType = LogType.INFO

        try:
            tlog = LogType(logtype)
        except BaseException:
            await ctx.send(f"Invalid log type of '{logtype}'", delete_after=30)
            return

        logs = LogManager.get_guild_type(ctx.guild.id, tlog, amount)
        log_res: list[str] = []
        for log in logs:
            log_res.append(f"> [{log.timestamp}] {log.message}")

        log_full: str = "> none"
        if len(log_res) > 0:
            log_full = '\n'.join(log_res)

        if len(log_full) > 2000:
            await ctx.send("Too large of a request of logs.",
                           delete_after=30)
            return

        embed = discord.Embed(title=f"Server {tlog.name} Logs")
        embed.color = discord.Colour.blurple()
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
        log_res: list[str] = []
        for log in logs:
            log_res.append(f"> [{log.timestamp}] {log.message}")

        log_full: str = "> none"
        if len(log_res) > 0:
            log_full = '\n'.join(log_res)

        if len(log_full) > 2000:
            await ctx.send("Too large of a request of logs.",
                           delete_after=30)
            return

        embed = discord.Embed(title=f"Server Logs for User: {user_id}")
        embed.color = discord.Colour.blurple()
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
        """Adds a specified role by Id to all current guild members.

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

        # Give the role to all of the members.
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
        """Shows all of the current settings for the server."""
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
        embed.color = discord.Colour.blurple()
        embed.set_footer(text="Output above are potential errors.")
        embed.description = f"**Users who reacted**: {len(users)}\n"\
            f"**Users in role**: {len(role.members)}\n\n"\
            "__**Has reacted, no role**__:\n"\
            f"{total_missing}\n\n"\
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

        # Iterate all of the react-roles for the server and combine them.
        res: list[str] = []
        rroles = react_roles.Manager.guild_roles(ctx.guild.id)
        for rrole in rroles:
            role = ctx.guild.get_role(rrole.role_id)
            if not role:
                continue
            res.append(f"{rrole.reaction} => {role.name} ({rrole.role_id})")
        if len(res) == 0:
            await ctx.send('no bound reactions to roles.')
            return
        text = '\n'.join(res)
        await ctx.send(f"```{text}```")


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    await bot.add_cog(Admin(bot))
