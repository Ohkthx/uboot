import discord
from discord import ui

from managers import settings
from dclient.helper import thread_close, find_tag


async def validate_user(interaction: discord.Interaction) -> bool:
    res = interaction.response
    channel = interaction.channel
    guild = interaction.guild
    user = interaction.user
    if not channel or not guild or not user:
        return False

    if not isinstance(channel, discord.Thread):
        return False

    setting = settings.Manager.get(guild.id)
    role = guild.get_role(setting.suggestion_reviewer_role_id)
    if setting.suggestion_reviewer_role_id == 0 or not role:
        return False

    if not isinstance(user, discord.Member):
        return False
    if not role in user.roles:
        await res.send_message("You must be a reviewer to do that.",
                               ephemeral=True)
        return False
    return True


class SuggestionView(ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @ui.button(label='🗹 Approve', style=discord.ButtonStyle.green,
               custom_id='suggestion_view:approve')
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        valid = await validate_user(interaction)
        if not valid:
            return

        thread = interaction.channel
        if not isinstance(thread, discord.Thread):
            return

        # Find the tags from available tags.
        rm_names = ['open', 'denied']
        add_tag = find_tag('approved', thread.parent)

        tags = list(thread.applied_tags)
        for name in rm_names:
            tags = [t for t in tags if t.name != name]
        if add_tag is not None and add_tag not in tags:
            tags.append(add_tag)

        # Apply the new tags.
        await thread.edit(applied_tags=tags)

        res = interaction.response
        await res.send_message("Your suggestion was approved by "
                               f"**{interaction.user}**.")

    @ui.button(label='⨯ Deny', style=discord.ButtonStyle.red,
               custom_id='suggestion_view:deny')
    async def deny(self, interaction: discord.Interaction, button: ui.Button):
        valid = await validate_user(interaction)
        if not valid:
            return

        thread = interaction.channel
        if not isinstance(thread, discord.Thread):
            return

        # Find the tags from available tags.
        rm_names = ['open', 'approved']
        add_tag = find_tag('denied', thread.parent)

        tags = list(thread.applied_tags)
        for name in rm_names:
            tags = [t for t in tags if t.name != name]
        if add_tag is not None and add_tag not in tags:
            tags.append(add_tag)

        # Apply the new tags.
        await thread.edit(applied_tags=tags)

        res = interaction.response
        await res.send_message("Your suggestion was denied by "
                               f"**{interaction.user}**.")

    @ui.button(label='🔒 Close', style=discord.ButtonStyle.grey,
               custom_id='suggestion_view:close')
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        valid = await validate_user(interaction)
        if not valid:
            return

        res = interaction.response
        await res.send_message("Your suggestion was closed by "
                               f"**{interaction.user}**.")

        channel = interaction.channel
        user_msg = f"Your thread was closed by **{interaction.user}**."
        if interaction.user.id == channel.owner_id:
            user_msg = ""
        await thread_close("open", "closed", channel,
                           "unlisted closure", user_msg)
