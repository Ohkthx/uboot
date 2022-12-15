"""All of the panels used to manage Private Guilds (SubGuilds)."""
from typing import Union, Optional
from datetime import datetime

import discord
from discord import ui

from dclient import DiscordBot
from dclient.helper import get_channel, get_member
from dclient.modals.generic_reason import ReasonModal
from managers import subguilds, settings


def guild_info(bot: DiscordBot,
               subguild: subguilds.SubGuild,
               owner: Union[discord.User, discord.Member]) -> discord.Embed:
    """Panel displaying basic guild information. This is sent on guild
    creation.
    """
    title = f"Welcome to {subguild.name}!"
    desc = f"**Leader**: {owner.mention}\n"\
        f"**Date Created**: {datetime.utcnow().replace(microsecond=0)} UTC\n"\
        f"\nGuild management commands are prefixed with: `{bot.prefix}guild`\n"\
        f"**Help** command: `{bot.prefix}help guild`"
    color = discord.Colour.from_str("#00ff08")
    return discord.Embed(title=title, description=desc, color=color)


async def create_subguild(bot: DiscordBot,
                          interaction: discord.Interaction,
                          setting: settings.Settings,
                          subguild: subguilds.SubGuild,
                          owner: discord.Member,
                          promo_embed: discord.Embed) -> bool:
    """Creates a Private Guild (SubGuild). Starts the guilds private thread,
    creates the promotional text.
    """
    res = interaction.response

    # Validate the sub guild channel exists (used for signups and promotions.)
    channel = await get_channel(bot, setting.sub_guild_channel_id)
    if not channel:
        await res.send_message("Guild channel may be unset.",
                               ephemeral=True,
                               delete_after=60)
        return False

    # Has to be a text channel so a private thread can be created.
    if not isinstance(channel, discord.TextChannel):
        await res.send_message("Guild channel not set to a Text Channel.",
                               ephemeral=True,
                               delete_after=60)
        return False

    # Send the promotional embed.
    old_desc = promo_embed.description
    promo_embed.description = f"{old_desc}\n\nInterested in joining?\n"\
        "Press the 'Request to Join' button below!"
    promo_msg = await channel.send(embed=promo_embed,
                                   view=GuildPromotionView(bot))
    promo_embed.description = old_desc
    subguild.msg_id = promo_msg.id

    # Create the thread and update the subguild.
    thread = await channel.create_thread(name=subguild.name,
                                         type=discord.ChannelType.private_thread)
    subguild.thread_id = thread.id
    subguild.save()
    await thread.send(embed=guild_info(bot, subguild, owner))
    await thread.add_user(owner)
    return True


