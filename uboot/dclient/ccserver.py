"""Command and Control Server for the Discord Bot."""

import discord

from dclient.views.dm import DMNewView
from .helper import get_user


class CCServer:
    """Command and Control Server for the Discord Bot."""

    def __init__(self, client: discord.Client,
                 owner: discord.User,
                 dm_channel: discord.TextChannel) -> None:
        self.client = client
        self.owner = owner
        self.dm_channel = dm_channel

    @property
    def guild(self) -> discord.Guild:
        """Gets the guild for the CCServer"""
        return self.dm_channel.guild

    def is_guild(self, guild_id: int) -> bool:
        """Checks if the provided guild id is the CCServer."""
        return guild_id == self.guild.id

    @staticmethod
    def is_dm(message: discord.Message) -> bool:
        """Checks if a message belongs to a DM Channel."""
        return isinstance(message.channel, discord.DMChannel)

    def is_response(self, message: discord.Message) -> bool:
        """Checks if a message is a response to a DM."""
        thread = message.channel
        if not isinstance(thread, discord.Thread):
            return False

        return thread.parent == self.dm_channel

    def add_thread(self, thread: discord.Thread) -> None:
        """Adds a thread to memory."""
        if isinstance(thread.parent, discord.ForumChannel):
            return
        if thread.parent != self.dm_channel:
            return

        self.guild._add_thread(thread)

    def remove_thread(self, thread: discord.Thread) -> None:
        """Removes a thread from memory."""
        if isinstance(thread.parent, discord.ForumChannel):
            return
        if thread.parent != self.dm_channel:
            return

        self.guild._remove_thread(thread)

    async def get_thread(self, user: discord.User) -> discord.Thread:
        """Gets the users DM thread. Creates a new one if it cannot be found."""
        threads = self.dm_channel.threads
        thread = next((t for t in threads if t.name == str(user.id)), None)
        if thread:
            return thread

        # Add the user text and join button.
        embed = DMNewView.get_panel(user)
        view = DMNewView(self.client)
        message = await self.dm_channel.send(embed=embed, view=view)

        # Create the thread and add it to the cache.
        thread = await self.dm_channel.create_thread(name=str(user.id),
                                                     message=message)
        self.add_thread(thread)

        await thread.add_user(self.owner)
        return thread

    async def log_dm(self, message: discord.Message) -> None:
        """Logs a DM into the CCServer."""
        if message.guild or not self.is_dm(message):
            return

        if not isinstance(message.author, discord.User):
            return

        # Send the message to the dm channel and thread.
        user_thread = await self.get_thread(message.author)
        content = message.content.replace("```", "+++")
        await user_thread.send(f"```{content}```")

    async def process(self, message: discord.Message) -> None:
        """Process a message inside a DM Thread and respond."""
        thread = message.channel
        if not isinstance(thread, discord.Thread):
            return

        if thread.parent != self.dm_channel:
            return

        # Try to get the user.
        user_id: int = 0
        try:
            user_id = int(thread.name)
        except BaseException:
            pass
        if user_id <= 0:
            await message.reply("Could not extract user id.", delete_after=30)
            return

        user = await get_user(self.client, user_id)
        if not user:
            await message.reply("Could not find user.", delete_after=30)
            return

        await user.send(message.content)
