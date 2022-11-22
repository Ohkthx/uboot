import discord
from discord.ext import commands
from discord.ext.commands import param

from dclient import DiscordBot


class ReactRole(commands.Cog):
    """Reaction Role management."""

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        self.delete_after = 5.0

    @commands.group(name="react-role")
    @commands.has_guild_permissions(manage_messages=True)
    async def react_role(self, ctx: commands.Context) -> None:
        """Used to bind or unbind emoji reactions to roles."""
        if ctx.invoked_subcommand is None:
            await ctx.message.delete()
            await ctx.send('invalid react-role command.',
                           delete_after=self.delete_after)

    @react_role.command(name='bind')
    async def bind(self,
                   ctx: commands.Context,
                   emoji: str = param(description="Emoji to represent role."),
                   role_id: int = param(description="Numeric Id of the role.")):
        """Binds an emoji that can be reacted to for role assignment."""
        config = self.bot._config

        # Verify the channel exists.
        react_ch = self.bot.get_channel(config.react_role_id)
        if react_ch is None:
            react_ch = self.bot.fetch_channel(config.react_role_id)
        if react_ch is None or not isinstance(react_ch, discord.TextChannel):
            await ctx.send("invalid channel id provided or channel type.")
            return

        # Get the message the reactions are attached to.
        react_msg = await react_ch.fetch_message(config.react_role_msg_id)
        if react_msg is None:
            await ctx.send("could not identify the reaction-role message.")
            return

        # Make sure the guild is valid.
        if ctx.guild is None:
            await ctx.send("could not identify the guild.")
            return

        # Check if the role exists.
        guild_role = ctx.guild.get_role(role_id)
        if guild_role is None:
            await ctx.send("could not identify the targeted role.")
            return

        # Add the base reaction to the message to represent the role.
        await react_msg.add_reaction(emoji)
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
        config = self.bot._config

        # Verify the channel exists.
        react_ch = self.bot.get_channel(config.react_role_id)
        if react_ch is None:
            react_ch = self.bot.fetch_channel(config.react_role_id)
        if react_ch is None or not isinstance(react_ch, discord.TextChannel):
            await ctx.send("invalid channel id provided or channel type.")
            return

        # Make sure the guild is valid.
        if ctx.guild is None:
            return

        # Remove the role locally.
        msg = "role may already be unbound."
        added = self.bot.rm_react_role(emoji, role_id, ctx.guild.id)
        if added:
            msg = "reaction and role unbound."
        await ctx.send(msg)

        # Get the message the reactions are attached to.
        react_msg = await react_ch.fetch_message(config.react_role_msg_id)
        if react_msg is None:
            return

        # Remove the base reaction to the message to represent the role.
        if self.bot.user:
            await react_msg.remove_reaction(emoji, self.bot.user)

    @react_role.command(name='list')
    async def list(self, ctx: commands.Context):
        """Displays a list of currently bound emojis to roles."""
        # Make sure the guild is valid.
        if ctx.guild is None:
            await ctx.send("could not identify the guild.")
            return

        res: list[str] = []
        react_roles = self.bot.react_roles
        for rrole in react_roles:
            role = ctx.guild.get_role(rrole.role_id)
            if role is None:
                continue
            res.append(f"{rrole.reaction} => {role.name} ({rrole.role_id})")
        if len(res) == 0:
            await ctx.send('no bound reactions to roles.')
            return
        text = '\n'.join(res)
        await ctx.send(f"```{text}```")


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(ReactRole(bot))
