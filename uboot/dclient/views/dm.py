"""Views / Panels used for testing new features or referencing."""
from typing import Optional

import discord
from discord import ui

from dclient.modals.dm import DMResponseModal
from dclient.helper import get_user


async def extract_user(client: discord.Client,
                       message: discord.Message) -> Optional[discord.User]:
    """Attempt to get the user from a message with an embed."""
    # Get the embed to extract the user id.
    if len(message.embeds) == 0:
        return None

    # Extract the user id from the footer.
    user_id: int = 0
    try:
        if message.embeds[0].footer.text:
            user_id = int(message.embeds[0].footer.text)
    except BaseException:
        pass

    # Lookup the user
    return await get_user(client, user_id)


class DMDeleteView(ui.View):
    """Adds a "DELETE MESSAGE" button to DMs."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @ui.button(label='DELETE MESSAGE', style=discord.ButtonStyle.red,
               custom_id='dm_delete_view:delete')
    async def delete(self, interaction: discord.Interaction, _: ui.Button):
        """Button to press to delete the message."""
        msg = interaction.message
        if not msg:
            return

        await msg.delete()


class DMNewView(ui.View):
    """Used to create the invite link into a new DM."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel(user: discord.User) -> discord.Embed:
        """Creates the panel for joining a DM."""
        embed = discord.Embed(title=str(user))
        embed.description = "This is a private direct message. You are "\
            "being a presented as and representing the bot."
        embed.set_footer(text=str(user.id))
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    @ui.button(label='JOIN', style=discord.ButtonStyle.blurple,
               custom_id='dm_new_view:join')
    async def join(self, interaction: discord.Interaction, _: ui.Button):
        """Prompts for a response message."""
        res = interaction.response
        client = interaction.client
        msg = interaction.message
        channel = interaction.channel

        if not msg:
            return await res.send_message("Could not locate message.",
                                          delete_after=15)

        user = await extract_user(client, msg)
        if not user:
            return await res.send_message("Unable to load the user.",
                                          delete_after=15)

        if not channel or not isinstance(channel, discord.TextChannel):
            return await res.send_message("Invalid channel to join.",
                                          delete_after=15)

        threads = channel.threads
        thread = next((t for t in threads if t.name == str(user.id)), None)
        if not thread:
            return await res.send_message("DM no longer exists.",
                                          delete_after=15)

        await thread.add_user(interaction.user)
        await res.send_message(f"You have been added to <#{thread.id}>",
                               ephemeral=True,
                               delete_after=15)

    @ui.button(label='REFRESH', style=discord.ButtonStyle.green,
               custom_id='dm_new_view:refresh')
    async def refresh(self, interaction: discord.Interaction, _: ui.Button):
        """Refreshes the user embed."""
        res = interaction.response
        client = interaction.client
        msg = interaction.message

        if not msg:
            return await res.send_message("Could not locate message.",
                                          delete_after=15)

        user = await extract_user(client, msg)
        if not user:
            return await res.send_message("Unable to load the user.",
                                          delete_after=15)

        await msg.edit(embed=DMNewView.get_panel(user))
        await res.send_message(f"User has been refreshed.",
                               ephemeral=True,
                               delete_after=15)


class DMResponseView(ui.View):
    """Adds a 'RESPOND' and 'DELETE MESSAGE' buttons to DMs."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @ ui.button(label='RESPOND', style=discord.ButtonStyle.blurple,
                custom_id='dm_response_view:respond')
    async def respond(self, interaction: discord.Interaction, _: ui.Button):
        """Prompts for a response message."""
        res = interaction.response
        client = interaction.client
        msg = interaction.message

        if not msg:
            return await res.send_message("Could not locate message.",
                                          delete_after=15)

        user = await extract_user(client, msg)
        if not user:
            return await res.send_message("Unable to load the user.",
                                          delete_after=15)

        modal = DMResponseModal(user)
        await res.send_modal(modal)
        await modal.wait()

    @ ui.button(label='DELETE MESSAGE', style=discord.ButtonStyle.red,
                custom_id='dm_response_view:delete')
    async def delete(self, interaction: discord.Interaction, _: ui.Button):
        """Button to press to delete the message."""
        msg = interaction.message
        if not msg:
            return

        await msg.delete()


async def setup(bot: discord.Client) -> None:
    """This is called by process that loads extensions."""
    bot.add_view(DMDeleteView(bot))
    bot.add_view(DMNewView(bot))
    bot.add_view(DMResponseView(bot))
