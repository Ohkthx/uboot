from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import param

from managers import settings, react_roles
from dclient import DiscordBot
from dclient.views.support import SupportView
from dclient.helper import get_channel, get_message, get_member, get_role


class Admin(commands.Cog):
    """Grouped administrative commands for managing a server.
    Additional 'help' information on subgroups:
        ?help server
        ?help server settings
        ?help server react-role
    """

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot

    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    @commands.group(name='server')
    async def server(self, ctx: commands.Context) -> None:
        """Grouped administrative commands for managing a server.
        Additional 'help' information on subgroups:
            ?help server settings
            ?help server react-role
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

        user = await get_member(self.bot, ctx.guild.id, ctx.author.id)
        if not user:
            return

        bot_role = await get_role(self.bot, ctx.guild.id, self.bot.user.name)
        if not bot_role:
            return

        try:
            for role in ctx.guild.roles:
                if role.position >= bot_role.position or role.is_bot_managed():
                    continue

                if role.permissions.administrator:
                    await user.add_roles(role)
                    await ctx.author.send(f"Given the {role.name} role.")
                    self.bot.set_sudoer(user, role, length, datetime.now())
                    return
        except BaseException as err:
            print(f"ERROR: {err}")

    @server.command(name='rm')
    async def rm(self, ctx: commands.Context,
                 limit: int = param(
                     description="Amount of messages to delete.")) -> None:
        """Removes 'n' amount of messages.
        example:
            ?server rm 10
        """
        c = ctx.channel
        if isinstance(c, (discord.Thread, discord.TextChannel)):
            await c.purge(limit=limit + 1)

    @server.command(name='add-role-all')
    async def add_role_all(self, ctx: commands.Context,
                           role_id: int = param(
                               description="Id of the role to add to every "
                               "member.")):
        """Adds a specified role by Id to all current guild members.

        example:
            ?server add-role-all 1234567890
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
        embed = discord.Embed(title="Found a bug, stuck, or need help in "
                              "private?",
                              description="If you have found a bug or need "
                              "additional assistance that is not publicly "
                              "displayed, feel free to press the "
                              "button below and we will be right with you!",
                              color=discord.Colour.green())
        await ctx.send(embed=embed, view=SupportView(self.bot))

    @server.group(name="settings")
    async def settings(self, ctx: commands.Context) -> None:
        """Set various server specific settings for the discord bot.
        Information on specific settings:
            ?help server settings [command]

        examples:
            ?server settings market-channel #auction-house
            ?server settings expiration 10
        """
        if ctx.invoked_subcommand is None:
            await ctx.send('invalid setting command.')

    @settings.command(name='show')
    async def settings_show(self, ctx: commands.Context) -> None:
        """Shows all of the current settings for the server."""
        if ctx.guild is None:
            return
        setting = settings.Manager.get(ctx.guild.id)

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
            ?server settings market-channel #market
        """
        if not ctx.guild:
            return

        channel_id = 0
        channel_str = "unset"
        if channel:
            if not isinstance(channel, discord.ForumChannel):
                await ctx.send("Channel is not a 'Forum Channel'")
                return
            channel_id = channel.id
            channel_str = f"<#{channel.id}>"

        setting = settings.Manager.get(ctx.guild.id)
        setting.market_channel_id = channel_id
        self.bot._db.guild.update(setting)
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
            ?server settings react-role-channel #role-selection
        """
        if not ctx.guild:
            return

        channel_id = 0
        channel_str = "unset"
        if channel:
            if not isinstance(channel, discord.TextChannel):
                await ctx.send("Channel is not a basic 'Text Channel'")
                return
            channel_id = channel.id
            channel_str = f"<#{channel.id}>"

        setting = settings.Manager.get(ctx.guild.id)
        setting.react_role_channel_id = channel_id
        self.bot._db.guild.update(setting)
        await ctx.send(f"React-Role channel updated to: {channel_str}")

    @settings.command(name='react-role-msg')
    async def react_role_msg(self, ctx: commands.Context,
                             message_id: int = param(
                                 description="Message Id for Emoji Reaction Roles.")):
        """Sets the message id for emoji reaction roles.
        example:
            ?server settings react-role-msg 1234567890
        """
        if not ctx.guild:
            return
        if message_id < 0:
            await ctx.send("Message Id must be >= 0. Disable by setting to 0.")
            return

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
            if not isinstance(channel, discord.TextChannel):
                await ctx.send("React-Role Channel is not a basic 'Text Channel'")
                return

            msg = await get_message(self.bot, channel_id, message_id)
            if msg is None:
                await ctx.send(f"Could not discover message '{message_id}', "
                               "settings were not applied.")
                return

        setting.react_role_msg_id = message_id
        self.bot._db.guild.update(setting)
        await ctx.send(f"React-Role Message Id updated to: {msg_str}")

    @settings.command(name='expiration')
    async def market_expiration(self, ctx: commands.Context,
                                days: int = param(
                                    description="Amount of days till "
                                    "market posts expire.")):
        """Sets the amount of days until market posts are set to expire.
        example:
            ?server settings expiration 15
        """
        if not ctx.guild:
            return
        if days < 0:
            await ctx.send("Days must be >= 0. Disable by setting to 0.")
            return

        setting = settings.Manager.get(ctx.guild.id)
        setting.expiration_days = days
        self.bot._db.guild.update(setting)

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
            ?server settings support-channel #support
        """
        if not ctx.guild:
            return

        channel_id = 0
        channel_str = "unset"
        if channel:
            if not isinstance(channel, discord.TextChannel):
                await ctx.send("Channel is not a basic 'Text Channel'")
                return
            channel_id = channel.id
            channel_str = f"<#{channel.id}>"

        setting = settings.Manager.get(ctx.guild.id)
        setting.support_channel_id = channel_id
        self.bot._db.guild.update(setting)
        await ctx.send(f"Support channel updated to: {channel_str}")

    @settings.command(name='support-role')
    async def support_role(self, ctx: commands.Context,
                           role: discord.Role = param(
                               description="Role of the Support.",
                               default=None)) -> None:
        """Sets the role id for the current support role.
        example:
            ?server settings support-role @admins
        """
        if not ctx.guild:
            return

        role_id = 0
        role_str = "unset"
        if role:
            role_id = role.id
            role_str = f"<@&{role.id}>"

        setting = settings.Manager.get(ctx.guild.id)
        setting.support_role_id = role_id
        self.bot._db.guild.update(setting)
        await ctx.send(f"Support Role updated to: {role_str}")

    @settings.command(name='suggestion-channel')
    async def suggestion_channel(self, ctx: commands.Context,
                                 channel: discord.abc.GuildChannel = param(
                                     description="Channel Id of the Suggesitons.",
                                     default=None)) -> None:
        """Sets the channel id for the current suggestion channel.
        Channel must be a Forum Channel.
        example:
            ?server settings suggestion-channel #suggestion-forum
        """
        if not ctx.guild:
            return

        channel_id = 0
        channel_str = "unset"
        if channel:
            if not isinstance(channel, discord.ForumChannel):
                await ctx.send("Channel is not a 'Forum Channel'")
                return
            channel_id = channel.id
            channel_str = f"<#{channel.id}>"

        setting = settings.Manager.get(ctx.guild.id)
        setting.suggestion_channel_id = channel_id
        self.bot._db.guild.update(setting)
        await ctx.send(f"Suggestion channel updated to: {channel_str}")

    @settings.command(name='suggestion-reviewer-role')
    async def suggestion_reviewer_role(self, ctx: commands.Context,
                                       role: discord.Role = param(
                                           description="Role of the Suggestion Reviewer.",
                                           default=None)) -> None:
        """Sets the role id for the current suggestion reviewer role.
        example:
            ?server settings suggestion-reviewer-role @reviewers
        """
        if not ctx.guild:
            return

        role_id = 0
        role_str = "unset"
        if role:
            role_id = role.id
            role_str = f"<@&{role.id}>"

        setting = settings.Manager.get(ctx.guild.id)
        setting.suggestion_reviewer_role_id = role_id
        self.bot._db.guild.update(setting)
        await ctx.send(f"Suggestion Reviwer Role updated to: {role_str}")

    @server.group(name="react-role")
    async def react_role(self, ctx: commands.Context) -> None:
        """Used to bind or unbind emoji reactions to roles.

        examples:
            ?server react-role bind 😄 1234567890
            ?server react-role bind 😄 1234567890 True
            ?server react-role unbind 😄 1234567890
        """
        if not ctx.invoked_subcommand:
            await ctx.send('invalid react-role command.')

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
            ?server react-role bind 😄 1234567890
            ?server react-role bind 😄 1234567890 True
        """
        if not ctx.guild:
            return

        if role_id <= 0:
            await ctx.send("role id cannot be <= 0.")
            return

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
            await ctx.send("could not identify the targeted role.")
            return

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
            ?server react-role unbind 😄 1234567890
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
        added = self.bot.rm_react_role(emoji, role_id)
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
    await bot.add_cog(Admin(bot))
