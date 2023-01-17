"""Entrance into the application."""
from typing import Optional

from config import GeneralConfig, CONFIG_FILENAME
from managers.logs import Log, Manager as LogManager
from dclient import DiscordBot


def main() -> None:
    """Entrance function into the application."""
    config: Optional[GeneralConfig] = None

    try:
        # Load the configuration file.
        config = GeneralConfig.load_config()
    except BaseException as err:
        Log.error(f"Error while loading configuration file:\n{str(err)}")
        return

    # Create the configuration file if it could not be loaded.
    if not config:
        Log.info(f"Configuration file '{CONFIG_FILENAME}' does not exist.")
        if GeneralConfig.make_default_config():
            Log.info(f"Default config: '{CONFIG_FILENAME}' created.")
        return

    Log.debug_mode = config.debug
    Log.debug("DEBUG is set")
    Log.debug(f"PREFIX: {config.discord.prefix}")

    LogManager.init("uboot.sqlite3")

    # Start the discord bot.
    DiscordBot.init_run(config.discord)


if __name__ == "__main__":
    main()
