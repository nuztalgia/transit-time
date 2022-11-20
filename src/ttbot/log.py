import logging
import sys
from typing import Final, Literal

from botstrap import Color


class Log:
    _logger: Final[logging.Logger] = logging.getLogger(__name__)

    @classmethod
    def config(cls, level: Literal[1, 2, 3, 4] = 2) -> None:
        logging.basicConfig(
            level=max(level + 1, 4) * 10,
            style="{",
            format=Color.cyan("[{asctime}]") + " {message}",
            datefmt="%Y-%m-%d %H:%M:%S",
            stream=sys.stdout,
        )
        cls._logger.setLevel(level * 10)

    @classmethod
    def d(cls, message: str) -> None:
        cls._logger.debug(Color.grey(message))

    @classmethod
    def i(cls, message: str) -> None:
        cls._logger.info(message)

    @classmethod
    def w(cls, message: str) -> None:
        cls._logger.warning(Color.yellow(f"WARNING: {message}"))

    @classmethod
    def e(cls, message: str) -> None:
        cls._logger.error(Color.red(f"ERROR: {message}"))
