import discord
from discord.ext import commands
from discord.ext.commands import param

from dclient import DiscordBot
from dclient.helper import get_channel, get_message
from settings import SettingsManager


class ReactRole(commands.Cog):
    """Reaction Role management."""

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        self.delete_after = 5.0

    @commands.group(name="react-role")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    async def react_role(self, ctx: commands.Context) -> None:
        """Used to bind or unbind emoji reactions to roles."""
        if not ctx.invoked_subcommand:
            await ctx.message.delete()
            await ctx.send('invalid react-role command.',
                           delete_after=self.delete_after)

    @react_role.command(name='bind')
    async def bind(self,
                   ctx: commands.Context,
                   emoji: str = param(description="Emoji to represent role."),
                   role_id: int = param(description="Numeric Id of the role.")):
        """Binds an emoji that can be reacted to for role assignment."""
        if not ctx.guild:
            return

        if role_id <= 0:
            await ctx.send("role id cannot be <= 0.")
            return

        setting = SettingsManager.get(ctx.guild.id)
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
        except:
            await ctx.send("could not add emoji, may be custom or invalid.")
            return
        msg = "role may already be bound."
        added = self.bot.add_react_role(emoji, role_id, ctx.guild.id)
        if added:
            msg = "reaction and role bound."
        await ctx.send(msg)

    @react_role.command(name='unbind')
    async def unbind(self,
                     ctx: commands.Context,
                     emoji: str = param(description="Emoji to unbind."),
                     role_id: int = param(description="Numeric Id of the role.")):
        """Unbinds an emoji reaction from the role specified."""
        if not ctx.guild:
            return

        setting = SettingsManager.get(ctx.guild.id)
        channel_id = setting.react_role_channel_id
        message_id = setting.react_role_msg_id

        # Get the message the reactions are attached to.
        react_msg = await get_message(self.bot, channel_id, message_id)
        if react_msg and self.bot.user:
            # Remove the base reaction to the message to represent the role.
            await react_msg.remove_reaction(emoji, self.bot.user)

        # Remove the role locally.
        msg = "role may already be unbound."
        added = self.bot.rm_react_role(emoji, role_id, ctx.guild.id)
        if added:
            msg = "reaction and role unbound."
        await ctx.send(msg)

    @react_role.command(name='list')
    async def list(self, ctx: commands.Context):
        """Displays a list of currently bound emojis to roles."""
        # Make sure the guild is valid.
        if not ctx.guild:
            await ctx.send("could not identify the guild.")
            return

        res: list[str] = []
        react_roles = self.bot.react_roles
        for rrole in react_roles:
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
    await bot.add_cog(ReactRole(bot))
