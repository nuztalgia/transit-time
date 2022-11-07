import json
import logging
import os
import re
from argparse import ArgumentParser, Namespace
from collections.abc import Callable, Sequence
from dataclasses import InitVar, asdict, dataclass, field
from functools import partial
from pathlib import Path
from string import Template
from typing import Any, Final
from urllib.parse import quote_plus

import dotenv
import requests
from rich import box
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Column, Table

DESCRIPTION: Final[str] = (
    "Fetches data from the TriMet API, processes it, "
    "and saves the results in this directory."
)
DATA_PATH: Final[Path] = Path(__file__).parent.resolve()

TRACKED_ROUTES: Final[tuple[int, ...]] = (90, 100, 190, 200, 290)
ROUTE_TYPES: Final[dict[str, str]] = {"R": "Rail", "B": "Bus"}

HEADER_TEMPLATE: Final[Template] = Template(
    "![$route_name](https://placehold.co/820x100/$route_color/fff?"
    "text=Route+${route_id}+%28${route_name_encoded}%29&font=montserrat)"
)
STOP_LINK_TEMPLATE: Final[Template] = Template(
    "[`${id}`](https://www.google.com/maps/search/?api=1&query=${lat}%2C${long})"
)


@dataclass(frozen=True, kw_only=True)
class Stop:
    id: int
    name: str
    direction: str
    lat: float
    long: float


@dataclass(frozen=True, kw_only=True)
class Route:
    id: int
    name: str
    type: str
    color: str
    directions: InitVar[dict[str, list[dict[str, Any]]]]
    direction_stops: dict[str, list[Stop]] = field(default_factory=dict)
    log: InitVar[Callable[[str], None]] = print

    def __post_init__(
        self, directions: dict[str, list[dict[str, Any]]], log: Callable[[str], None]
    ):
        log_connector = "─" * (7 - len(str(self.id)))
        for direction_name, raw_stops in directions.items():
            last_stop_index = len(raw_stops) - 1
            log(
                f"[bright_magenta]> Route [bright_green]{self.id}[bright_magenta]"
                f" {log_connector} [bright_yellow]{self.name} ({direction_name})",
            )
            self.direction_stops[direction_name] = [
                self._create_stop(
                    direction_name, raw_stop, stop_index, last_stop_index, log
                )
                for stop_index, raw_stop in enumerate(raw_stops)
            ]

    def _create_stop(
        self,
        direction_name: str,
        raw_stop: dict[str, Any],
        stop_index: int,
        last_stop_index: int,
        log: Callable[[str], None],
    ) -> Stop:
        name = re.sub(r" MAX St(?:atio)?n$", "", raw_stop["desc"].replace("/ ", "/"))
        stop_id, lat, long = raw_stop["locid"], raw_stop["lat"], raw_stop["lng"]

        if stop_index == last_stop_index:
            direction = f"Terminus ({direction_name.replace('To ', '')})"
        elif raw_direction := raw_stop["dir"]:
            direction = f"{raw_direction} ({direction_name})"
        elif stop_id == 10579:
            # API returns an empty string for the "dir" of this particular stop.
            direction = f"Eastbound ({direction_name})"
        else:
            raise ValueError(f"Empty direction for stop '{name}' on route {self.name}.")

        log(
            f"  [cyan]{str(stop_index + 1).zfill(2)})[/] Stop "
            f"[bright_cyan]{str(stop_id).rjust(5)} [bright_black]{name}"
        )
        return Stop(id=stop_id, name=name, direction=direction, lat=lat, long=long)

    def _get_readme_markdown(self) -> str:
        header = HEADER_TEMPLATE.substitute(
            route_color=self.color,
            route_id=self.id,
            route_name=self.name,
            route_name_encoded=quote_plus(self.name),
        )
        markdown = f'<div align="center">\n\n{header}\n\n<table>\n<tr>\n'
        format_stop_link = STOP_LINK_TEMPLATE.safe_substitute

        for direction_name, stops in self.direction_stops.items():
            col1 = [format_stop_link(**asdict(stop)) for stop in stops]
            col2 = [stop.name for stop in stops]
            col1_size, col2_size = max(len(s) for s in col1), max(len(s) for s in col2)
            markdown += (
                f'<td align="center" width=410>\n\n## {direction_name}\n\n'
                f"| {'Stop ID'.ljust(col1_size)} | {'Stop Name'.ljust(col2_size)} |\n"
                f"| :{'-' * (col1_size - 2)}: | {'-' * col2_size} |\n"
                + "\n".join(
                    f"| {stop_link.ljust(col1_size)} | {stop_name.ljust(col2_size)} |"
                    for stop_link, stop_name in zip(col1, col2)
                )
                + "\n\n</td>\n"
            )

        markdown += "</tr>\n</table>\n\n</div>"
        return markdown

    def write_files(self) -> None:
        data_dir = DATA_PATH / self.type.lower() / self.name.lower().replace(" ", "-")
        data_dir.mkdir(parents=True, exist_ok=True)

        def write_file(contents: str, name: str, ext: str = "json") -> None:
            file_path = data_dir / f"{name}.{ext}"
            file_path.write_text(f"{contents.strip()}\n", newline="\n")

        write_file(self._get_readme_markdown(), "readme", "md")

        for direction_name, stops in self.direction_stops.items():
            file_name = re.sub(r"\W", "-", direction_name.lower())
            stops_to_json = partial(json.dumps, [asdict(stop) for stop in stops])
            write_file(stops_to_json(indent=2), file_name)
            write_file(stops_to_json(separators=(",", ":")), f"{file_name}.min")