class GuildManagerView(ui.View):
    """Guild Manager View is used by staff/admins to control the access to the
    guild. Options are to close or reopen the guild. Closing the guild notifies
    the guild leader of the closure and reason.
    """

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_close(interaction: discord.Interaction) -> discord.Embed:
        """The panel that is sent to the guild and its leader."""
        color = discord.Colour.from_str("#ff0f08")  # Red color.
        desc = f"This guild was closed by {interaction.user}"
        embed = discord.Embed(title="Guild Closed",
                              color=color,
                              description=desc)
        return embed

    @ui.button(label='Close Guild', style=discord.ButtonStyle.red,
               custom_id='guild_invite_view: close_guild')
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        """Closes the guild notifying the guild leader. This just locks and
        archives the thread preventing additional messages being sent to it.
        """
        res = interaction.response

        # Has to be performed within a server
        guild = interaction.guild
        if not interaction.message or not guild:
            return await res.send_message("Could not find the guilds panel.",
                                          ephemeral=True,
                                          delete_after=60)
        # Get the embed for the guild information.
        if len(interaction.message.embeds) == 0:
            return await res.send_message("Could not locate embed for guild.",
                                          ephemeral=True,
                                          delete_after=60)
        embed = interaction.message.embeds[0]
        embed.set_author(name=f"Closed by {interaction.user}")
        embed.color = discord.Colour.from_str("#ff0f08")

        # Extract the sub guilds id from its panel.
        subguild_id = 0
        try:
            if embed.footer.text:
                subguild_id = int(embed.footer.text)
        except BaseException:
            pass
        if subguild_id < 1:
            return await res.send_message("Unable to load the guild.",
                                          ephemeral=True,
                                          delete_after=60)

        # Get the subguild and settings
        subguild = subguilds.Manager.get(guild.id, subguild_id)
        setting = settings.Manager.get(guild.id)

        # Validate the channels that all private threads exist in.
        channel = await get_channel(self.bot, setting.sub_guild_channel_id)
        if not channel:
            return await res.send_message("Guild channel may be unset.",
                                          ephemeral=True,
                                          delete_after=60)

        # Verify that the channel is a text channel, which means threads can
        # exist in it.
        if not isinstance(channel, discord.TextChannel):
            return await res.send_message("Guild channel not set to a Text Channel.",
                                          ephemeral=True,
                                          delete_after=60)

        # Try to get the thread the private guild exists in.
        thread = channel.get_thread(subguild.thread_id)
        if not thread:
            return await res.send_message("Guilds thread channel not found.",
                                          ephemeral=True,
                                          delete_after=60)

        # Prompt the admin for a reason that will be sent to the guild leader.
        owner = await get_member(self.bot, guild.id, subguild.owner_id)
        from_user = await get_member(self.bot, guild.id, interaction.user.id)
        reasoning = ReasonModal(owner, from_user,
                                "Guild Closed",
                                f"**Guild Name**: {subguild.name}",
                                # Red color.
                                discord.Colour.from_str("#ff0f08")
                                )
        await res.send_modal(reasoning)
        if await reasoning.wait():
            return

        # Disable the guild.
        subguild.disabled = True
        subguild.save()

        # Send notifications to the guild
        await thread.send(embed=GuildManagerView.get_close(interaction))
        await thread.edit(archived=True, locked=True)

        # Remove the promotional text.
        msg = await channel.fetch_message(subguild.msg_id)
        if msg:
            await msg.delete()

        await interaction.message.edit(embed=embed)

    @ui.button(label='Reopen Guild', style=discord.ButtonStyle.green,
               custom_id='guild_invite_view: open_guild')
    async def reopen(self, interaction: discord.Interaction, button: ui.Button):
        """If the guld had be closed previously, this will reopen it and allow
        users to interact with each other again inside the guild.
        """
        res = interaction.response
        guild = interaction.guild
        if not interaction.message or not guild:
            return await res.send_message("Could not find the guilds panel.",
                                          ephemeral=True,
                                          delete_after=60)

        # Get the embed for the guilds panel.
        if len(interaction.message.embeds) == 0:
            return await res.send_message("Could not locate embed for guild.",
                                          ephemeral=True,
                                          delete_after=60)
        embed = interaction.message.embeds[0]
        embed.colour = discord.Colour.blurple()
        embed.remove_author()

        # Extract the sub guilds id from its panel.
        subguild_id = 0
        try:
            if embed.footer.text:
                subguild_id = int(embed.footer.text)
        except BaseException:
            pass
        if subguild_id < 1:
            return await res.send_message("Unable to load the guild.",
                                          ephemeral=True,
                                          delete_after=60)

        # Get the subguild and settings
        subguild = subguilds.Manager.get(guild.id, subguild_id)
        if not subguild.disabled:
            return await res.send_message("That guild appears to already be "
                                          "opened.",
                                          ephemeral=True,
                                          delete_after=60)

        setting = settings.Manager.get(guild.id)

        # Validate the channel that all sub guilds exist in.
        channel = await get_channel(self.bot, setting.sub_guild_channel_id)
        if not channel:
            return await res.send_message("Guild channel may be unset.",
                                          ephemeral=True,
                                          delete_after=60)

        # Verify it is a text channel, only private threads can exist in text
        # channels.
        if not isinstance(channel, discord.TextChannel):
            return await res.send_message("Guild channel not set to a Text Channel.",
                                          ephemeral=True,
                                          delete_after=60)

        # Attempt to find the thread in the archived threads.
        thread: Optional[discord.Thread] = None
        async for t in channel.archived_threads(private=True, joined=True):
            if t.id == subguild.thread_id:
                thread = t
                break
        if not thread:
            return await res.send_message("Guilds thread channel not found.",
                                          ephemeral=True,
                                          delete_after=60)

        # Send notifications to the guild
        await thread.edit(archived=False, locked=False)

        # Resend the promotional embed to the sub guilds channel.
        old_desc = embed.description
        embed.description = f"{old_desc}\n\nInterested in joining?\n"\
            "Press the 'Request to Join' button below!"
        promo_msg = await channel.send(embed=embed,
                                       view=GuildPromotionView(self.bot))
        embed.description = old_desc
        subguild.msg_id = promo_msg.id

        # Update the sub guild to be enabled.
        subguild.disabled = False
        subguild.save()

        embed.set_author(name=f"Opened by {interaction.user}")
        embed.colour = discord.Colour.from_str("#00ff08")  # Green color.
        await interaction.message.edit(embed=embed)
        await res.send_message("Guild reopened.", ephemeral=True,
                               delete_after=60)


