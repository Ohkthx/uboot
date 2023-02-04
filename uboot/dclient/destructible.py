"""Destructible temporarily exist and will be queued for deletion."""
from typing import Optional, Callable, Awaitable, Any
from datetime import datetime, timedelta
from enum import Enum

import discord

from managers.logs import Log

DelCallback = Callable[[Optional[discord.Message]], Awaitable[Any]]


class Destructible:
    """A Destructible that has a temporary life. Upon expiration, it is
    destroyed and removed from Discord.
    """

    class Category(Enum):
        """Categories of Destructibles."""
        OTHER = 'other'
        GAMBLE = 'gamble'
        MONSTER = 'monster'

    def __init__(self, category: 'Destructible.Category',
                 user_id: int, length: int, delete_msg: bool = False) -> None:
        self.category = category
        self.user_id = user_id
        self.length = length
        self.delete_msg = delete_msg

        self._msg: Optional[discord.Message] = None
        self._callback: Optional[Callable] = None
        self._is_done: bool = False
        self._timestamp: datetime = datetime.now()

    @property
    def message(self) -> Optional[discord.Message]:
        """Obtains the protected message property."""
        return self._msg

    def add_time(self, seconds: int) -> None:
        """Adds seconds to the destructible."""
        self._timestamp += timedelta(seconds=seconds)

    def set_message(self, message: Optional[discord.Message] = None) -> None:
        """Sets the message for the destructible, automatically adding it to
        the Destructible Manager as well.
        """
        if not message:
            return

        if self.message and DestructibleManager.get(self.message.id):
            # Remove the old tracked destructible.
            del DestructibleManager._destructibles[self.message.id]

        # Add the new tracked destructible.
        if len(message.content) == 0 and len(message.embeds) == 0:
            self.delete_msg = True
        self._msg = message
        DestructibleManager.add(self)

    def set_callback(self, func: DelCallback) -> None:
        """Sets a function to be called upon removing."""
        self._callback = func

    def is_expired(self) -> bool:
        """Checks if the view has expired and should be removed."""
        now = datetime.now()
        return now - self._timestamp > timedelta(seconds=self.length)

    async def remove(self):
        """Removes the view, deleting if the message has no content."""
        if not self._msg or self._is_done:
            self._msg = None
            self._is_done = True
            return

        if self._callback:
            await self._callback(self._msg)
        self._is_done = True

        try:
            # If it is an empty message without the view, just remove it.
            if self.delete_msg:
                self._msg.components = []
                return await self._msg.delete()

            self._msg = await self._msg.edit(view=None)
        except BaseException:
            Log.debug("Could not remove the destructible view.")


class DestructibleManager:
    """Manages all the destructibles."""
    # Message Id: Destructible
    _destructibles: dict[int, Destructible] = {}

    @staticmethod
    def extend(msg_id: int, seconds: int) -> None:
        """Extends the time for a destructibles by the amount of seconds passed
        to it.
        """
        destructible = DestructibleManager.get(msg_id)
        if not destructible:
            return
        destructible.add_time(seconds)

    @staticmethod
    def get(msg_id: int) -> Optional[Destructible]:
        """Attempts to get a Destructible based on the message id."""
        return DestructibleManager._destructibles.get(msg_id)

    @staticmethod
    async def remove_one(msg_id: int, remote: bool) -> None:
        """Deletes a single Destructible locally, remotely if true."""
        destructible = DestructibleManager.get(msg_id)
        if destructible:
            if remote and destructible.message:
                await destructible.remove()
            del DestructibleManager._destructibles[msg_id]

    @staticmethod
    async def remove_many(user_id: int, remote: bool,
                          category: Optional[Destructible.Category] = None) -> None:
        """Removes all destructibles for a user with an optional type
        specified. If 'remote' is true, it will attempt to make an API request
        to remove them remotely.
        """
        # Build the list to remove.
        delete_me: list[int] = []
        for msg_id, destruct in DestructibleManager._destructibles.items():
            if destruct.user_id == user_id:
                if category:
                    # Category specified, double check category type.
                    if destruct.category == category:
                        delete_me.append(msg_id)
                else:
                    # Category does not matter, flag for deletion.
                    delete_me.append(msg_id)

        # Remove the destructibles
        for msg_id in delete_me:
            to_delete = DestructibleManager._destructibles.get(msg_id)
            if remote and to_delete:
                # Attempt to remove them remotely as well.
                await to_delete.remove()
            del DestructibleManager._destructibles[msg_id]

    @staticmethod
    def add(destructible: Destructible) -> bool:
        """Adds a destructible, but only if the message is currently set."""
        msg = destructible.message
        if not msg:
            return False
        DestructibleManager._destructibles[msg.id] = destructible
        return True

    @staticmethod
    async def purge() -> None:
        """Removes all expired destructibles."""
        # Check destructible views, if they are expired they will be removed.
        delete: list[int] = []
        for view_id, destruct in DestructibleManager._destructibles.items():
            if destruct.is_expired():
                await destruct.remove()
                delete.append(view_id)

        # Remove from memory.
        for i in delete:
            del DestructibleManager._destructibles[i]
