from collections.abc import Sequence
from datetime import datetime
from typing import Final

from discord import Color, Embed
from emoji import emojize
from humanize import apnumber, intcomma

from ttbot import TransitArrival, TransitLine, TransitStop, time

SEPARATOR: Final[str] = f"** **\n{'‾' * 48}\n** **"


def get_arrivals_error_embed(line: TransitLine, stop: TransitStop) -> Embed:
    vehicles = line.get_vehicle_noun(pluralize=True)
    return Embed(
        color=Color.brand_red(),
        title=f"\\{emojize(':no_entry:')}\u2002This doesn't look good...",
        description=(
            f"There are currently no `{line.display_name}` {vehicles} "
            f"due to arrive at **{stop.name}**. Please try again later!"
        ),
    )


def get_arrivals_detailed_embed(
    line: TransitLine,
    stop: TransitStop,
    arrivals: Sequence[TransitArrival],
    direction_text: str = "",
    query_time: int | None = None,
) -> Embed:
    current_time = time.get_datetime(query_time)
    embed = Embed(
        color=line.hex_color,
        title=f"\\{line.display_name}:\u2002{stop.name}",
        description=(
            f"Located **{apnumber(len(arrivals))}** incoming "
            + line.get_vehicle_noun(pluralize=len(arrivals) != 1)
            + (f" traveling {direction_text}." if direction_text else ".")
        ),
    )

    for number, arrival in enumerate(arrivals, start=1):
        vehicle_emoji = emojize(f":{apnumber(number)}:")
        vehicle_name = (
            f"{(vehicle_noun := line.get_vehicle_noun(pluralize=False)).title()} "
            f"{'#' if arrival.vehicle_id.isdigit() else ''}{arrival.vehicle_id}"
        )
        vehicle_title = f"{vehicle_emoji}\u2002**{vehicle_name}**"
        _add_arrival_fields(embed, arrival, current_time, vehicle_title, vehicle_noun)

    return embed


def _add_arrival_fields(
    embed: Embed,
    arrival: TransitArrival,
    current_time: datetime,
    vehicle_title: str,
    vehicle_noun: str,
) -> None:
    title_value = f"{vehicle_title} ({arrival.vehicle_sign})\n\u200B"
    embed.add_field(name=SEPARATOR, value=title_value, inline=False)

    def add_time_field(emoji_name: str, title: str, time_ms: int) -> None:
        timestamp = f"<t:{round(time_ms / 1000)}:T>"
        value = f"{timestamp}\n*({time.format_relative_time(time_ms, current_time)})*"
        _add_inline_field(embed, emoji_name, title, value)

    add_time_field("calendar_spiral", "Scheduled Arrival", arrival.scheduled_time)
    add_time_field("alarm_clock", "Estimated Arrival", arrival.estimated_time)

    distance_value = (
        f"{intcomma(feet := arrival.distance_ft)} ft *({round(feet / 5280, 2)} mi)*"
        f"\n{intcomma(round(feet / 3.281))} m *({round(feet / 3281, 2)} km)*"
    )
    _add_inline_field(embed, "map", "Distance from Station", distance_value)

    emoji, label = time.get_summary_text(arrival.scheduled_time, arrival.estimated_time)
    summary_value = f":{emoji}:\u2002This {vehicle_noun} {label}"
    embed.add_field(name="\u200B", value=summary_value, inline=False)


def _add_inline_field(embed: Embed, emoji_name: str, title: str, value: str) -> None:
    embed.add_field(
        name=f":{emoji_name}:\u2002{title}" + (" \u200B" * 6),
        value="\n:black_small_square:\u2002".join(["", *value.split("\n")]).strip(),
        inline=True,
    )
