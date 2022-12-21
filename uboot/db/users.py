"""Database manager for User settings."""
from typing import Optional

from .db_socket import DbSocket, clean_name

# 0 : int - user_id
# 1 : int - gold
# 2 : int - msg_count
# 3 : int - gambles
# 4 : int - gambles_won
# 5 : int - button_press
# 6 : int - monsters
# 7 : int - kills
# 8 : int - exp
# 9 : int - locations
# 10: int - c_location
# 11: int - deaths
UserRaw = tuple[int, int, int, int, int, int, int, int, int, int, int, int]


class UserDb(DbSocket):
    """Database manager for User settings."""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.table_name = clean_name('users')
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} "\
            "( id INTEGER PRIMARY KEY DESC, "\
            "gold INTEGER, msg_count INTEGER, "\
            "gambles INTEGER, gambles_won INTEGER, "\
            "button_press INTEGER, "\
            "monsters INTEGER, kills INTEGER, exp INTEGER, "\
            "locations INTEGER, c_location INTEGER, "\
            "deaths INTEGER )"
        self.query['insert_one'] = "INSERT OR IGNORE INTO {table_name} "\
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

    def find_one(self, user_id: int) -> Optional[UserRaw]:
        """Gets a single user based on its id."""
        where_key = f"id = {user_id}"
        return self._find_one(where_key)

    def find_all(self) -> list[UserRaw]:
        """Pulls all users from database."""
        return self._find_many()

    def insert_one(self, raw: UserRaw) -> None:
        """Adds one user to the database only if it does not exist."""
        self._insert_one(raw)

    def update(self, raw: UserRaw) -> None:
        """Updates a user in the database, if it does not exist it will
        be created.
        """
        old = self.find_one(raw[0])
        if not old:
            return self.insert_one(raw)

        # Update it here.
        set_key = f"gold = {raw[1]}, msg_count = {raw[2]}, "\
            f"gambles = {raw[3]}, gambles_won = {raw[4]}, "\
            f"button_press = {raw[5]}, "\
            f"monsters = {raw[6]}, kills = {raw[7]}, exp = {raw[8]}, "\
            f"locations = {raw[9]}, c_location = {raw[10]}, "\
            f"deaths = {raw[11]}"
        where_key = f"id = {raw[0]}"
        self._update(set_key, where_key)
        return None