class GuildInviteView(ui.View):
    """The panel used to accept new members into the private guild
    (SubGuild). Only the guild leader can press it.
    """

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel(interaction: discord.Interaction) -> discord.Embed:
        """This is the panel that is used to present the new user."""
        color = discord.Color.from_str("#F1C800")  # Yellow color.
        desc = f"**Applicant**: {interaction.user.mention} "\
            f"[{interaction.user}]\n"\
            f"**Date**: {datetime.utcnow().replace(microsecond=0)} UTC\n\n"\
            "If you wish to accept the request, then press the button below."
        embed = discord.Embed(title="Join Request",
                              color=color,
                              description=desc)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=interaction.user.id)
        return embed

    @ui.button(label='Accept', style=discord.ButtonStyle.green,
               custom_id='guild_invite_view: accept')
    async def accept(self, interaction: discord.Interaction, button: ui.Button):
        """Upon being pressed, the user that submitted the request will be
        added to the private guild.
        """
        res = interaction.response
        guild = interaction.guild
        thread = interaction.channel
        if not guild or not thread:
            return await res.send_message("Must be used in a guild channel.",
                                          ephemeral=True,
                                          delete_after=60)

        # Private Guild has to be a thread.
        if not isinstance(thread, discord.Thread):
            return await res.send_message("Must be used in a guild thread.",
                                          ephemeral=True,
                                          delete_after=60)

        # Resolve the invite message.
        if not interaction.message:
            return await res.send_message("Could not find invite message.",
                                          ephemeral=True,
                                          delete_after=60)

        # Verify that the guild owner is the one who pressed the button.
        subguild = subguilds.Manager.by_thread(guild.id, thread.id)
        if not subguild or interaction.user.id != subguild.owner_id:
            return await res.send_message("Must be the owner of guild to do that.",
                                          ephemeral=True,
                                          delete_after=60)

        # Get the embed for the invite.
        if len(interaction.message.embeds) == 0:
            return await res.send_message("Could not locate embed for invite.")
        embed = interaction.message.embeds[0]

        # Extract the id of the user being invited to the guild.
        user_id: int = 0
        try:
            if embed.footer.text:
                user_id = int(embed.footer.text)
        except BaseException:
            pass
        if user_id < 1:
            return await res.send_message("Unable to parse user id.")

        # Get the users Member account.
        user = guild.get_member(user_id)
        if not user:
            try:
                user = await guild.fetch_member(user_id)
            except BaseException:
                pass
        if not user:
            return await res.send_message("Unable to find the user.")

        # Add the user to the private guild abd greet them.
        await thread.add_user(user)
        await res.send_message(f"Hail {user}! Welcome to the community.")

        embed.title = f"[APPROVED] {embed.title}"
        embed.colour = discord.Colour.from_str("#00ff08")  # Green color.
        embed.set_footer(text=f"Approved by {interaction.user}")
        await interaction.message.edit(embed=embed, view=None)


