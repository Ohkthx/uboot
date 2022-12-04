from config import ProjectConfig, CONFIG_FILENAME
from utils import Log
from dclient import DiscordBot


def main() -> None:
    # Load the configuration file.
    config = ProjectConfig.load_config()
    if config is None:
        Log.print(f"Configuration file '{CONFIG_FILENAME}' does not exist.")
        if ProjectConfig.make_default_config():
            Log.print(f"Default config: '{CONFIG_FILENAME}' created.")
        return

    Log.debug_mode = config.debug
    Log.debug("DEBUG is set")
    Log.debug(f"PREFIX: {config.discord.prefix}")

    # Start the discord bot.
    DiscordBot.init_run(config.discord)


if __name__ == "__main__":
    main()
