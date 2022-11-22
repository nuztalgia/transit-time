import functools
import json
import re
from string import Template
from typing import Final, cast

import uikitty
from discord import ButtonStyle, Cog, Embed
from discord.commands import ApplicationContext, SlashCommandGroup
from dotenv import dotenv_values

from ttbot import Log, TransitArrival, TransitLine, TransitStop, TransitTimeBot, embeds

_DESCRIPTION_TEMPLATE: Final[Template] = Template("Check transit times in ${area}.")
_AREA_NAME_REGEX: Final[re.Pattern] = re.compile(
    re.sub(r"\$\{\w+}\.$", r"(?P<area>.+)\.$", _DESCRIPTION_TEMPLATE.template)
)

_TRIMET_APP_ID: Final[str] = dotenv_values().get("TRIMET_APP_ID", "")
_MAX_ARRIVALS: Final[int] = 5


def _get_command_description(area_name: str) -> str:
    return _DESCRIPTION_TEMPLATE.substitute(area=area_name)


def _get_area_name(command_desc: str) -> str:
    return cast(re.Match, _AREA_NAME_REGEX.search(command_desc)).group("area")


class TransitCog(Cog):
    def __init__(self, bot: TransitTimeBot) -> None:
        self.bot: Final[TransitTimeBot] = bot

    transit: Final[SlashCommandGroup] = SlashCommandGroup(
        name="transit",
        description="Commands for checking transit times in supported cities.",
    )

    @transit.command(description=_get_command_description("Portland, Oregon"))
    async def pdx(self, ctx: ApplicationContext) -> None:
        line, stop, direction = await self._get_transit_parameters(ctx)
        arrivals_url = "https://developer.trimet.org/ws/v2/arrivals"
        params = {"locIds": stop.id, "appID": _TRIMET_APP_ID, "arrivals": _MAX_ARRIVALS}

        stop_log_info = f"#{stop.id}: {stop.name}, {stop.direction}"
        Log.d(f"Fetching {line.name} arrivals for stop {stop_log_info}.")

        async with self.bot.http_session.get(arrivals_url, params=params) as response:
            results = json.loads(await response.text()).get("resultSet", {})

        arrivals = [
            TransitArrival(
                vehicle_id=arrival["vehicleID"],
                vehicle_sign=arrival.get("shortSign", f"To {direction}"),
                scheduled_time=arrival.get("scheduled", 0),
                estimated_time=arrival.get("estimated", 0),
                distance_ft=arrival.get("feet", 0),
            )
            for arrival in results.get("arrival", [])
            if (
                arrival.get("vehicleID")
                and (arrival.get("status") == "estimated")
                and (arrival.get("route") == line.system_id)
            )
        ]

        if not arrivals:
            Log.e(f"Invalid results from TriMet API: {json.dumps(results)}")
            await ctx.edit(embed=embeds.get_arrivals_error_embed(line, stop), view=None)
            return

        location = results.get("location", [{}])[0]
        direction_label = f"{location['dir'].lower()} " if location.get("dir") else ""
        direction_text = f"{direction_label}to **{direction}**"

        embed = embeds.get_arrivals_detailed_embed(
            line, stop, arrivals, direction_text, results.get("queryTime")
        )
        Log.d(embed.description.replace("*", ""))
        await ctx.edit(embed=embed, view=None)  # TODO: Show buttons for quick access.

    async def _get_transit_parameters(
        self, ctx: ApplicationContext
    ) -> tuple[TransitLine, TransitStop, str]:
        get_user_choice = functools.partial(
            uikitty.dynamic_select,
            ctx,
            log=lambda message: Log.d(f"{' ' * 4}{message}"),
        )
        area_code = ctx.command.name.strip().strip("_").upper()
        area_name = _get_area_name(getattr(ctx.command, "description", area_code))
        area_lines = TransitLine.for_area_code(area_code)

        await ctx.response.defer(ephemeral=True, invisible=False)
        Log.d(f"└── {len(area_lines)} supported transit lines in {area_name}.")

        transit_line = await get_user_choice(
            embed=Embed(title=f"Select a transit line in {area_name}."),
            **area_lines,
        )
        line_name = transit_line.display_name
        create_embed = functools.partial(Embed, color=transit_line.hex_color)

        direction = await get_user_choice(
            embed=create_embed(title=f"Select a direction for `{line_name}`."),
            button_style=ButtonStyle.primary,
            **{f"To {direction}": direction for direction in transit_line.directions},
        )
        stops = await self.bot.get_transit_stops(transit_line.get_data_path(direction))

        transit_stop = await get_user_choice(
            embed=create_embed(
                title=f"You're going to {direction}!",
                description=f"Select a stop to check `{line_name}` arrival times.",
            ),
            **{stop.name: stop for stop in stops},
        )
        return transit_line, transit_stop, direction


def setup(bot: TransitTimeBot) -> None:
    bot.add_cog(TransitCog(bot))
