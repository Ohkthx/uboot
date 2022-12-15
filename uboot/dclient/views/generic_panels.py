"""Generic Panels / Views for Forum Threads."""
from typing import Optional

import discord
from discord import ui
from discord.ext import commands

from managers import settings
from dclient.helper import thread_close, find_tag, get_guild
from dclient.modals.generic_reason import ReasonModal


async def validate_user(interaction: discord.Interaction,
                        guild: discord.Guild,
                        role_id: int) -> Optional[discord.Role]:
    """Validates that the user who attempted to performed the interaction has
    all the required roles to do it.
    """
    user = interaction.user
    if not interaction.channel or not user:
        return

    # Only interested in performing this action inside threads.
    if not isinstance(interaction.channel, discord.Thread):
        return

    # Attempt to extract the role from the guild.
    role = guild.get_role(role_id)
    if role_id == 0 or not role:
        return

    # If the user is not a guild member, ignore.
    if not isinstance(user, discord.Member):
        return

    # If the user does not have the role, notify them they cannot do that.
    if not role in user.roles:
        res = interaction.response
        embed = discord.Embed(title="Invalid Permissions",
                              description=f"You must have the {role.mention} "
                              "role to do that.",
                              color=discord.Color.red())
        return await res.send_message(embed=embed,
                                      ephemeral=True,
                                      delete_after=60)
    return role


class BasicThreadView(ui.View):
    """This view/panel is for unknown threads that contain 'in-progress' and
    'close' tags.
    """

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @staticmethod
    async def get_panel(bot: commands.Bot, guild_id: int) -> discord.Embed:
        """Get the panel for the basic view. Assume the required role to
        perform tasks is 'support'.
        """
        role_name = "support"

        # Extract the exact role name, attempting to first get a mentionable.
        setting = settings.Manager.get(guild_id)
        role_id = setting.support_role_id
        guild = await get_guild(bot, guild_id)
        if guild:
            role = next((r for r in guild.roles if r.id == role_id), None)
            if role:
                role_name = role.mention

        title = "Support Panel"
        color = discord.Colour.from_str("#00ff08")
        desc = f"This interactive panel is only for use by {role_name}.\n\n"\
            "> __**Options**:__\n"\
            "> ├ **In Progress**: Work in progress.\n"\
            "> └ **Close**: Close and lock thread, prompts reason.\n\n"\
            "__Note__: Please allow all parties to view the thread before closure."

        return discord.Embed(title=title, description=desc, color=color)

    @ui.button(label='In Progress', style=discord.ButtonStyle.blurple,
               custom_id='basic_thread_view:progress')
    async def progress(self, interaction: discord.Interaction, button: ui.Button):
        """Upon being pressed, the thread will be marked as in-progress to
        indicate to the user that it is being worked on.
        """

        # Make sure the channel is a thread.
        thread = interaction.channel
        if not interaction.guild or not isinstance(thread, discord.Thread):
            return

        # Make sure the thread belongs to a Forum Channel.
        if not isinstance(thread.parent, discord.ForumChannel):
            return

        # Validate the user can perform the action.
        setting = settings.Manager.get(interaction.guild.id)
        role_id = setting.support_role_id
        role = await validate_user(interaction, interaction.guild, role_id)
        if not role:
            return

        # Update the thread that it is being worked on.
        res = interaction.response
        user_msg = f"Your thread was marked in-progress by **{interaction.user}**."
        embed = discord.Embed(title="Labeled as being in-progress",
                              description=user_msg,
                              color=discord.Colour.blue())
        await res.send_message(embed=embed)

        # Find the tags from available tags.
        rm_names = ['closed']
        add_tag = find_tag('in-progress', thread.parent)

        tags = list(thread.applied_tags)
        for name in rm_names:
            tags = [t for t in tags if t.name != name]
        if add_tag is not None and add_tag not in tags:
            tags.append(add_tag)

        # Apply the new tags.
        await thread.edit(applied_tags=tags)

    @ui.button(label='🔒 Close', style=discord.ButtonStyle.grey,
               custom_id='basic_thread_view:close')
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        """Closes and archives a thread. Preventing further communication from
        ocurring within it.
        """
        # Validate that the action is inside of a thread.
        thread = interaction.channel
        if not interaction.guild or not isinstance(thread, discord.Thread):
            return

        # Validate the user can perform the action.
        setting = settings.Manager.get(interaction.guild.id)
        role_id = setting.support_role_id
        role = await validate_user(interaction, interaction.guild, role_id)
        if not role:
            return

        # Resolve the member that is performing the action.
        user_id = interaction.user.id
        from_user = interaction.guild.get_member(user_id)
        if not from_user:
            try:
                from_user = await interaction.guild.fetch_member(user_id)
            except BaseException:
                pass

        # Prompt staff/admin for a reason it is being closed.
        res = interaction.response
        reason = ReasonModal(thread.owner, from_user,
                             "Thread Closed",
                             f"**Name**: {thread.name}",
                             discord.Color.light_grey())
        await res.send_modal(reason)
        if await reason.wait():
            return

        # If reason was provided, officially close the thread and archive.
        await thread_close(["open", "in-progress"], "closed", thread,
                           "unlisted closure")


