from typing import Optional

import discord


def find_tag(tag: str, ch: discord.ForumChannel) -> Optional[discord.ForumTag]:
    for avail_tag in ch.available_tags:
        if avail_tag.name.lower() == tag.lower():
            return avail_tag
    return None


async def thread_close(tag_rm_name: str, tag_add_name: str,
                       thread: discord.Thread,
                       reason: str,
                       user_msg: str) -> None:

    if not isinstance(thread.parent, discord.ForumChannel):
        await thread.send('thread is not in a forum channel.')
        return

    # Find the tags from available tags.
    rm_tag = find_tag(tag_rm_name, thread.parent)
    add_tag = find_tag(tag_add_name, thread.parent)

    tags = list(thread.applied_tags)
    if rm_tag is not None and rm_tag in tags:
        tags = [t for t in tags if t.name != tag_rm_name]
    if add_tag is not None and add_tag not in tags:
        tags.append(add_tag)

    # Unsubscribe everyone.
    for subscriber in await thread.fetch_members():
        await thread.remove_user(subscriber)

    # Archive and Lock.
    await thread.edit(archived=True, locked=True, reason=reason,
                      applied_tags=tags)

    # Message owner that their thread is closed.
    if thread.guild and thread.owner_id:
        owner = thread.guild.get_member(thread.owner_id)
        if owner is None:
            owner = await thread.guild.fetch_member(thread.owner_id)
        if owner:
            await owner.send(user_msg)