class GuildPromotionView(ui.View):
    """Guild Promotion view is the text and buttons used to promote private
    guilds. Buttons include a 'Request to Join' or a prompt to create your own.
    """

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @ui.button(label='Request to Join', style=discord.ButtonStyle.blurple,
               custom_id='guild_promotion_view: request')
    async def request(self, interaction: discord.Interaction, button: ui.Button):
        """Upon pressing this button, a request is sent to the guild to
        join.
        """
        res = interaction.response
        if not interaction.message or not interaction.guild:
            return

        # Get the embed for the promotion.
        if len(interaction.message.embeds) == 0:
            return await res.send_message("Could not locate embed for guild.",
                                          ephemeral=True,
                                          delete_after=60)
        embed = interaction.message.embeds[0]

        # Extract the sub guilds id.
        subguild_id = 0
        try:
            if embed.footer.text:
                subguild_id = int(embed.footer.text)
        except BaseException:
            pass
        if subguild_id < 1:
            return await res.send_message("Unable to load the guild.",
                                          ephemeral=True,
                                          delete_after=60)

        # Get the subguild and settings
        subguild = subguilds.Manager.get(interaction.guild.id, subguild_id)
        setting = settings.Manager.get(interaction.guild.id)

        # Validate the channels.
        channel = await get_channel(self.bot, setting.sub_guild_channel_id)
        if not channel:
            return await res.send_message("Guild channel may be unset.",
                                          ephemeral=True,
                                          delete_after=60)

        # Channel has to be a text channel for private threads to exist.
        if not isinstance(channel, discord.TextChannel):
            return await res.send_message("Guild channel not set to a Text Channel.",
                                          ephemeral=True,
                                          delete_after=60)

        # Get the private guilds thread.
        thread = channel.get_thread(subguild.thread_id)
        if not thread:
            return await res.send_message("Guilds thread channel not found.",
                                          ephemeral=True,
                                          delete_after=60)

        # Create a new guild invite panel that will be sent to be accepted.
        embed = GuildInviteView.get_panel(interaction)
        await thread.send(embed=embed, view=GuildInviteView(self.bot))

        await res.send_message('Request sent to the guild.',
                               ephemeral=True, delete_after=60)

    @ui.button(label='Create Your Own', style=discord.ButtonStyle.grey,
               custom_id='guild_promotion_view: create')
    async def create(self, interaction: discord.Interaction, button: ui.Button):
        """Placeholder that just tells the user to create their own."""
        res = interaction.response
        await res.send_message('Scroll to the top of the channel, a request '
                               'form can be accessed there.',
                               ephemeral=True,
                               delete_after=60)


