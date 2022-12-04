from datetime import datetime, timedelta

# 0 : int - user_id
# 1 : int - gold
# 2 : int - msg_count
# 3 : int - gambles
# 4 : int - gambles_won
# 5 : int - button_press
UserRaw = tuple[int, int, int, int, int, int]


def make_raw(user_id: int) -> UserRaw:
    return (user_id, 0, 0, 0, 0, 0)


class User():
    def __init__(self, raw: UserRaw) -> None:
        self.id = raw[0]
        self.gold = raw[1]
        self.msg_count = raw[2]
        self.gambles = raw[3]
        self.gambles_won = raw[4]
        self.button_press = raw[5]
        self.last_message = datetime.now() - timedelta(seconds=20)

    def __str__(self) -> str:
        return f"id: {self.id}, gold: {self.gold}, msgs: {self.msg_count}"

    @property
    def _raw(self) -> UserRaw:
        return (self.id, self.gold, self.msg_count, self.gambles,
                self.gambles_won, self.button_press)

    def add_message(self) -> None:
        self.msg_count += 1
        now = datetime.now()
        time_diff = now - self.last_message
        if time_diff >= timedelta(seconds=15):
            self.gold += 1
            self.last_message = now

    def win_rate(self) -> float:
        if self.gambles == 0:
            return 0
        return (1 + (self.gambles_won - self.gambles) /
                self.gambles) * 100

    def minimum(self, floor: int) -> float:
        minimum_offset = int(self.gold * 0.1)
        return minimum_offset if minimum_offset > floor else floor


class Manager():
    _users: dict[int, User] = {}

    @staticmethod
    def add(user: User) -> User:
        Manager._users[user.id] = user
        return user

    @staticmethod
    def get(user_id: int) -> User:
        user = Manager._users.get(user_id)
        if not user:
            user = User(make_raw(user_id))
            Manager.add(user)
        return user

    @staticmethod
    def getall() -> list[User]:
        return list(Manager._users.values())
