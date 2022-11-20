from __future__ import annotations

import re
from enum import Enum
from typing import Final, NamedTuple


class TransitStop(NamedTuple):
    id: int
    name: str
    direction: str
    lat: float
    long: float


class TransitLine(Enum):
    def __init__(self, display_name: str, hex_color: int, *directions: str) -> None:
        self.display_name: Final[str] = display_name
        self.hex_color: Final[int] = hex_color
        self.directions: Final[tuple[str, ...]] = directions

    @classmethod
    def for_area_code(cls, area_code: str) -> dict[str, TransitLine]:
        return {
            transit_line.display_name: transit_line
            for transit_line in TransitLine
            if transit_line.name.startswith(area_code)
        }

    def get_data_path(self, direction: str) -> str:
        if direction not in self.directions:
            raise ValueError(f"Invalid direction for {self.name}: '{direction}'")

        path_directory = self.name.replace("__", "/").replace("_", "-").lower()
        path_file = re.sub(r"\W", "-", f"to-{direction.lower()}")

        return f"{path_directory}/{path_file}"

    PDX__RAIL__MAX_BLUE_LINE = (
        "🔵 MAX Blue Line",
        0x084C8D,
        "Gresham",
        "Hillsboro",
    )
    PDX__RAIL__MAX_GREEN_LINE = (
        "🟢 MAX Green Line",
        0x008852,
        "Clackamas Town Center",
        "Portland City Center/PSU",
    )
    PDX__RAIL__MAX_ORANGE_LINE = (
        "🟠 MAX Orange Line",
        0xF58220,
        "Portland City Center",
        "Milwaukie",
    )
    PDX__RAIL__MAX_RED_LINE = (
        "🔴 MAX Red Line",
        0xD81526,
        "Portland International Airport",
        "Beaverton Transit Center",
    )
    PDX__RAIL__MAX_YELLOW_LINE = (
        "🟡 MAX Yellow Line",
        0xF8C213,
        "Expo Center",
        "Portland City Center",
    )
