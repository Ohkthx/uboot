"""Helper functions related to the Discord API that have no true home."""
from typing import Optional

import discord
from discord import ForumChannel, TextChannel

from managers import react_roles


def find_tag(tag: str, channel: ForumChannel) -> Optional[discord.ForumTag]:
    """Attempts to find a tag by name belonging to a forum channel."""
    for avail_tag in channel.available_tags:
        if avail_tag.name.lower() == tag.lower():
            return avail_tag
    return None


async def get_role_by_name(client: discord.Client, guild_id: int,
                           role_name: str) -> Optional[discord.Role]:
    """Attempts to get a role by its name that belongs to a server.
    Tries to get it from cache first, if not found then fetches from API.
    """
    guild = await get_guild(client, guild_id)
    if not guild:
        # Could not resolve guild, no tag found.
        return None

    # Iterate all of the cached tags for the guild.
    role = next((r for r in guild.roles if r.name == role_name), None)
    if not role:
        # Could not find it in cache, attempt to fetch it from API.
        try:
            roles = await guild.fetch_roles()
            role = next((r for r in roles if r.name == role_name), None)
        except BaseException:
            return None
    return role


async def get_role(client: discord.Client, guild_id: int,
                   role_id: int) -> Optional[discord.Role]:
    """Attempts to get a role by its id belonging to the specified guild id.
    Tries to get it from cache first, if not found then fetches from API.
    """
    guild = await get_guild(client, guild_id)
    if not guild:
        # Could not resolve guild, no tag found.
        return None

    # Iterate all of the cached tags for the guild.
    role = next((r for r in guild.roles if r.id == role_id), None)
    if not role:
        # Could not find it in cache, attempt to fetch it from API.
        try:
            roles = await guild.fetch_roles()
            role = next((r for r in roles if r.id == role_id), None)
        except BaseException:
            return None
    return role


async def get_guild(client: discord.Client,
                    guild_id: int) -> Optional[discord.Guild]:
    """Attempt to get the guild based on its id.
    Tries to get it from cache first, if not found then fetches from API.
    """
    # Check cached guilds.
    guild = client.get_guild(guild_id)
    if not guild:
        # Could not find in cachexd, try to fetch it from API.
        try:
            guild = await client.fetch_guild(guild_id)
        except BaseException:
            return None
    return guild


async def get_member(client: discord.Client, guild_id: int,
                     user_id: int) -> Optional[discord.Member]:
    """Attempt to get the member based on its id.
    Tries to get it from cache first, if not found then fetches from API.
    """
    guild = await get_guild(client, guild_id)
    if not guild:
        # Could not resolve guild, no member found.
        return None

    # Attempt to find the member in cache first.
    member = guild.get_member(user_id)
    if not member:
        # Could not find in cache, try to fetch from API.
        try:
            member = await guild.fetch_member(user_id)
        except BaseException:
            return None
    return member


async def get_user(client: discord.Client,
                   user_id: int) -> Optional[discord.User]:
    """Attempt to get the user based on its id.
    Tries to get it from cache first, if not found then fetches from API.
    """
    # Attempt to find the user in cache first.
    user = client.get_user(user_id)
    if not user:
        # Could not find in cache, try to fetch from API.
        try:
            user = await client.fetch_user(user_id)
        except BaseException:
            return None
    return user


async def get_channel(client: discord.Client,
                      channel_id: int) -> Optional[discord.abc.GuildChannel]:
    """Attempt to get a channel based on its id.
    Tries to get it from cache first, if not found then fetches from API.
    """
    # Attempt from cache first.
    channel = client.get_channel(channel_id)
    if not channel:
        # Fallback on trying to fetch from API.
        try:
            channel = await client.fetch_channel(channel_id)
        except BaseException:
            return None
    if not isinstance(channel, discord.abc.GuildChannel):
        # Only want guild channels.
        return None
    return channel


async def get_message(client: discord.Client, channel_id: int,
                      message_id: int) -> Optional[discord.Message]:
    """Attempt to fetch a message from the API."""
    channel = await get_channel(client, channel_id)
    if not channel or not isinstance(channel, TextChannel):
        # Could not resolve the text channel.
        return None

    try:
        return await channel.fetch_message(message_id)
    except BaseException:
        return None


async def thread_close(tag_rm_names: list[str], tag_add_name: str,
                       thread: discord.Thread,
                       reason: str) -> None:
    """Closes and archives a thread. Removes and replaces tags/labels."""
    tags = []
    if isinstance(thread.parent, ForumChannel):
        # Find the tags from available tags.
        add_tag = find_tag(tag_add_name, thread.parent)

        tags = list(thread.applied_tags)
        for name in tag_rm_names:
            tags = [t for t in tags if t.name != name]
        if add_tag is not None and add_tag not in tags:
            tags.append(add_tag)

        # Unsubscribe everyone.
        for subscriber in await thread.fetch_members():
            await thread.remove_user(subscriber)

    # Archive and Lock.
    await thread.edit(archived=True, locked=True, reason=reason,
                      applied_tags=tags)


async def react_processor(client: discord.Client,
                          payload: discord.RawReactionActionEvent,
                          ) -> Optional[tuple[discord.Member, discord.Role, bool]]:
    """Processes Reaction events and checks if a Reaction Role pair exists
    for it already.
    """
    if not payload.guild_id:
        return None

    # Validate the guild for the reaction.
    guild = await get_guild(client, payload.guild_id)
    if not guild:
        return None

    # Check if it is a react-role.
    react_role = react_roles.Manager.find(guild.id, payload.emoji.name)
    if not react_role:
        return None

    # Validate the member/user exists.
    user = await get_member(client, guild.id, payload.user_id)
    if not user or user.bot:
        return None

    # Get the role related to the reaction.
    guild_role = guild.get_role(react_role.role_id)
    if not guild_role:
        return None

    return (user, guild_role, react_role.reversed)
