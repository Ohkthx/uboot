"""Representation of a log. Keeps track of several items and manages the
connection between database and memory.
"""
from typing import Optional
from datetime import datetime
from enum import IntEnum, auto

from db.logs import LogDb, LogRaw


class LogType(IntEnum):
    """Determines the severity or type of the log."""
    INFO = auto()
    DEBUG = auto()
    ERROR = auto()
    COMMAND = auto()
    ACTION = auto()
    PLAYER = auto()


def make_raw(guild_id: int, user_id: int,
             logtype: LogType, msg: str) -> LogRaw:
    """Creates a raw log (tuple) fit for storing into a database with
    pre-defined defaults.
    """
    timestamp = datetime.utcnow().replace(microsecond=0).isoformat()
    return guild_id, user_id, int(logtype), timestamp, msg.replace("'", '')


class Log:
    """Representation of a log. Initialized with LogRaw."""
    debug_mode: bool = False
    _last_len: int = 0

    def __init__(self, raw: LogRaw) -> None:
        self.guild_id = raw[0]
        self.user_id = raw[1]
        self.type = LogType(raw[2])
        self.timestamp = raw[3].replace("'", '')
        self.message = raw[4].replace("'", '')

    def __str__(self) -> str:
        """Overrides the string method."""
        guild_text = '' if self.guild_id == 0 else f'[{self.guild_id}]'
        user_text = '' if self.user_id == 0 else f'[{self.user_id}]'
        return f"[{self.timestamp}]{guild_text}{user_text}"\
            f"[{self.type.name.lower()}] {self.message}"

    @property
    def _raw(self) -> LogRaw:
        """Converts the Log back into a LogRaw."""
        return (self.guild_id, self.user_id, int(self.type),
                f"'{self.timestamp}'", f"'{self.message}'")

    def save(self) -> None:
        """Stores the log into the database, saving it."""
        if Manager.db:
            Manager.db.insert_one(self._raw)

    @staticmethod
    def info(msg: str, end: str = '\n',
             guild_id: int = 0, user_id: int = 0) -> None:
        """Creates a normal print log."""
        return Log.do(msg, end=end,
                      guild_id=guild_id, user_id=user_id,
                      logtype=LogType.INFO)

    @staticmethod
    def debug(msg: str, end: str = '\n',
              guild_id: int = 0, user_id: int = 0) -> None:
        """Creates a debug log."""
        return Log.do(msg, end=end,
                      guild_id=guild_id, user_id=user_id,
                      logtype=LogType.DEBUG)

    @staticmethod
    def error(msg: str, end: str = '\n',
              guild_id: int = 0, user_id: int = 0) -> None:
        """Creates an error log."""
        return Log.do(msg, end=end,
                      guild_id=guild_id, user_id=user_id,
                      logtype=LogType.ERROR)

    @staticmethod
    def command(msg: str, end: str = '\n',
                guild_id: int = 0, user_id: int = 0) -> None:
        """Creates a command log."""
        return Log.do(msg, end=end,
                      guild_id=guild_id, user_id=user_id,
                      logtype=LogType.COMMAND)

    @staticmethod
    def action(msg: str, end: str = '\n',
               guild_id: int = 0, user_id: int = 0) -> None:
        """Creates an action log."""
        return Log.do(msg, end=end,
                      guild_id=guild_id, user_id=user_id,
                      logtype=LogType.ACTION)

    @staticmethod
    def player(msg: str, end: str = '\n',
               guild_id: int = 0, user_id: int = 0) -> None:
        """Creates an action log."""
        return Log.do(msg, end=end,
                      guild_id=guild_id, user_id=user_id,
                      logtype=LogType.PLAYER)

    @staticmethod
    def do(msg: str, end: str = '\n',
           guild_id: int = 0, user_id: int = 0,
           logtype: LogType = LogType.INFO) -> None:
        """Creates a log input, saving if it ends in a new line."""
        if logtype == LogType.INFO:
            Log._print(f"[{logtype.name.lower()}] {msg}", end=end)
        if logtype == LogType.DEBUG:
            Log._debug(f"[{logtype.name.lower()}] {msg}", end=end)
        if logtype == LogType.ERROR:
            Log._error(f"[{logtype.name.lower()}] {msg}", end=end)
        if logtype >= LogType.COMMAND:
            Log._print(f"[{logtype.name.lower()}] {msg}", end=end)

        # Ignore in-line messages.
        if end != '\n':
            return

        # Create and save the log.
        log = Log(make_raw(guild_id, user_id, logtype, msg))
        log.save()

    @staticmethod
    def clear() -> None:
        """Clears the current line, this is used on updating text."""
        print(' ' * Log._last_len, end='\r')

    @staticmethod
    def _print(text: str, end: str = '\n') -> None:
        """Prints text to console. By default, it creates a new line.
        Passing '\r' makes it return the cursor to the beginning of the line.
        """
        diff: int = Log._last_len - len(text)
        extra = ''
        if diff > 0:
            extra = ' ' * diff
        print(f"{text}{extra}", end=end)
        Log._last_len = len(text)

    @staticmethod
    def _debug(text: str, end: str = '\n') -> None:
        """Only prints the text passed if debug mode is currently set."""
        if not Log.debug_mode:
            return
        Log._print(text, end=end)

    @staticmethod
    def _error(text: str, end: str = '\n') -> None:
        """Prints text in the event of an error."""
        Log._print(text, end=end)


class Manager:
    """Manages the Log database in memory and in storage."""
    db: Optional[LogDb] = None
    _logs: list[Log] = []

    @staticmethod
    def init(dbname: str) -> None:
        """Initializes the Log Manager, connecting and loading from
        database.
        """
        Manager.db = LogDb(dbname)

    @staticmethod
    def get_guild_type(guild_id: int, logtype: LogType,
                       amount: int) -> list[Log]:
        """Get logs based on its guild and type."""
        if not Manager.db:
            return []
        raw_logs = Manager.db.find_guild_type(guild_id, int(logtype))
        logs = [Log(log) for log in raw_logs]
        return logs[-amount:]

    @staticmethod
    def get_guild_user(guild_id: int, user_id: int, amount: int) -> list[Log]:
        """Get logs based on its guild and user."""
        if not Manager.db:
            return []
        raw_logs = Manager.db.find_guild_user(guild_id, user_id)
        logs = [Log(log) for log in raw_logs]
        return logs[-amount:]
