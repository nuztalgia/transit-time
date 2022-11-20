from botstrap import Botstrap, CliColors, Color, Option
from discord import Activity, ActivityType

from ttbot.log import Log
from ttbot.version import VERSION


def main() -> int:
    colors = CliColors(primary=Color.cyan, highlight=Color.pink)
    botstrap = Botstrap(name="transit-time-bot", version=VERSION, colors=colors)

    args = botstrap.parse_args(
        loglevel=Option(
            default=2,
            choices=range(1, 5),
            help="A value from 1 to 4 specifying the lowest message level to log.",
        ),
        force_sync=Option(
            flag=True,
            help="Sync all commands regardless of their current state on Discord.",
        ),
    )
    Log.config(level=args.loglevel)

    activity = Activity(type=ActivityType.listening, name="/transit pdx")
    botstrap.run_bot(
        "ttbot.bot.TransitTimeBot", activity=activity, force_sync=args.force_sync
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