def parse_args(argv: Sequence[str] | None) -> Namespace:
    parser = ArgumentParser(description=DESCRIPTION, add_help=False)
    parser.add_argument(
        "-v", "--verbose", help="Enable verbose console output.", action="store_true"
    )
    parser.add_argument("-h", "--help", help="Show this help message.", action="help")
    return parser.parse_args(argv)


def get_logger(verbose: bool) -> logging.Logger:
    base_log_level = logging.DEBUG if verbose else logging.INFO
    handler = RichHandler(
        omit_repeated_times=False, show_level=False, show_path=False, markup=True
    )
    logging.basicConfig(
        format="%(message)s", datefmt="[%X]", level=base_log_level, handlers=[handler]
    )
    return logging.getLogger(__name__)


def fetch_routes() -> list[dict[str, Any]] | None:
    dotenv.load_dotenv()
    response = requests.get(
        "https://developer.trimet.org/ws/V1/routeConfig",
        params={
            "appID": os.environ.get("TRIMET_APP_ID"),
            "dir": True,
            "json": True,
            "stops": True,
        },
    )
    if response.status_code == requests.codes.ok:
        return response.json().get("resultSet", {}).get("route")
    else:
        return None


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    log = get_logger(args.verbose)

    log.debug("Requesting all routes from TriMet API.")
    routes = fetch_routes()

    if not routes:
        error_message = "Unable to fetch routes from TriMet API."
        log.error(f"[bright_red]ERROR: {error_message} Exiting.")
        return 1

    log.info(f"Received {len(routes)} routes from TriMet API.")
    route_table_rows, route_initializers = [], []

    for raw_route in routes:
        route_table_rows.append(
            (
                str(route_id := raw_route["id"]),
                route_name := raw_route["desc"].strip(),
                route_type := ROUTE_TYPES[raw_route["type"]],
                str(len(directions := raw_route.get("dir", []))),
                "[bright_green]Y" if (tracked := route_id in TRACKED_ROUTES) else "N",
            )
        )
        if tracked:
            if len(directions) == 2:
                initialize_route = partial(
                    Route,
                    id=route_id,
                    name=route_name,
                    type=route_type,
                    color=raw_route.get("routeColor", "000"),
                    directions={
                        d.get("desc", "Unknown").strip(): d.get("stop", [])
                        for d in directions
                    },
                )
                route_initializers.append(initialize_route)
            else:
                warning_message = f"Unexpected number of directions for {route_name}."
                log.warning(f"[bright_yellow]WARNING: {warning_message} Skipping.")
                log.debug(raw_route)

    if args.verbose:
        route_table = Table(
            Column("ID", justify="right", style="bright_cyan"),
            Column("Name"),
            Column("Type"),
            Column("Dirs", justify="center"),
            Column("Tracked?", justify="center", style="bright_black"),
            title="",
            box=box.ROUNDED,
            header_style="bright_magenta",
        )
        for row in route_table_rows:
            route_table.add_row(*row)
        Console(log_path=False).log(route_table)

    log.info(f"Populating data files for {len(route_initializers)} tracked routes.")
    log.debug(f"[bright_magenta]└── {TRACKED_ROUTES=}")
    callable_log = partial(log.debug, extra={"highlighter": None})

    for initialize_route in route_initializers:
        route = initialize_route(log=callable_log)
        route.write_files()

    log.info("[bright_green]Completed successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
