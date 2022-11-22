from datetime import datetime, timedelta
from typing import Final

from discord.utils import utcnow
from humanize import naturaltime

ONE_MINUTE: Final[timedelta] = timedelta(minutes=1)


def format_relative_time(time_ms: int, relative_to: datetime | None = None) -> str:
    text = naturaltime(get_datetime(time_ms), when=relative_to or utcnow())

    if text.endswith(" from now"):
        text = f"in {text.replace(' from now', '')}"

    return text


def get_datetime(millis_since_epoch: int | None = None) -> datetime:
    return (
        datetime.fromtimestamp(millis_since_epoch / 1000)
        if millis_since_epoch
        else utcnow()
    )


def get_summary_text(scheduled_ms: int, estimated_ms: int) -> tuple[str, str]:
    scheduled_time = get_datetime(scheduled_ms)
    estimated_time = get_datetime(estimated_ms)

    if (scheduled_time - estimated_time) > ONE_MINUTE:
        return "racehorse", "is ahead of schedule!"
    elif (estimated_time - scheduled_time) > ONE_MINUTE:
        return "snail", "is running late."
    else:
        exact = scheduled_time == estimated_time
        return "rooster", f"should be {'right' if exact else 'approximately'} on time."
