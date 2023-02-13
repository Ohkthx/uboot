from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Union


class Action:
    """Logs a user action, that will be completed later."""

    class Types(Enum):
        """Various types of actions that can be taken."""
        NONE = "none"
        ITEM_MOVE = "item_move"

    def __init__(self,
                 user_id: int,
                 action_type: Types = Types.NONE,
                 expire_seconds: int = 300) -> None:
        self.user_id: int = user_id
        self.type = action_type
        self.created_at: datetime = datetime.now()
        self.expire_time = expire_seconds

    @property
    def is_expired(self) -> bool:
        """Checks if an action is expired and should be removed."""
        maximum_time = timedelta(seconds=self.expire_time)
        return datetime.now() - self.created_at > maximum_time

    def refresh(self) -> None:
        """Refreshes the expiration timer."""
        self.created_at = datetime.now()

    def set_expire(self) -> None:
        """Flags the action as being expired."""
        self.created_at -= timedelta(seconds=self.expire_time)


class ItemMove(Action):
    """Action used to move items between inventories."""

    def __init__(self, user_id: int) -> None:
        super().__init__(user_id,
                         action_type=Action.Types.ITEM_MOVE,
                         expire_seconds=300)
        self.source_id: str = ""
        self.destination_id: str = ""
        self.item_id: str = ""


class Manager:
    actions: list[Action] = []

    @staticmethod
    def add(action: Union[Action, ItemMove]) -> None:
        """Adds an action to the queue."""
        Manager.actions.append(action)
        sorted(Manager.actions, key=lambda a: a.created_at)

    @staticmethod
    def get(user_id: int, action_type: Action.Types,
            ) -> Optional[Union[Action, ItemMove]]:
        """Attempts to get an action in queue."""
        for action in Manager.actions:
            if action.type == action_type and action.user_id == user_id:
                if action.is_expired:
                    Manager.remove(user_id, action_type)
                    return None
                return action
        return None

    @staticmethod
    def remove(user_id: int, action_type: Action.Types) -> None:
        """Attempts to remove an action from queue."""
        keepers: list[Action] = []
        for action in Manager.actions:
            if action.type == action_type and user_id == action.user_id:
                continue
            keepers.append(action)
        Manager.actions = keepers
