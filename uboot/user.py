from typing import Optional


class User():
    def __init__(self, id: int, gold: int = 0, msg_count: int = 0) -> None:
        self.id = id
        self.gold = gold
        self.msg_count = msg_count


class UserManager():
    def __init__(self, users: list[User]) -> None:
        self.users = users

    def add(self, user: User) -> None:
        return

    def get(self, user_id: int) -> Optional[User]:
        return None
