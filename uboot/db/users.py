from typing import Optional
from .db_socket import DbSocket, clean_name

# 0 : int - user_id
# 1 : int - gold
# 2 : int - msg_count
# 3 : int - gambles
# 4 : int - gambles_won
# 5 : int - button_press
UserRaw = tuple[int, int, int, int, int, int]


class UserDb(DbSocket):
    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.table_name = clean_name('users')
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} "\
            "( id INTEGER PRIMARY KEY DESC, "\
            "gold INTEGER, msg_count INTEGER, "\
            "gambles INTEGER, gambles_won INTEGER, "\
            "button_press INTEGER )"
        self.query['insert_one'] = "INSERT OR IGNORE INTO {table_name} "\
            "VALUES(?, ?, ?, ?, ?, ?)"

    def find_one(self, id: int) -> Optional[UserRaw]:
        where_key = f"id = {id}"
        return self._find_one(where_key)

    def find_all(self) -> list[UserRaw]:
        return self._find_many()

    def insert_one(self, raw: UserRaw) -> None:
        self._insert_one(raw)

    def update(self, raw: UserRaw) -> None:
        old = self.find_one(raw[0])
        if not old:
            return self.insert_one(raw)

        # Update it here.
        set_key = f"gold = {raw[1]}, msg_count = {raw[2]}, "\
            f"gambles = {raw[3]}, gambles_won = {raw[4]}, "\
            f"button_press = {raw[5]}"
        where_key = f"id = {raw[0]}"
        self._update(set_key, where_key)
