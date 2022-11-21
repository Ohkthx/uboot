from typing import Callable


def catch_kbdint(func: callable):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except KeyboardInterrupt:
            print("CAUGHT KEYBOARD INTERRUPT.")
    return wrapper


class Log():
    debug_mode: bool = False
    _last_len: int = 0

    @staticmethod
    def clear() -> None:
        print(' ' * Log._last_len, end='\r')

    @staticmethod
    def print(text: str, end: str = '\n') -> None:
        diff: int = Log._last_len - len(text)
        extra = ''
        if diff > 0:
            extra = ' ' * (diff)
        print(f"{text}{extra}", end=end)
        Log._last_len = len(text)

    @staticmethod
    def debug(text: str, end: str = '\n') -> None:
        if not Log.debug_mode:
            return
        Log.print(text, end=end)
