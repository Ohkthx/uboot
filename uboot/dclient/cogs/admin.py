"""Admin and Staff commands for managing the server."""
import discord
from discord.ext import commands
from discord.ext.commands import param

from managers import settings, react_roles
from dclient import DiscordBot
from dclient.views.support_request import SupportRequestView
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
            print(f"ERROR: {err}")

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

    @server.command(name="support")
    async def support(self, ctx: commands.Context):
        """Creates the support ticket button."""
        await ctx.send(embed=SupportRequestView.get_panel(),
                       view=SupportRequestView(self.bot))

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
        for attachment in ctx.message.attachments:
            print(f"{attachment.content_type} {attachment.filename}")
        await ctx.send("Not implemented yet.")

    @settings.command(name='show')
    async def settings_show(self, ctx: commands.Context) -> None:
        """Shows all of the current settings for the server."""
        if ctx.guild is None:
            return
        setting = settings.Manager.get(ctx.guild.id)

        # combines all of the server settings into a single message.
        items: list[str] = []
        for key, value in setting.__dict__.items():
            if value == 0:
                value = "unset"
            key = key.replace('_', ' ').title()
            items.append(f"{key}: {value}")
        msg = '\n'.join(items)
        await ctx.send(f"```{msg}```")

    @settings.command(name='market-channel')
    async def market_channel(self, ctx: commands.Context,
                             channel: discord.abc.GuildChannel = param(
                                 description="Market channel",
                                 default=None)) -> None:
        """Sets the channel id for the current market channel.
        Channel must be a Forum Channel.
        example:
            (prefix)server settings market-channel #market
        """
        if not ctx.guild:
            return

        channel_id = 0
        channel_str = "unset"
        if channel:
            # Make sure the channel is the correct type.
            if not isinstance(channel, discord.ForumChannel):
                await ctx.send("Channel is not a 'Forum Channel'")
                return
            channel_id = channel.id
            channel_str = f"<#{channel.id}>"

        # Save the settings for the guild.
        setting = settings.Manager.get(ctx.guild.id)
        setting.market_channel_id = channel_id
        setting.save()
        await ctx.send(f"Market channel updated to: {channel_str}")

    @settings.command(name='react-role-channel')
    async def react_role_channel(self, ctx: commands.Context,
                                 channel: discord.abc.GuildChannel = param(
                                     description="Channel for Emoji "
                                     "Reaction Roles.",
                                     default=None)) -> None:
        """Sets the channel id for the emoji reaction roles.
        Channel must be a Text Channel.
        example:
            (prefix)server settings react-role-channel #role-selection
        """
        if not ctx.guild:
            return

        channel_id = 0
        channel_str = "unset"
        if channel:
            # Make sure the channel is the correct type.
            if not isinstance(channel, discord.TextChannel):
                await ctx.send("Channel is not a basic 'Text Channel'")
                return
            channel_id = channel.id
            channel_str = f"<#{channel.id}>"

        # Save the settings for the guild.
        setting = settings.Manager.get(ctx.guild.id)
        setting.react_role_channel_id = channel_id
        setting.save()
        await ctx.send(f"React-Role channel updated to: {channel_str}")

    @settings.command(name='react-role-msg')
    async def react_role_msg(self, ctx: commands.Context,
                             message_id: int = param(
                                 description="Message Id for Emoji Reaction Roles.")):
        """Sets the message id for emoji reaction roles.
        example:
            (prefix)server settings react-role-msg 1234567890
        """
        if not ctx.guild:
            return
        if message_id < 0:
            await ctx.send("Message Id must be >= 0. Disable by setting to 0.")
            return

        # Make sure the channel has been set already.
        setting = settings.Manager.get(ctx.guild.id)
        channel_id = setting.react_role_channel_id
        if channel_id <= 0 and message_id != 0:
            await ctx.send("Please the the react-role channel id first.")
            return

        # Check if channel exists.
        msg_str = "unset"
        if message_id != 0:
            msg_str = f"'{message_id}'"
            channel = await get_channel(self.bot, channel_id)
            if not channel:
                return

            # Make sure the channel is the correct type.
            if not isinstance(channel, discord.TextChannel):
                await ctx.send("React-Role Channel is not a basic 'Text Channel'")
                return

            # Validate that the message exists.
            msg = await get_message(self.bot, channel_id, message_id)
            if not msg:
                await ctx.send(f"Could not discover message '{message_id}', "
                               "settings were not applied.")
                return

        # Save the settings for the guild.
        setting.react_role_msg_id = message_id
        setting.save()
        await ctx.send(f"React-Role Message Id updated to: {msg_str}")

    @settings.command(name='expiration')
    async def market_expiration(self, ctx: commands.Context,
                                days: int = param(
                                    description="Amount of days till "
                                    "market posts expire.")):
        """Sets the amount of days until market posts are set to expire.
        example:
            (prefix)server settings expiration 15
        """
        if not ctx.guild:
            return
        if days < 0:
            await ctx.send("Days must be >= 0. Disable by setting to 0.")
            return

        # Save the settings for the guild.
        setting = settings.Manager.get(ctx.guild.id)
        setting.expiration_days = days
        setting.save()

        days_str = "unset"
        if days > 0:
            days_str = f"{days}"
        await ctx.send(f"Expiration Days updated to: {days_str}")

    @settings.command(name='support-channel')
    async def support_channel(self, ctx: commands.Context,
                              channel: discord.abc.GuildChannel = param(
                                  description="Channel Id of the Support.",
                                  default=None)) -> None:
        """Sets the channel id for the current support channel.
        Channel must be a Text Channel.
        example:
            (prefix)server settings support-channel #support
        """
        if not ctx.guild:
            return

        channel_id = 0
        channel_str = "unset"
        if channel:
            # Make sure the channel is the correct type.
            if not isinstance(channel, discord.TextChannel):
                await ctx.send("Channel is not a basic 'Text Channel'")
                return
            channel_id = channel.id
            channel_str = f"<#{channel.id}>"

        # Save the settings for the guild.
        setting = settings.Manager.get(ctx.guild.id)
        setting.support_channel_id = channel_id
        setting.save()
        await ctx.send(f"Support channel updated to: {channel_str}")

    @settings.command(name='support-role')
    async def support_role(self, ctx: commands.Context,
                           role: discord.Role = param(
                               description="Role of the Support.",
                               default=None)) -> None:
        """Sets the role id for the current support role.
        example:
            (prefix)server settings support-role @admins
        """
        if not ctx.guild:
            return

        role_id = 0
        role_str = "unset"
        if role:
            role_id = role.id
            role_str = f"<@&{role.id}>"

        # Save the settings for the guild.
        setting = settings.Manager.get(ctx.guild.id)
        setting.support_role_id = role_id
        setting.save()
        await ctx.send(f"Support Role updated to: {role_str}")

    @settings.command(name='suggestion-channel')
    async def suggestion_channel(self, ctx: commands.Context,
                                 channel: discord.abc.GuildChannel = param(
                                     description="Channel Id of the Suggesitons.",
                                     default=None)) -> None:
        """Sets the channel id for the current suggestion channel.
        Channel must be a Forum Channel.
        example:
            (prefix)server settings suggestion-channel #suggestion-forum
        """
        if not ctx.guild:
            return

        channel_id = 0
        channel_str = "unset"
        if channel:
            # Make sure the channel is the correct type.
            if not isinstance(channel, discord.ForumChannel):
                await ctx.send("Channel is not a 'Forum Channel'")
                return
            channel_id = channel.id
            channel_str = f"<#{channel.id}>"

        # Save the settings for the guild.
        setting = settings.Manager.get(ctx.guild.id)
        setting.suggestion_channel_id = channel_id
        setting.save()
        await ctx.send(f"Suggestion channel updated to: {channel_str}")

    @settings.command(name='suggestion-reviewer-role')
    async def suggestion_reviewer_role(self, ctx: commands.Context,
                                       role: discord.Role = param(
                                           description="Role of the Suggestion Reviewer.",
                                           default=None)) -> None:
        """Sets the role id for the current suggestion reviewer role.
        example:
            (prefix)server settings suggestion-reviewer-role @reviewers
        """
        if not ctx.guild:
            return

        role_id = 0
        role_str = "unset"
        if role:
            role_id = role.id
            role_str = f"<@&{role.id}>"

        # Save the settings for the guild.
        setting = settings.Manager.get(ctx.guild.id)
        setting.suggestion_reviewer_role_id = role_id
        setting.save()
        await ctx.send(f"Suggestion Reviwer Role updated to: {role_str}")

    @settings.command(name='request-review-channel')
    async def request_review_channel(self, ctx: commands.Context,
                                     channel: discord.abc.GuildChannel = param(
                                         description="Channel Id of the Requests.",
                                         default=None)) -> None:
        """Sets the channel id for the request review channel.
        Channel must be a Text Channel.
        example:
            (prefix)server settings request-review-channel #requests
        """
        if not ctx.guild:
            return

        channel_id = 0
        channel_str = "unset"
        if channel:
            # Make sure the channel is the correct type.
            if not isinstance(channel, discord.TextChannel):
                await ctx.send("Channel is not a 'Text Channel'")
                return
            channel_id = channel.id
            channel_str = f"<#{channel.id}>"

        # Save the settings for the guild.
        setting = settings.Manager.get(ctx.guild.id)
        setting.request_review_channel_id = channel_id
        setting.save()
        await ctx.send(f"Request Review channel updated to: {channel_str}")

    @settings.command(name='sub-guild-channel')
    async def sub_guild_channel(self, ctx: commands.Context,
                                channel: discord.abc.GuildChannel = param(
                                    description="Channel Id of the "
                                    "Sub-Guilds.",
                                    default=None)) -> None:
        """Sets the channel id for the sub-guild channel.
        Channel must be a Text Channel.
        example:
            (prefix)server settings sub-guild-channel #guild-requests
        """
        if not ctx.guild:
            return

        channel_id = 0
        channel_str = "unset"
        if channel:
            # Make sure the channel is the correct type.
            if not isinstance(channel, discord.TextChannel):
                await ctx.send("Channel is not a 'Text Channel'")
                return
            channel_id = channel.id
            channel_str = f"<#{channel.id}>"

        # Save the settings for the guild.
        setting = settings.Manager.get(ctx.guild.id)
        setting.sub_guild_channel_id = channel_id
        setting.save()
        await ctx.send(f"Sub-Guild channel updated to: {channel_str}")

    @settings.command(name='lotto-role')
    async def lotto_role(self, ctx: commands.Context,
                         role: discord.Role = param(
                             description="Role of the Lotto players.",
                             default=None)) -> None:
        """Sets the role id for the current lotto role.
        example:
            (prefix)server settings lotto-role @lotto
        """
        if not ctx.guild:
            return

        role_id = 0
        role_str = "unset"
        if role:
            role_id = role.id
            role_str = f"<@&{role.id}>"

        # Save the settings for the guild.
        setting = settings.Manager.get(ctx.guild.id)
        setting.lotto_role_id = role_id
        setting.save()
        await ctx.send(f"Lotto Role updated to: {role_str}")

    @settings.command(name='lotto-winner-role')
    async def lotto_winner_role(self, ctx: commands.Context,
                                role: discord.Role = param(
                                    description="Role of the Winning Lotto players.",
                                    default=None)) -> None:
        """Sets the role id for the current winning lotto role.
        example:
            (prefix)server settings lotto-winner-role @lotto-winner
        """
        if not ctx.guild:
            return

        role_id = 0
        role_str = "unset"
        if role:
            role_id = role.id
            role_str = f"<@&{role.id}>"

        # Save the settings for the guild.
        setting = settings.Manager.get(ctx.guild.id)
        setting.lotto_winner_role_id = role_id
        setting.save()
        await ctx.send(f"Lotto Winner Role updated to: {role_str}")

    @settings.command(name='minigame-role')
    async def minigame_role(self, ctx: commands.Context,
                            role: discord.Role = param(
                                description="Role to participate in minigames.",
                                default=None)) -> None:
        """Sets the role id for the current minigame role. This allows for
        monster combat and gambling.

        example:
            (prefix)server settings minigame-role @combatant
        """
        if not ctx.guild:
            return

        role_id = 0
        role_str = "unset"
        if role:
            role_id = role.id
            role_str = f"<@&{role.id}>"

        # Save the settings for the guild.
        setting = settings.Manager.get(ctx.guild.id)
        setting.minigame_role_id = role_id
        setting.save()
        await ctx.send(f"MiniGame Role updated to: {role_str}")

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
        channel_id = setting.react_role_channel_id
        message_id = setting.react_role_msg_id

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
        channel_id = setting.react_role_channel_id
        message_id = setting.react_role_msg_id

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
        channel_id = setting.react_role_channel_id
        message_id = setting.react_role_msg_id

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
