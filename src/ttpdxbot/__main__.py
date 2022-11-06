from botstrap import Botstrap, CliColors, Color

from ttpdxbot import VERSION
from ttpdxbot.bot import Bot


def main() -> int:
    colors = CliColors(primary=Color.cyan, highlight=Color.pink)
    Botstrap(name="tt-pdx-bot", version=VERSION, colors=colors).run_bot(Bot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
