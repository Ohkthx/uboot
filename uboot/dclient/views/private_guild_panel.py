from typing import Union
from datetime import datetime

import discord
from discord import ui

from dclient import DiscordBot
from dclient.helper import get_channel, get_member
from managers import subguilds, settings


def guild_info(bot: DiscordBot,
               subguild: subguilds.SubGuild,
               owner: Union[discord.User, discord.Member]) -> discord.Embed:
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
    res = interaction.response
    channel = await get_channel(bot, setting.sub_guild_channel_id)
    if not channel:
        await res.send_message("Guild channel may be unset.",
                               ephemeral=True,
                               delete_after=60)
        return False
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


class GuildPromotionView(ui.View):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @ui.button(label='Request to Join', style=discord.ButtonStyle.blurple,
               custom_id='guild_promotion_view: request')
    async def request(self, interaction: discord.Interaction, button: ui.Button):
        res = interaction.response
        if not interaction.message or not interaction.guild:
            return

        # Get the embed.
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

        # Validate the channels and get the thread..
        channel = await get_channel(self.bot, setting.sub_guild_channel_id)
        if not channel:
            return await res.send_message("Guild channel may be unset.",
                                          ephemeral=True,
                                          delete_after=60)
        if not isinstance(channel, discord.TextChannel):
            return await res.send_message("Guild channel not set to a Text Channel.",
                                          ephemeral=True,
                                          delete_after=60)
        thread = channel.get_thread(subguild.thread_id)
        if not thread:
            return await res.send_message("Guilds thread channel not found.",
                                          ephemeral=True,
                                          delete_after=60)

        color = discord.Color.from_str("#F1C800")  # Yellow color.
        desc = f"**Requester**: {interaction.user.mention}\n"\
            f"**Date**: {datetime.utcnow().replace(microsecond=0)} UTC\n\n"\
            "If you wish to accept the request, then please @mention\n"\
            "the user in the channel."
        embed = discord.Embed(title="Join Request",
                              color=color,
                              description=desc)
        await thread.send(embed=embed)

        await res.send_message('Request sent to the guild.',
                               ephemeral=True, delete_after=60)

    @ui.button(label='Create Your Own', style=discord.ButtonStyle.grey,
               custom_id='guild_promotion_view: create')
    async def create(self, interaction: discord.Interaction, button: ui.Button):
        res = interaction.response
        await res.send_message('Scroll to the top of the channel, a request '
                               'form can be accessed there.',
                               ephemeral=True,
                               delete_after=60)


class GuildApprovalView(ui.View):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel(name: str, abbrv: str,
                  description: str,
                  user: Union[discord.User, discord.Member],
                  subguild_id: int) -> discord.Embed:
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
        res = interaction.response
        if not interaction.message or not interaction.guild:
            return

        # Get the embed.
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
        embed.title = f"[APPROVED] {embed.title}"
        embed.colour = discord.Colour.from_str("#00ff08")  # Green color.
        embed.set_footer(text=f"Approved by {interaction.user}")
        await interaction.message.edit(embed=embed, view=None)

        # Update the guild settings.
        subguild.disabled = False
        subguild.save()

        await owner.send(f"Guild approved by {interaction.user}.")
        await res.send_message('Guild approved.', ephemeral=True,
                               delete_after=60)

    @ui.button(label='⨯ Deny', style=discord.ButtonStyle.red,
               custom_id='guild_approval_view:deny')
    async def deny(self, interaction: discord.Interaction, button: ui.Button):
        res = interaction.response
        if not interaction.message or not interaction.guild:
            return

        # Get the embed.
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
        else:
            await owner.send(f"Guild denied by {interaction.user}, reach out "
                             "for additional information.")

        # Update the guild status.
        await interaction.message.edit(embed=embed, view=None)
        await res.send_message('Guild denied.', ephemeral=True,
                               delete_after=60)


async def setup(bot: DiscordBot) -> None:
    bot.add_view(GuildPromotionView(bot))
    bot.add_view(GuildApprovalView(bot))