class GuildApprovalView(ui.View):
    """Panel used to approve or deny new guild creation requests."""

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel(name: str, abbrv: str,
                  description: str,
                  user: Union[discord.User, discord.Member],
                  subguild_id: int) -> discord.Embed:
        """Panel text for admins/staff to see the guild information."""
        now = datetime.utcnow().replace(microsecond=0)
        title = name
        desc = f"**Abbreviation**: {abbrv}\n"\
            f"**Point of Contact**: {user.mention}\n"\
            f"**Established**: {now} UTC\n\n"\
            f"**Description**:\n```{description}```"
        color = discord.Color.from_str("#F1C800")  # Yellow color.
        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_footer(text=subguild_id)
        return embed

    @ui.button(label='🗹 Approve', style=discord.ButtonStyle.green,
               custom_id='guild_approval_view:approve')
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        """Approves the guild creation request. Establishes the guilds thread
        and sends the promotional panel to the sub guild channel.
        """
        res = interaction.response
        if not interaction.message or not interaction.guild:
            return

        # Get the embed to extract the guilds id.
        if len(interaction.message.embeds) == 0:
            return await res.send_message("Could not locate embed for guild.")
        embed = interaction.message.embeds[0]
        embed.colour = discord.Colour.blurple()

        # Extract the sub guilds id.
        subguild_id: int = 0
        try:
            if embed.footer.text:
                subguild_id = int(embed.footer.text)
        except BaseException:
            pass
        if subguild_id < 1:
            return await res.send_message("Unable to load the guild.")

        # Get the subguilds settings and owner.
        subguild = subguilds.Manager.get(interaction.guild.id, subguild_id)
        owner = await get_member(self.bot, subguild.guild_id, subguild.owner_id)
        if not owner:
            return await res.send_message("Guild Owner could not be found.",
                                          ephemeral=True,
                                          delete_after=60)

        # Create the thread.
        setting = settings.Manager.get(interaction.guild.id)
        if not await create_subguild(self.bot, interaction,
                                     setting, subguild, owner, embed):
            return

        # Mark it as approved and remove the buttons.
        color = discord.Colour.from_str("#00ff08")  # Green color.
        embed.color = color
        embed.set_author(name=f"Approved by {interaction.user}")
        await interaction.message.edit(embed=embed,
                                       view=GuildManagerView(self.bot),
                                       )

        # Update the guild settings.
        subguild.disabled = False
        subguild.save()

        await owner.send(embed=embed)
        await res.send_message('Guild approved.', ephemeral=True,
                               delete_after=60)

    @ui.button(label='⨯ Deny', style=discord.ButtonStyle.red,
               custom_id='guild_approval_view:deny')
    async def deny(self, interaction: discord.Interaction, button: ui.Button):
        """Denies a guild creation requestion. Prompts staff for a reason why
        the guild was denied and sends that reason to the guild leader to
        potentially makes changes.
        """
        res = interaction.response
        if not interaction.message or not interaction.guild:
            return

        # Get the embed to extract the guild id.
        if len(interaction.message.embeds) == 0:
            return await res.send_message("Could not locate embed for guild.")
        embed = interaction.message.embeds[0]
        embed.title = f"[DENIED] {embed.title}"
        embed.colour = discord.Colour.from_str("#ff0f08")  # Red color.

        # Extract the sub guilds id from the footer then update it.
        subguild_id = 0
        try:
            if embed.footer.text:
                subguild_id = int(embed.footer.text)
            embed.set_footer(text=f"Denied by {interaction.user}")
        except BaseException:
            pass
        if subguild_id < 1:
            return await res.send_message("Unable to load the guild.")

        # Get the subguilds settings and owner, notify them of the status.
        subguild = subguilds.Manager.get(interaction.guild.id, subguild_id)
        owner = await get_member(self.bot, subguild.guild_id, subguild.owner_id)
        if not owner:
            await res.send_message("Guild Owner could not be found.",
                                   ephemeral=True,
                                   delete_after=60)

        from_user: Optional[discord.Member] = None
        if isinstance(interaction.user, discord.Member):
            from_user = interaction.user

        # Send a reason to the guild leader.
        reasoning = ReasonModal(owner, from_user,
                                "Guild Application Denied",
                                f"**Guild Name**: {subguild.name}",
                                # Red color.
                                discord.Colour.from_str("#ff0f08")
                                )
        await res.send_modal(reasoning)
        if await reasoning.wait():
            return

        # Update the guild status.
        await interaction.message.edit(embed=embed, view=None)


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    bot.add_view(GuildPromotionView(bot))
    bot.add_view(GuildApprovalView(bot))
    bot.add_view(GuildInviteView(bot))
    bot.add_view(GuildManagerView(bot))
