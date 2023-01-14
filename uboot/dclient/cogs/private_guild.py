"""Private / SubGuild commands for managing the private guild mechanic."""
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import param

from managers import settings, subguilds
from dclient import DiscordBot
from dclient.helper import get_channel


class Guild(commands.Cog):
    """Guilds are private threads existing in a large Discord server.
    Guilds are strictly invite only with the guild leader having
    basic abilities to manage it.

    Popular commands:
        (prefix)help guild
        (prefix)guild kick @UserToKick
    """

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot

    @commands.guild_only()
    @commands.group(name="guild")
    async def guild(self, ctx: commands.Context) -> None:
        """Guilds are private threads existing in a large Discord server.
        Guilds are strictly invite only with the guild leader having
        basic abilities to manage it.

        Popular commands:
            (prefix)help guild
            (prefix)guild kick @UserToKick
        """
        if not ctx.invoked_subcommand:
            await ctx.send('invalid guild command.')

    @commands.guild_only()
    @guild.command(name="kick")
    async def kick(self, ctx: commands.Context,
                   user: discord.Member = param(description="User to kick")):
        """Kicks the mentioned user from the guild.
        Only the guild leader can kick.
        Cannot kick guild leader or the bot.

        examples:
            (prefix)guild kick @BadApple
        """
        if not ctx.guild or not ctx.channel:
            return await ctx.send("Must be used in a guild channel.",
                                  ephemeral=True,
                                  delete_after=60)

        # Command not available outside of threads.
        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.send("Must be used in a guild thread.",
                                  ephemeral=True,
                                  delete_after=60)

        # Verify the owner is attempting the command. Prevent others for access
        subguild = subguilds.Manager.by_thread(ctx.guild.id, ctx.channel.id)
        if not subguild or ctx.author.id != subguild.owner_id:
            return await ctx.send("Must be the owner of guild where the "
                                  "command is being used.",
                                  ephemeral=True,
                                  delete_after=60)

        if ctx.author == user:
            return await ctx.send("You cannot kick yourself.", delete_after=60)
        if self.bot.user and self.bot.user == user:
            return await ctx.send("You cannot kick the bot.", delete_after=60)

        # Remove the user and provide text.
        await ctx.channel.remove_user(user)
        color = discord.Color.from_str("#F1C800")  # Yellow color.
        desc = f"**Removed**: {user.mention}\n"\
            f"**Date**: {datetime.utcnow().replace(microsecond=0)} UTC"
        embed = discord.Embed(title="User Kicked",
                              color=color,
                              description=desc)
        await ctx.channel.send(embed=embed)

    @commands.guild_only()
    @guild.command(name="ban")
    async def ban(self, ctx: commands.Context,
                  user: discord.Member = param(description="User to ban")):
        """Bans the mentioned user from the guild.
        Only the guild leader can ban.
        Cannot ban guild leader or the bot.

        examples:
            (prefix)guild ban @BadApple
        """
        if not ctx.guild or not ctx.channel:
            return await ctx.send("Must be used in a guild channel.",
                                  delete_after=60)

        # Command not available outside of threads.
        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.send("Must be used in a guild thread.",
                                  delete_after=60)

        # Verify the owner is attempting the command. Prevent others for access
        subguild = subguilds.Manager.by_thread(ctx.guild.id, ctx.channel.id)
        if not subguild or ctx.author.id != subguild.owner_id:
            return await ctx.send("Must be the owner of guild where the "
                                  "command is being used.",
                                  delete_after=60)

        if ctx.author == user:
            return await ctx.send("You cannot ban yourself.", delete_after=60)
        if user.guild_permissions.manage_channels:
            return await ctx.send("You cannot ban admins.", delete_after=60)
        if self.bot.user and self.bot.user == user:
            return await ctx.send("You cannot ban the bot.", delete_after=60)

        # Remove the user and add them to the banned list.
        await ctx.channel.remove_user(user)
        if not user.id in subguild.banned:
            subguild.banned.append(user.id)
            subguild.save()

        color = discord.Color.from_str("#F1C800")  # Yellow color.
        desc = f"**Removed**: {user.mention}\n"\
            f"**Date**: {datetime.utcnow().replace(microsecond=0)} UTC"
        embed = discord.Embed(title="User banned",
                              color=color,
                              description=desc)
        await ctx.channel.send(embed=embed)

    @commands.guild_only()
    @guild.command(name="unban")
    async def unban(self, ctx: commands.Context,
                    user: discord.Member = param(description="User to unban")):
        """Unbans the mentioned user from the guild.
        Only the guild leader can unban.
        Cannot unban guild leader or the bot.

        examples:
            (prefix)guild unban @GoodApple
        """
        if not ctx.guild or not ctx.channel:
            return await ctx.send("Must be used in a guild channel.",
                                  delete_after=60)

        # Command not available outside of threads.
        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.send("Must be used in a guild thread.",
                                  delete_after=60)

        # Verify the owner is attempting the command. Prevent others for access
        subguild = subguilds.Manager.by_thread(ctx.guild.id, ctx.channel.id)
        if not subguild or ctx.author.id != subguild.owner_id:
            return await ctx.send("Must be the owner of guild where the "
                                  "command is being used.",
                                  delete_after=60)

        # Remove the user from the banned lsit.
        if user.id in subguild.banned:
            subguild.banned = [b for b in subguild.banned if b != user.id]
            subguild.save()

        color = discord.Color.from_str("#F1C800")  # Yellow color.
        desc = f"**Unbanned**: {user}\n"\
            f"**Date**: {datetime.utcnow().replace(microsecond=0)} UTC"
        embed = discord.Embed(title="User unbanned",
                              color=color,
                              description=desc)
        await ctx.channel.send(embed=embed)

    @commands.guild_only()
    @guild.command(name="description", aliases=("desc",))
    async def description(self, ctx: commands.Context,
                          description: str = param(description="Description to add")):
        """Modifies the guilds promotion description.

        examples:
            (prefix)guild description "Welcome new players!"
        """
        if not ctx.guild or not ctx.channel:
            return await ctx.send("Must be used in a guild channel.", delete_after=60)

        # Command not available outside of threads.
        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.send("Must be used in a guild thread.",
                                  delete_after=60)

        # Verify the owner is attempting the command. Prevent others for access
        subguild = subguilds.Manager.by_thread(ctx.guild.id, ctx.channel.id)
        if not subguild or ctx.author.id != subguild.owner_id:
            return await ctx.send("Must be the owner of guild where the command is being used.",
                                  delete_after=60)

        setting = settings.Manager.get(ctx.guild.id)

        # Validate the channels and get the thread.
        channel = await get_channel(self.bot, setting.sub_guild_channel_id)
        if not channel:
            return await ctx.send("Guild channel may be unset.", delete_after=60)
        if not isinstance(channel, discord.TextChannel):
            return await ctx.send("Guild channel not set to a Text Channel.",
                                  delete_after=60)

        # Get the promotional message.
        msg = await channel.fetch_message(subguild.msg_id)
        if not msg:
            return await ctx.send("Could not fetch the promotional message to "
                                  "update.",
                                  delete_after=60)

        # Get the embed assigned to the promotional message.
        if len(msg.embeds) == 0:
            return await ctx.send("Could not locate embed for guild.", delete_after=60)

        # Update the description.
        embed = msg.embeds[0]
        if not embed.description:
            embed.description = "**Description**:```none```Press the join button!"
        parts = embed.description.split("```")
        description = description.strip("```")
        embed.description = f"{parts[0]}```{description}```{parts[-1]}"

        # Send the update.
        await msg.edit(embed=embed)


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    await bot.add_cog(Guild(bot))
