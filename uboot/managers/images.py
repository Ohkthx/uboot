"""Handles all images used by the bot."""
import os
import pathlib
from typing import Optional

import discord


class Manager:
    """Manages the images."""
    # [file name] path
    _images: dict[str, pathlib.Path] = {}

    @staticmethod
    def init() -> None:
        """Initialized all entities images."""
        Manager.load_images()

    @staticmethod
    def load_images() -> None:
        """Loads all the images from the image directory."""
        dirname = os.getcwd()
        path = pathlib.Path(os.path.join(dirname, 'images', 'entities'))
        if not path.exists():
            return

        # For each one that IS a file.
        for item in path.iterdir():
            if not item.is_file() or item.name == "__init__.py":
                continue

            # Create a binding.
            name, path = item.name, item.absolute()
            Manager._images[name] = path

    @staticmethod
    def get(filename: str) -> Optional[discord.File]:
        """Gets an image, loading it from storage and converting to a discord
        image file.
        """
        path = Manager._images.get(filename, None)
        if path:
            return discord.File(path, filename=filename)
        return None
