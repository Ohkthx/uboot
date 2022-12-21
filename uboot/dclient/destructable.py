"""Destructables temporarily exist and will be queued for deletion."""
from typing import Optional, Callable, Awaitable, Any
from datetime import datetime, timedelta
from enum import Enum

import discord

from utils import Log


class Destructable():
    """A Destructable that has a temporary life. Upon expiration it is
    destroyed and removed from Discord.
    """

    class Category(Enum):
        """Categories of Destructables."""
        OTHER = 'other'
        GAMBLE = 'gamble'
        MONSTER = 'monster'

    def __init__(self, category: 'Destructable.Category',
                 user_id: int, length: int, delete_msg: bool = False) -> None:
        self.category = category
        self.user_id = user_id
        self.length = length
        self.delete_msg = delete_msg

        self._msg: Optional[discord.Message] = None
        self._callback: Optional[Callable] = None
        self._isdone: bool = False
        self._timestamp: datetime = datetime.now()

    @property
    def message(self) -> Optional[discord.Message]:
        """Obtains the protected message property."""
        return self._msg

    def add_time(self, seconds: int) -> None:
        """Adds seconds to the destructable."""
        self._timestamp += timedelta(seconds=seconds)

    def set_message(self, message: Optional[discord.Message] = None) -> None:
        """Sets the message for the destructable, automatically adding it to
        the Destructable Manager aswell.
        """
        if not message:
            return

        if self.message and DestructableManager.get(self.message.id):
            # Remove the old tracked destructable.
            del DestructableManager._destructables[self.message.id]

        # Add the new tracked destructable.
        if len(message.content) == 0 and len(message.embeds) == 0:
            self.delete_msg = True
        self._msg = message
        DestructableManager.add(self)

    def set_callback(
            self, func: Callable[[Optional[discord.Message]], Awaitable[Any]]) -> None:
        """Sets a function to be called upon removing."""
        self._callback = func

    def isexpired(self) -> bool:
        """Checks if the view has expired and should be removed."""
        now = datetime.now()
        return now - self._timestamp > timedelta(seconds=self.length)

    async def remove(self):
        """Removes the view, deleting if the message has no content."""
        if not self._msg or self._isdone:
            self._msg = None
            self._isdone = True
            return

        if self._callback:
            await self._callback(self._msg)
        self._isdone = True

        try:
            # If it is an empty message without the view, just remove it.
            if self.delete_msg:
                self._msg.components = []
                return await self._msg.delete()

            self._msg = await self._msg.edit(view=None)
        except BaseException:
            Log.debug("Could not remove the destructable view.")


class DestructableManager():
    """Manages all of the destructables."""
    # Message Id: Destructable
    _destructables: dict[int, Destructable] = {}

    @staticmethod
    def extend(msg_id: int, seconds: int) -> None:
        """Extends the time for a destructables by the amount of seconds passed
        to it.
        """
        destructable = DestructableManager.get(msg_id)
        if not destructable:
            return
        destructable.add_time(seconds)

    @staticmethod
    def get(msg_id: int) -> Optional[Destructable]:
        """Attempts to get a Destructable based on the message id."""
        return DestructableManager._destructables.get(msg_id)

    @staticmethod
    async def remove_one(msg_id: int, remote: bool) -> None:
        """Deletes a single Destructable locally, remotely if true."""
        destructable = DestructableManager.get(msg_id)
        if destructable:
            if remote and destructable.message:
                await destructable.remove()
            del DestructableManager._destructables[msg_id]

    @staticmethod
    async def remove_many(user_id: int, remote: bool,
                          category: Optional[Destructable.Category] = None) -> None:
        """Removes all destructables for a user with an optional type
        specified. If 'remote' is true, it will attempt to make an API request
        to remove them remotely.
        """
        # Build the list to remove.
        delete_me: list[int] = []
        for msgid, destruct in DestructableManager._destructables.items():
            if destruct.user_id == user_id:
                if category:
                    # Category specified, double check category type.
                    if destruct.category == category:
                        delete_me.append(msgid)
                else:
                    # Category does not matter, flag for deletion.
                    delete_me.append(msgid)

        # Remove the destructables
        for msgid in delete_me:
            to_delete = DestructableManager._destructables.get(msgid)
            if remote and to_delete:
                # Attempt to remove them remotely as well.
                await to_delete.remove()
            del DestructableManager._destructables[msgid]

    @staticmethod
    def add(destructable: Destructable) -> bool:
        """Adds a destructable, but only if the message is currently set."""
        msg = destructable.message
        if not msg:
            return False
        DestructableManager._destructables[msg.id] = destructable
        return True

    @staticmethod
    async def purge() -> None:
        """Removes all expired destructables."""
        # Check destructable views, if they are expired they will be removed.
        delete: list[int] = []
        for view_id, destruct in DestructableManager._destructables.items():
            if destruct.isexpired():
                await destruct.remove()
                delete.append(view_id)

        # Remove from memory.
        for i in delete:
            del DestructableManager._destructables[i]
