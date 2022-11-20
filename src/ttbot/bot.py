import functools
import json
import re
from collections.abc import Callable
from pathlib import Path
from string import Template
from typing import Any, Final

import emoji
from aiohttp import ClientSession
from discord import ApplicationContext, Bot, ChannelType
from discord.abc import GuildChannel

from ttbot.data import TransitStop
from ttbot.log import Log
from ttbot.version import VERSION

_REPO_DATA_ROOT: Final[str] = "nuztalgia/transit-time/main/data"
_DATA_URL_TEMPLATE: Final[Template] = Template(
    f"https://raw.githubusercontent.com/{_REPO_DATA_ROOT}/$data_path.min.json"
)


# noinspection PyAbstractClass
class TransitTimeBot(Bot):
    def __init__(self, force_sync: bool, **options: Any) -> None:
        super().__init__(**options)

        self._transit_stops: Final[dict[str, list[TransitStop]]] = {}
        self._force_sync: Final[bool] = force_sync
        self._initialized: bool = False

        for file_path in Path(__file__).parent.glob("cogs/[!_]*.py"):
            Log.d(f"Loading extension '{file_path.stem}'.")
            self.load_extension(f"ttbot.cogs.{file_path.stem}")

    @property
    def http_session(self) -> ClientSession:
        # noinspection PyUnresolvedReferences, PyProtectedMember
        return self.http._HTTPClient__session

    async def clear_cache(self) -> None:
        Log.i("Clearing cached transit stops.")
        self._transit_stops.clear()

    async def get_transit_stops(self, data_path: str) -> list[TransitStop]:
        if data_path not in self._transit_stops:
            data_url = _DATA_URL_TEMPLATE.substitute(data_path=data_path)
            Log.d(f"Making HTTP request to fetch stops for '{data_path}'.")

            async with self.http_session.get(data_url) as response:
                stop_data_list = json.loads(await response.text())

            stops = [TransitStop(**stop_data) for stop_data in stop_data_list]
            Log.i(f"Successfully fetched {len(stops)} stops for '{data_path}'.")
            self._transit_stops[data_path] = stops
        else:
            Log.d(f"Returning cached stops for '{data_path}'.")

        return self._transit_stops[data_path]

    # noinspection PyMethodMayBeStatic
    async def on_application_command(self, ctx: ApplicationContext) -> None:
        command_name = ctx.command.qualified_name
        channel_name = _get_channel_name(ctx.channel)
        Log.i(f"{ctx.user} used command '{command_name}' in {channel_name}.")

    async def on_ready(self) -> None:
        if self._initialized:
            Log.i("Received another 'on_ready' event. Ignoring.")
            return

        if self._force_sync:
            Log.w("Force-syncing commands. Be mindful of the rate limit.")
            await self.sync_commands(force=True)

        Log.i(f"Transit Time Bot v{VERSION} is online and ready!")
        self._initialized = True


def _get_channel_name(channel: GuildChannel) -> str:
    if channel.type == ChannelType.private:
        return "a direct message"
    else:
        sanitized_name = _sanitize_channel_name(emoji.demojize(channel.name))
        return f"#{sanitized_name}" if sanitized_name else f"Channel #{channel.id}"


_sanitize_channel_name: Final[Callable[[str], str]] = functools.partial(
    re.compile(r"(:[\w-]+:|^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$)", re.ASCII).sub, ""
)
