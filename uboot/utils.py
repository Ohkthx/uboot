"""General utilities that are not big enough for their own category."""


class Log():
    """Wrapper for print that allows for more fancy output."""
    debug_mode: bool = False
    _last_len: int = 0

    @staticmethod
    def clear() -> None:
        """Clears the current line, this is used on updating text."""
        print(' ' * Log._last_len, end='\r')

    @staticmethod
    def print(text: str, end: str = '\n') -> None:
        """Prints text to console. By default it creates a new line.
        Passing '\r' makes it return the cursor to the beginning of the line.
        """
        diff: int = Log._last_len - len(text)
        extra = ''
        if diff > 0:
            extra = ' ' * (diff)
        print(f"{text}{extra}", end=end)
        Log._last_len = len(text)

    @staticmethod
    def debug(text: str, end: str = '\n') -> None:
        """Only prints the text passed if debug mode is currently set."""
        if not Log.debug_mode:
            return
        Log.print(text, end=end)
