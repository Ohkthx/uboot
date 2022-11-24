from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import param

from dclient import DiscordBot
from dclient.helper import get_channel, get_message
from settings import SettingsManager


async def validate_channel(bot: DiscordBot, ctx: commands.Context,
                           channel_id: int) -> Optional[discord.TextChannel]:
    channel = await get_channel(bot, channel_id)
    if not channel:
        await ctx.send(f"Could not discover channel '{channel_id}', "
                       "settings were not applied.")
        return None
    return channel


class Settings(commands.Cog):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot

    @commands.guild_only()
    @commands.group(name="setting")
    async def setting(self, ctx: commands.Context) -> None:
        """Set various settings for the discord bot."""
        if ctx.invoked_subcommand is None:
            await ctx.send('invalid setting command.')

    @setting.command(name='list')
    async def list(self, ctx: commands.Context) -> None:
        """Lists all of the current settings for the server."""
        if ctx.guild is None:
            return
        setting = SettingsManager.get(ctx.guild.id)

        items: list[str] = []
        for key, value in setting.__dict__.items():
            if value == 0:
                value = "unset"
            key = key.replace('_', ' ').title()
            items.append(f"{key}: {value}")
        msg = '\n'.join(items)
        await ctx.send(f"```{msg}```")

    @setting.command(name='market-channel')
    async def market_channel(self, ctx: commands.Context,
                             channel_id: int = param(
                                 description="Channel Id of the Market.")) -> None:
        """Sets the channel id for the current market channel."""
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

        setting = SettingsManager.get(ctx.guild.id)
        setting.market_channel_id = channel_id
        self.bot._db.guild.update(setting)
        await ctx.send(f"Market Channel Id updated to: {channel_str}")

    @setting.command(name='react-role-channel')
    async def react_role_channel(self, ctx: commands.Context,
                                 channel_id: int = param(
                                     description="Channel Id for Emoji Reaction Roles.")):
        """Sets the channel id for the emoji reaction roles."""
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

        setting = SettingsManager.get(ctx.guild.id)
        setting.react_role_channel_id = channel_id
        self.bot._db.guild.update(setting)
        await ctx.send(f"React-Role Channel Id updated to: {channel_str}")

    @setting.command(name='react-role-msg')
    async def react_role_msg(self, ctx: commands.Context,
                             message_id: int = param(
                                 description="Message Id for Emoji Reaction Roles.")):
        """Sets the message id for emoji reaction roles."""
        if not ctx.guild:
            return
        if message_id < 0:
            await ctx.send("Message Id must be >= 0. Disable by setting to 0.")
            return

        setting = SettingsManager.get(ctx.guild.id)
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

    @setting.command(name='expiration')
    async def market_expiration(self, ctx: commands.Context,
                                days: int = param(
                                    description="Amount of days till "
                                    "market posts expire.")):
        """Sets the amount of days until market posts are set to expire."""
        if not ctx.guild:
            return
        if days < 0:
            await ctx.send("Days must be >= 0. Disable by setting to 0.")
            return
        setting = SettingsManager.get(ctx.guild.id)
        setting.expiration_days = days
        self.bot._db.guild.update(setting)

        days_str = "unset"
        if days > 0:
            days_str = f"{days}"
        await ctx.send(f"Expiration Days updated to: {days_str}")


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(Settings(bot))
