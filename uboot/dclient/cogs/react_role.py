import discord
from discord.ext import commands

from dclient import DiscordBot


class ReactRole(commands.Cog):
    def __init__(self, bot: DiscordBot) -> None:
        self._bot = bot
        self.delete_after = 5.0

    @commands.group(name="react-role")
    @commands.has_guild_permissions(manage_messages=True)
    async def react_role(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await ctx.message.delete()
            await ctx.send('invalid react-role command.',
                           delete_after=self.delete_after)

    @react_role.command(name='bind',
                        description='binds a reaction to a role.')
    async def bind(self, ctx: commands.Context, reaction: str, role_id: int) -> None:
        config = self._bot._config

        # Verify the channel exists.
        react_ch = self._bot.get_channel(config.react_role_id)
        if react_ch is None:
            react_ch = self._bot.fetch_channel(config.react_role_id)
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
        await react_msg.add_reaction(reaction)
        msg = "role may already be bound."
        added = self._bot.add_react_role(reaction, role_id, ctx.guild.id)
        if added:
            msg = "reaction and role bound."
        await ctx.send(msg)

    @react_role.command(name='unbind',
                        description='unbinds a reaction from a role.')
    async def unbind(self, ctx: commands.Context, reaction: str, role_id: int) -> None:
        config = self._bot._config

        # Verify the channel exists.
        react_ch = self._bot.get_channel(config.react_role_id)
        if react_ch is None:
            react_ch = self._bot.fetch_channel(config.react_role_id)
        if react_ch is None or not isinstance(react_ch, discord.TextChannel):
            await ctx.send("invalid channel id provided or channel type.")
            return

        # Make sure the guild is valid.
        if ctx.guild is None:
            return

        # Remove the role locally.
        msg = "role may already be unbound."
        added = self._bot.rm_react_role(reaction, role_id, ctx.guild.id)
        if added:
            msg = "reaction and role unbound."
        await ctx.send(msg)

        # Get the message the reactions are attached to.
        react_msg = await react_ch.fetch_message(config.react_role_msg_id)
        if react_msg is None:
            return

        # Remove the base reaction to the message to represent the role.
        if self._bot.user:
            await react_msg.remove_reaction(reaction, self._bot.user)

    @react_role.command(name='list',
                        description="lists all of the currently bound "
                        "reactions and roles")
    async def list(self, ctx: commands.Context):
        # Make sure the guild is valid.
        if ctx.guild is None:
            await ctx.send("could not identify the guild.")
            return

        res: list[str] = []
        react_roles = self._bot.react_roles
        for rrole in react_roles:
            role = ctx.guild.get_role(rrole.role_id)
            if role is None:
                continue
            res.append(f"{rrole.reaction} => {role.name} ({rrole.role_id})")
        if len(res) == 0:
            await ctx.send('No bound reactions to roles.')
            return
        text = '\n'.join(res)
        await ctx.send(f"```{text}```")


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(ReactRole(bot))
