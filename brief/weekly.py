"""Weekly summary: events and deadlines of the coming Monday-Sunday."""

import sys
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from brief import calendar, config, deadlines, utils

WEEKLY_DAY_PREFIX = calendar.CALENDAR_PREFIX  # e.g. "📆 <b>Lundi 23</b>"
WEEKLY_DEADLINES_HEADER = "⏰ <b>Échéances de la semaine</b>"


def coming_week(day: date) -> tuple[date, date]:
    """Next Monday (strictly after `day`) and the Sunday after it."""
    start = day + timedelta(days=7 - day.weekday())
    return start, start + timedelta(days=6)


def _date_without_year(d: date) -> str:
    return utils.format_long_date(d).rsplit(" ", 1)[0]


def build_weekly_sections() -> list[str]:
    """Header, one section per day with events, the week's deadlines and a
    count line. The calendar and deadline parts fail independently."""
    start, end = coming_week(utils.today())
    sections = [
        f"🗓 <b>Semaine du {_date_without_year(start)} au {_date_without_year(end)}</b>"
    ]
    n_events = n_deadlines = 0
    unknown = False  # a part failed, so the week may not actually be free

    if calendar.calendar_urls():
        try:
            calendars, failed = calendar.fetch_calendars()
            if not calendars:
                raise RuntimeError("all calendars failed")
            tz = ZoneInfo(config.TIMEZONE)
            for offset in range(7):
                day = start + timedelta(days=offset)
                events = calendar.merged_events(calendars, day, tz)
                if not events:
                    continue  # skip days without events
                n_events += len(events)
                day_name = utils.DAYS[day.weekday()].capitalize()
                header = f"{WEEKLY_DAY_PREFIX}{day_name} {day.day}</b>"
                sections.append("\n".join(
                    [header] + [f"{when}  {utils.escape(title)}" for when, title in events]
                ))
            if failed:
                sections.append(f"⚠️ {failed} agenda(s) indisponible(s).")
        except Exception as exc:
            print(f"[warn] weekly calendar failed: {type(exc).__name__}", file=sys.stderr)
            sections.append("⚠️ <b>Agenda</b> indisponible.")
            unknown = True

    try:
        due = deadlines.deadlines_between(start, end)
        if due:
            n_deadlines = len(due)
            sections.append("\n".join(
                [WEEKLY_DEADLINES_HEADER]
                + [f"• {utils.format_short_date(d)} : {utils.escape(t)}" for d, t in due]
            ))
    except Exception as exc:
        print(f"[warn] weekly deadlines failed: {type(exc).__name__}", file=sys.stderr)
        sections.append("⚠️ <b>Échéances</b> indisponibles.")
        unknown = True

    if n_events or n_deadlines or unknown:  # never claim a free week on errors
        sections.append(
            f"{utils.plural(n_events, 'événement')}, {utils.plural(n_deadlines, 'échéance')}."
        )
    else:
        sections.append("Semaine libre. 🎉")
    return sections
