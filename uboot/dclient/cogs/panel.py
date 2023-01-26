import discord
from discord.ext import commands
from discord.ext.commands import param

from dclient import DiscordBot
from dclient.helper import get_channel
from dclient.views.dm import DMDeleteView, DMResponseView
from dclient.views.minigame import TauntView, UserActionView
from dclient.views.support_request import SupportRequestView
from dclient.views.private_guild_signup import GuildSignupView
from dclient.views.private_guild_panel import GuildManagerView
from managers import settings


class Panel(commands.Cog):
    """Controls the (re)creation of panels."""

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot

    @commands.group(name="panel")
    async def panel(self, ctx: commands.Context) -> None:
        """Allows for the (re)creation of various panels that may have been
        deleted or implemented later.
        """
        if not ctx.invoked_subcommand:
            await ctx.send("Invalid panel command.", delete_after=30)

    @commands.dm_only()
    @panel.group(name="dm")
    async def dm(self, ctx: commands.Context) -> None:
        """Controls DM related panels. These are just buttons that get attached
        to previously created bot messages.

        examples:
            [panel dm delete 0123456789
            [panel dm response 0123456789
        """
        if not ctx.invoked_subcommand:
            await ctx.send("Invalid dm panel command.", delete_after=30)

    @dm.command(name="delete", aliases=("del", "rm", "remove"))
    async def dm_delete(self, ctx: commands.Context,
                        msg_id: int = param(
                            description="Message id to attach to.",
                        )) -> None:
        """Adds a 'DELETE MESSAGE' button to the message.

        examples:
            [panel dm delete 0123456789
        """
        channel = ctx.channel
        if not isinstance(channel, discord.DMChannel):
            return

        # Verify the message.
        if msg_id <= 0:
            await ctx.reply("Invalid message id, it must be greater than 0.",
                            delete_after=30)
            return

        # Attempt to get the message.
        msg = channel.get_partial_message(msg_id)
        if not msg:
            await ctx.reply("Invalid message id, could not be found.",
                            delete_after=30)
            return

        # Attach to the message.
        await msg.edit(view=DMDeleteView(self.bot))

    @dm.command(name="response", aliases=("res", "respond"))
    async def dm_response(self, ctx: commands.Context,
                          msg_id: int = param(
                              description="Message id to attach to.",
                          )) -> None:
        """Adds a 'RESPONSE' and 'DELETE MESSAGE' button to the message.

        examples:
            [panel dm response 0123456789
        """
        channel = ctx.channel
        if not isinstance(channel, discord.DMChannel):
            return

        # Verify the message.
        if msg_id <= 0:
            await ctx.reply("Invalid message id, it must be greater than 0.",
                            delete_after=30)
            return

        # Attempt to get the message.
        msg = channel.get_partial_message(msg_id)
        if not msg:
            await ctx.reply("Invalid message id, could not be found.",
                            delete_after=30)
            return

        # Attach to the message.
        await msg.edit(view=DMResponseView(self.bot))

    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    @panel.group(name="support")
    async def support(self, ctx: commands.Context) -> None:
        """The panel group for the Support Ticket system.

        examples:
            [panel support signup
        """
        if not ctx.invoked_subcommand:
            await ctx.send("Invalid support panel command.", delete_after=30)

    @support.command(name="signup", aliases=("invite", "inv", "request"))
    async def support_signup(self, ctx: commands.Context) -> None:
        """Adds the signup panel for the Support Ticket system. This allows
        users to fill out a form to get assistance from others privately.

        examples:
            [panel support signup
        """
        channel = ctx.channel
        if not isinstance(channel, discord.TextChannel):
            await ctx.reply("You need to be in a text channel to do that.",
                            delete_after=30)
            return

        await ctx.send(embed=SupportRequestView.get_panel(),
                       view=SupportRequestView(self.bot))

    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    @panel.group(name="thread")
    async def thread(self, ctx: commands.Context) -> None:
        """The panel group for generic threads.

        examples:
            [panel thread create
        """
        if not ctx.invoked_subcommand:
            await ctx.send("Invalid thread panel command.", delete_after=30)

    @thread.command(name="create", aliases=("generic",))
    async def thread_create(self, ctx: commands.Context) -> None:
        """Process that is normally called when a thread is created. This will
        create a generic panel based on the type of thread it is.

        examples:
            [panel thread create
        """
        # Check to make sure this is a thread it is being called in.
        thread = ctx.channel
        if not thread or not isinstance(thread, discord.Thread):
            return

        # Requires the thread to be in a Forum Channel.
        if not isinstance(thread.parent, discord.ForumChannel):
            return

        await self.bot.on_thread_create(thread)

    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    @panel.group(name="guild")
    async def guild(self, ctx: commands.Context) -> None:
        """The panel group for private guilds.

        examples:
            [panel guild signup
            [panel guild manage
        """
        if not ctx.invoked_subcommand:
            await ctx.send("Invalid guild panel command.", delete_after=30)

    @guild.command(name="signup")
    async def signup(self, ctx: commands.Context):
        """The 'Request / Signup' Panel for Guilds.

        examples:
            [panel guild signup
        """
        await ctx.send(embed=GuildSignupView.get_panel(),
                       view=GuildSignupView(self.bot))

    @guild.command(name="manage")
    async def manage(self, ctx: commands.Context,
                     msg_id: int = param(
                         description="id of the message to attach to.")):
        """Applies the 'Management' Panel' to a Private Guild representation.
        Only need to do this if it is missing.

        examples:
            [panel guild manage
        """
        channel = ctx.channel
        guild = ctx.guild
        if not channel or not guild:
            return

        # Attempt to get the message the panel is to be added to.
        msg = await channel.fetch_message(msg_id)
        if not msg:
            return await ctx.send("Could not find message by that id.",
                                  delete_after=60)

        # Prevent trying to attach to non-bot messages.
        if self.bot.user and msg.author.id != self.bot.user.id:
            return await ctx.send("Can only attach to the bots messages.",
                                  delete_after=60)

        # Add the view.
        await msg.edit(view=GuildManagerView(self.bot))

    @commands.guild_only()
    @panel.group(name="minigame")
    async def minigame(self, ctx: commands.Context) -> None:
        """Controls minigame related panels. These are just buttons that get
        attached to a forum thread.

        examples:
            [panel minigame taunt
        """
        if not ctx.invoked_subcommand:
            await ctx.send("Invalid minigame panel command.", delete_after=30)

    @minigame.command(name="user-actions")
    async def user_actions(self, ctx: commands.Context) -> None:
        """Creates a panel for various user actions (stats, bank, recall).

        examples:
            [panel minigame user-actions
        """
        guild = ctx.guild
        if not guild:
            return

        setting = settings.Manager.get(guild.id)
        thread_ch = await get_channel(self.bot, setting.minigame.channel_id)
        if not thread_ch or not isinstance(thread_ch, discord.ForumChannel):
            await ctx.send("Invalid minigame thread channel, could be unset.",
                           delete_after=30)
            return

        embed = UserActionView.get_panel()
        view = UserActionView(self.bot)

        # Create a new thread for the buttons.
        await thread_ch.create_thread(name="User Management",
                                      view=view, embed=embed)

    @minigame.command(name="taunt")
    async def taunt(self, ctx: commands.Context) -> None:
        """Creates a panel for the taunt button.

        examples:
            [panel minigame taunt
        """
        guild = ctx.guild
        if not guild:
            return

        setting = settings.Manager.get(guild.id)
        thread_ch = await get_channel(self.bot, setting.minigame.channel_id)
        if not thread_ch or not isinstance(thread_ch, discord.ForumChannel):
            await ctx.send("Invalid minigame thread channel, could be unset.",
                           delete_after=30)
            return

        embed = TauntView.get_panel()
        view = TauntView(self.bot)

        # Create a new thread for the taunt button.
        await thread_ch.create_thread(name="Taunt Panel", view=view, embed=embed)


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    await bot.add_cog(Panel(bot))