class SuggestionView(ui.View):
    """A Panel / View for appropriately handling suggestions that occur within
    Forum Channels. Allows staff to do easy management tasks.
    """

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @staticmethod
    async def get_panel(bot: commands.Bot, guild_id: int) -> discord.Embed:
        """Panel used to describe the available tasks to staff/admin. Assumed
        required role is 'reviewer'
        """
        role_name = "a reviewer"

        # Attempt to extract the real role name or mentionable.
        setting = settings.Manager.get(guild_id)
        role_id = setting.suggestion_reviewer_role_id
        guild = await get_guild(bot, guild_id)
        if guild:
            role = next((r for r in guild.roles if r.id == role_id), None)
            if role:
                role_name = role.mention

        title = "Suggestion Reviewer Panel"
        color = discord.Colour.from_str("#00ff08")
        desc = f"This interactive panel is only for use by {role_name}.\n\n"\
            "> __**Options**:__\n"\
            "> ├ **Approve**: Eventual implementation.\n"\
            "> ├ **Deny**: Not implementing.\n"\
            "> └ **Close**: Close and lock thread.\n\n"\
            "__Note__: Please allow all parties to view the thread before closure."

        return discord.Embed(title=title, description=desc, color=color)

    @ui.button(label='🗹 Approve', style=discord.ButtonStyle.green,
               custom_id='suggestion_view:approve')
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        """Marks the suggestion as being approved. Only usable by staff/admins
        with the correct role.
        """
        thread = interaction.channel
        if not interaction.guild or not isinstance(thread, discord.Thread):
            return
        if not isinstance(thread.parent, discord.ForumChannel):
            return

        # Validate that the user can perform the action.
        setting = settings.Manager.get(interaction.guild.id)
        role_id = setting.suggestion_reviewer_role_id
        role = await validate_user(interaction, interaction.guild, role_id)
        if not role:
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
        """Denies a suggestion. Labels it accordingly."""
        thread = interaction.channel
        if not interaction.guild or not isinstance(thread, discord.Thread):
            return
        if not isinstance(thread.parent, discord.ForumChannel):
            return

        # Validate that the user can perform the action.
        setting = settings.Manager.get(interaction.guild.id)
        role_id = setting.suggestion_reviewer_role_id
        role = await validate_user(interaction, interaction.guild, role_id)
        if not role:
            return

        # Get the users Member account.
        from_user: Optional[discord.Member] = None
        if isinstance(interaction.user, discord.Member):
            from_user = interaction.user

        # Prompt the reviewer for a reason why it is being denied.
        res = interaction.response
        reason = ReasonModal(thread.owner, from_user,
                             "Suggestion Denied",
                             f"**Suggestion**: {thread.name}",
                             discord.Color.red())
        await res.send_modal(reason)
        if await reason.wait():
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

    @ui.button(label='🔒 Close', style=discord.ButtonStyle.grey,
               custom_id='suggestion_view:close')
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        """Close and archive the suggestion preventing future participation
        unless it is reopened by staff.
        """
        thread = interaction.channel
        if not interaction.guild or not isinstance(thread, discord.Thread):
            return
        if not isinstance(thread.parent, discord.ForumChannel):
            return

        # Validate that the user can perform that action.
        setting = settings.Manager.get(interaction.guild.id)
        role_id = setting.suggestion_reviewer_role_id
        role = await validate_user(interaction, interaction.guild, role_id)
        if not role:
            return

        user_msg = f"Your suggestion was closed by **{interaction.user}**."
        embed = discord.Embed(title="Suggestion Closed",
                              description=user_msg,
                              color=discord.Color.light_grey())
        res = interaction.response
        await res.send_message(embed=embed)

        # Close, lock, and archive the thread.
        if interaction.user.id == thread.owner_id:
            user_msg = ""
        await thread_close(["open", "in-progress"], "closed", thread,
                           "unlisted closure", user_msg)
