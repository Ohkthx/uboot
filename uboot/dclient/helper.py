from typing import Optional

import discord
from discord import ForumChannel, TextChannel
from discord.ext import commands

from managers import react_roles


def find_tag(tag: str, channel: ForumChannel) -> Optional[discord.ForumTag]:
    for avail_tag in channel.available_tags:
        if avail_tag.name.lower() == tag.lower():
            return avail_tag
    return None


async def get_role_by_name(bot: commands.Bot, guild_id: int,
                           role_name: str) -> Optional[discord.Role]:
    guild = await get_guild(bot, guild_id)
    if not guild:
        return None

    role = next((r for r in guild.roles if r.name == role_name), None)
    if not role:
        try:
            roles = await guild.fetch_roles()
            role = next((r for r in roles if r.name == role_name), None)
        except BaseException:
            return None
    return role


async def get_role(bot: commands.Bot, guild_id: int,
                   role_id: int) -> Optional[discord.Role]:
    guild = await get_guild(bot, guild_id)
    if not guild:
        return None

    role = next((r for r in guild.roles if r.id == role_id), None)
    if not role:
        try:
            roles = await guild.fetch_roles()
            role = next((r for r in roles if r.id == role_id), None)
        except BaseException:
            return None
    return role


async def get_guild(bot: commands.Bot,
                    guild_id: int) -> Optional[discord.Guild]:
    guild = bot.get_guild(guild_id)
    if not guild:
        try:
            guild = await bot.fetch_guild(guild_id)
        except BaseException:
            return None
    return guild


async def get_member(bot: commands.Bot, guild_id: int,
                     user_id: int) -> Optional[discord.Member]:
    guild = await get_guild(bot, guild_id)
    if not guild:
        return None

    member = guild.get_member(user_id)
    if not member:
        try:
            member = await guild.fetch_member(user_id)
        except BaseException:
            return None
    return member


async def get_channel(bot: commands.Bot,
                      channel_id: int) -> Optional[discord.abc.GuildChannel]:
    channel = bot.get_channel(channel_id)
    if not channel:
        try:
            channel = await bot.fetch_channel(channel_id)
        except BaseException:
            return None
    if not isinstance(channel, discord.abc.GuildChannel):
        return None
    return channel


async def get_message(bot: commands.Bot, channel_id: int,
                      message_id: int) -> Optional[discord.Message]:
    channel = await get_channel(bot, channel_id)
    if not channel or not isinstance(channel, TextChannel):
        return None

    try:
        message = await channel.fetch_message(message_id)
        return message
    except BaseException:
        return None


async def thread_close(tag_rm_names: list[str], tag_add_name: str,
                       thread: discord.Thread,
                       reason: str,
                       user_msg: Optional[str] = None) -> None:
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

    # Message owner that their thread is closed.
    if not thread.guild or not thread.owner_id:
        return

    if user_msg is None or user_msg == "":
        return

    owner = thread.guild.get_member(thread.owner_id)
    if not owner:
        try:
            owner = await thread.guild.fetch_member(thread.owner_id)
        except BaseException as err:
            print(f"Error while closing thread: {err}")
            return
    if owner:
        try:
            await owner.send(user_msg)
        except BaseException as err:
            print(f"Error while sending closure message: {err}")


async def react_processor(bot: commands.Bot,
                          payload: discord.RawReactionActionEvent):
    if not payload.guild_id:
        return None

    # Validate the guild for the reaction.
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return None

    # Check if it is a react-role.
    react_role = react_roles.Manager.find(guild.id, payload.emoji.name)
    if not react_role:
        return None

    # Validate the member/user exists.
    user = await get_member(bot, guild.id, payload.user_id)
    if not user or user.bot:
        return None

    # Get the role related to the reaction.
    guild_role = guild.get_role(react_role.role_id)
    if not guild_role:
        return None

    return (user, guild_role, react_role.reversed)
