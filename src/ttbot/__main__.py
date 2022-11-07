from botstrap import Botstrap, CliColors, Color
from discord import Bot

from ttbot import VERSION


# noinspection PyAbstractClass,PyMethodMayBeStatic
class TransitTimeBot(Bot):
    def __init__(self, **options) -> None:
        super().__init__(**options)
        # TODO: Implement cogs and load them here.

    async def on_ready(self) -> None:
        print(f"Transit Time Bot v{VERSION} is online and ready!")


def main() -> int:
    colors = CliColors(primary=Color.cyan, highlight=Color.pink)
    botstrap = Botstrap(name="transit-time-bot", version=VERSION, colors=colors)
    botstrap.run_bot(TransitTimeBot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
