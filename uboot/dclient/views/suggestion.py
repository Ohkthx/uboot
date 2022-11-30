from typing import Optional

import discord
from discord import ui

from managers import settings
from dclient.helper import thread_close, find_tag


async def validate_user(interaction: discord.Interaction,
                        guild: discord.Guild, role_id: int, role_name: str):
    user = interaction.user
    if not interaction.channel or not user:
        return

    if not isinstance(interaction.channel, discord.Thread):
        return

    role = guild.get_role(role_id)
    if role_id == 0 or not role:
        return

    if not isinstance(user, discord.Member):
        return
    if not role in user.roles:
        res = interaction.response
        embed = discord.Embed(title="Invalid Permissions",
                              description=f"You must have the {role.mention} "
                              "role to do that.",
                              color=discord.Color.red())
        await res.send_message(embed=embed, ephemeral=True)
        return
    return role


class BasicThreadView(ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @ui.button(label='🔒 Close', style=discord.ButtonStyle.grey,
               custom_id='basic_thread_view:close')
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.guild:
            return
        setting = settings.Manager.get(interaction.guild.id)
        role_id = setting.support_role_id
        role = await validate_user(interaction, interaction.guild,
                                   role_id, "support")
        if not role:
            return

        res = interaction.response
        user_msg = f"Your thread was closed by **{interaction.user}**."
        embed = discord.Embed(title="Thread Closed",
                              description=user_msg,
                              color=discord.Color.light_grey())
        await res.send_message(embed=embed)

        channel = interaction.channel
        if interaction.user.id == channel.owner_id:
            user_msg = ""
        await thread_close("open", "closed", channel,
                           "unlisted closure", user_msg)


class SuggestionView(ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @ui.button(label='🗹 Approve', style=discord.ButtonStyle.green,
               custom_id='suggestion_view:approve')
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.guild:
            return
        setting = settings.Manager.get(interaction.guild.id)
        role_id = setting.suggestion_reviewer_role_id
        role = await validate_user(interaction, interaction.guild,
                                   role_id, "a reviewer")
        if not role:
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

        msg = f"Your suggestion was approved by **{interaction.user}**."
        embed = discord.Embed(title="Suggestion Approved",
                              description=msg,
                              color=discord.Color.green())
        res = interaction.response
        await res.send_message(embed=embed)

    @ui.button(label='⨯ Deny', style=discord.ButtonStyle.red,
               custom_id='suggestion_view:deny')
    async def deny(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.guild:
            return
        setting = settings.Manager.get(interaction.guild.id)
        role_id = setting.suggestion_reviewer_role_id
        role = await validate_user(interaction, interaction.guild,
                                   role_id, "a reviewer")
        if not role:
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

        msg = f"Your suggestion was denied by **{interaction.user}**."
        embed = discord.Embed(title="Suggestion Denied",
                              description=msg,
                              color=discord.Color.red())
        res = interaction.response
        await res.send_message(embed=embed)

    @ui.button(label='🔒 Close', style=discord.ButtonStyle.grey,
               custom_id='suggestion_view:close')
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.guild:
            return
        setting = settings.Manager.get(interaction.guild.id)
        role_id = setting.suggestion_reviewer_role_id
        role = await validate_user(interaction, interaction.guild,
                                   role_id, "a reviewer")
        if not role:
            return

        user_msg = f"Your suggestion was closed by **{interaction.user}**."
        embed = discord.Embed(title="Suggestion Closed",
                              description=user_msg,
                              color=discord.Color.light_grey())
        res = interaction.response
        await res.send_message(embed=embed)

        channel = interaction.channel
        if interaction.user.id == channel.owner_id:
            user_msg = ""
        await thread_close("open", "closed", channel,
                           "unlisted closure", user_msg)
