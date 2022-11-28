from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import param

from managers import settings, react_roles
from dclient.helper import get_channel, get_message
from dclient import DiscordBot


async def validate_channel(bot: DiscordBot, ctx: commands.Context,
                           channel_id: int) -> Optional[discord.TextChannel]:
    channel = await get_channel(bot, channel_id)
    if not channel:
        await ctx.send(f"Could not discover channel '{channel_id}', "
                       "settings were not applied.")
        return None
    return channel


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

    @server.command(name='rm')
    async def rm(self, ctx: commands.Context,
                 limit: int = param(
                     description="Amount of messages to delete.")) -> None:
        """Removes 'n' amount of messages.
        example:
            ?server rm 10
        """
        c = ctx.channel
        if isinstance(c, discord.Thread) or isinstance(c, discord.TextChannel):
            await c.purge(limit=limit + 1)

    @server.group(name="settings")
    async def settings(self, ctx: commands.Context) -> None:
        """Set various server specific settings for the discord bot.
        Information on specific settings:
            ?help server settings [command]

        examples:
            ?server settings market-channel 1234567890
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
                             channel_id: int = param(
                                 description="Channel Id of the Market.")) -> None:
        """Sets the channel id for the current market channel.
        example:
            ?server settings market-channel 1234567890
        """
        if not ctx.guild:
            return
        if channel_id < 0:
            await ctx.send("Channel Id must be >= 0. Disable by setting to 0.")
            return

        channel_str = f"unset"
        # Check if channel exists.
        if channel_id != 0:
            channel_str = f"<#{channel_id}>"
            channel = await validate_channel(self.bot, ctx, channel_id)
            if not channel:
                return
            if not isinstance(channel, discord.ForumChannel):
                await ctx.send(f"Channel is not a basic 'Forum Channel'")
                return

        setting = settings.Manager.get(ctx.guild.id)
        setting.market_channel_id = channel_id
        self.bot._db.guild.update(setting)
        await ctx.send(f"Market Channel Id updated to: {channel_str}")

    @settings.command(name='react-role-channel')
    async def react_role_channel(self, ctx: commands.Context,
                                 channel_id: int = param(
                                     description="Channel Id for Emoji Reaction Roles.")):
        """Sets the channel id for the emoji reaction roles.
        example:
            ?server settings react-role-channel 1234567890
        """
        if not ctx.guild:
            return
        if channel_id < 0:
            await ctx.send("Channel Id must be >= 0. Disable by setting to 0.")
            return

        channel_str = f"unset"
        # Check if channel exists.
        if channel_id != 0:
            channel_str = f"<#{channel_id}>"
            channel = await validate_channel(self.bot, ctx, channel_id)
            if not channel:
                return
            if not isinstance(channel, discord.TextChannel):
                await ctx.send(f"Channel is not a basic 'Text Channel'")
                return

        setting = settings.Manager.get(ctx.guild.id)
        setting.react_role_channel_id = channel_id
        self.bot._db.guild.update(setting)
        await ctx.send(f"React-Role Channel Id updated to: {channel_str}")

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
            channel = await validate_channel(self.bot, ctx, channel_id)
            if not channel:
                return
            if not isinstance(channel, discord.TextChannel):
                await ctx.send(f"React-Role Channel is not a basic 'Text Channel'")
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

    @server.group(name="react-role")
    async def react_role(self, ctx: commands.Context) -> None:
        """Used to bind or unbind emoji reactions to roles.

        examples:
            ?server react-role bind 😄 1234567890
            ?server react-role bind 😄 1234567890 True
            ?server react-role unbind 😄 1234567890
        """
        if not ctx.invoked_subcommand:
            await ctx.message.delete()
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

        # Make sure the guild is valid.
        if not ctx.guild:
            await ctx.send("could not identify the guild.")
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
            msg = "reaction and role bound."
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
            msg = "reaction and role unbound."
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
