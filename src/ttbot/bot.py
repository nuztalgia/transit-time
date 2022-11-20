import functools
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final

import emoji
from aiohttp import ClientSession
from discord import ApplicationContext, Bot, ChannelType
from discord.abc import GuildChannel

from ttbot import VERSION
from ttbot.log import Log


# noinspection PyAbstractClass
class TransitTimeBot(Bot):
    def __init__(self, force_sync: bool, **options: Any) -> None:
        super().__init__(**options)

        self._force_sync: Final[bool] = force_sync
        self._initialized: bool = False

        for file_path in Path(__file__).parent.glob("cogs/[!_]*.py"):
            Log.d(f"Loading extension '{file_path.stem}'.")
            self.load_extension(f"ttbot.cogs.{file_path.stem}")

    @property
    def http_session(self) -> ClientSession:
        # noinspection PyUnresolvedReferences, PyProtectedMember
        return self.http._HTTPClient__session

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
