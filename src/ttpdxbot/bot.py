import discord

from ttpdxbot import VERSION


# noinspection PyAbstractClass,PyMethodMayBeStatic
class Bot(discord.Bot):
    def __init__(self, **options) -> None:
        super().__init__(**options)
        # TODO: Implement cogs and load them here.

    async def on_ready(self) -> None:
        print(f"Train Tracker PDX Bot v{VERSION} is online and ready!")
