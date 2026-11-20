"""The statistics engine shared by every user interface.

All number crunching happens here. :func:`build_report` turns the normalized
streams frame from :mod:`spotify_wrapped.loader` into a :class:`Report`: plain,
JSON-serializable dataclasses that the TUI renders directly and the web UI
receives as JSON (see ``web/src/types.ts`` for the TypeScript mirror).

A report contains one :class:`WrappedStatistics` view for the whole history
(key ``"all"``) and one per calendar year (keys like ``"2024"``).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .formatting import format_duration, format_number, plural

SCHEMA_VERSION = 1
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ALL_TIME = "all"


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RankedItem:
    """One row of a ranking (an artist, track or album)."""

    rank: int
    name: str
    streams: int
    minutes: float
    share: float
    """Share (in percent) of all streams, or of all minutes for time based rankings."""
    artist: str | None = None
    """The artist of a track or album; ``None`` for artist rankings."""


@dataclass(frozen=True)
class DayStat:
    date: str
    """ISO date, e.g. ``"2024-03-01"``."""
    streams: int
    minutes: float
    top_artist: str | None = None


@dataclass(frozen=True)
class Bucket:
    """Aggregate for a bucket of a cyclic or calendar dimension (hour, weekday, month)."""

    key: int | str
    label: str
    streams: int
    minutes: float


@dataclass(frozen=True)
class HeatCell:
    weekday: int
    """0 = Monday ... 6 = Sunday."""
    hour: int
    streams: int


@dataclass(frozen=True)
class Stream:
    track: str
    artist: str
    minutes: float
    played_at: str


@dataclass(frozen=True)
class Highlight:
    """A short, human readable fact. Both UIs show these verbatim."""

    icon: str
    title: str
    value: str
    detail: str


@dataclass(frozen=True)
class Overview:
    total_streams: int
    total_minutes: float
    unique_artists: int
    unique_tracks: int
    unique_albums: int | None
    active_days: int
    days_in_period: int
    active_day_share: float
    average_stream_minutes: float
    average_minutes_per_active_day: float
    streams_per_artist: float
    streams_per_track: float
    top_artists_share: float
    """Percentage of streams going to the top-N artists."""
    one_off_artists: int
    """Artists that were only played a single time."""
    longest_streak: int
    longest_streak_start: str | None
    longest_streak_end: str | None
    longest_stream: Stream | None
    first_stream: str
    last_stream: str
    peak_hour: int
    peak_weekday: int


@dataclass(frozen=True)
class WrappedStatistics:
    key: str
    label: str
    year: int | None
    period_start: str
    period_end: str
    overview: Overview
    highlights: list[Highlight]
    top_artists: list[RankedItem]
    top_artists_by_time: list[RankedItem]
    least_streamed_artists: list[RankedItem]
    top_tracks: list[RankedItem]
    top_tracks_by_time: list[RankedItem]
    top_albums: list[RankedItem]
    top_days: list[DayStat]
    daily: list[DayStat]
    weekly: list[Bucket]
    """Weeks starting on Monday; ``key`` is the ISO date of the Monday."""
    monthly: list[Bucket]
    weekdays: list[Bucket]
    hours: list[Bucket]
    heatmap: list[HeatCell]


@dataclass
class Report:
    generated_at: str
    timezone: str
    top_n: int
    years: list[int]
    default_view: str
    views: dict[str, WrappedStatistics] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def view(self, key: str | int | None = None) -> WrappedStatistics:
        """Return the view for a year (or ``"all"``); defaults to :attr:`default_view`."""
        return self.views[str(key) if key is not None else self.default_view]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# --------------------------------------------------------------------------- #
# Computation
# --------------------------------------------------------------------------- #


def _minutes(ms: float) -> float:
    return round(float(ms) / 60_000, 1)


def _pct(part: float, whole: float) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def _ranking(grouped: pd.DataFrame, by: str, total: float, top_n: int, ascending: bool = False,
             with_artist: bool = False) -> list[RankedItem]:
    """Build a ranking from a frame indexed by name with ``streams``/``ms`` columns."""
    other = "ms" if by == "streams" else "streams"
    ordered = grouped.reset_index().sort_values(
        [by, other, "name"], ascending=[ascending, ascending, True]
    ).head(top_n)
    return [
        RankedItem(
            rank=rank,
            name=str(row.name),
            artist=str(row.artist) if with_artist else None,
            streams=int(row.streams),
            minutes=_minutes(row.ms),
            share=_pct(getattr(row, by), total),
        )
        for rank, row in enumerate(ordered.itertuples(index=False), start=1)
    ]


def _aggregate(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    return frame.groupby(keys, sort=False).agg(streams=("ms_played", "size"), ms=("ms_played", "sum"))


def _longest_streak(dates: pd.Series) -> tuple[int, str | None, str | None]:
    days = pd.Series(sorted(set(dates)))
    if days.empty:
        return 0, None, None
    ordinals = days.map(lambda d: d.toordinal())
    # Consecutive days share the same (ordinal - position) value.
    run_id = ordinals - pd.RangeIndex(len(ordinals))
    runs = days.groupby(run_id.values).agg(["first", "last", "size"])
    best = runs.sort_values(["size", "first"], ascending=[False, True]).iloc[0]
    return int(best["size"]), best["first"].isoformat(), best["last"].isoformat()


def _personality(peak_hour: int) -> tuple[str, str, str]:
    if 5 <= peak_hour < 11:
        return "🌅", "Early Bird", "Most of your music happens in the morning."
    if 11 <= peak_hour < 17:
        return "🌞", "Daytime Groover", "You keep the music going through the day."
    if 17 <= peak_hour < 22:
        return "🌆", "Evening Unwinder", "Evenings are when you press play the most."
    return "🦉", "Night Owl", "Your headphones come alive after dark."


def _highlights(ov: Overview, top_artists: list[RankedItem], top_tracks: list[RankedItem],
                top_days: list[DayStat], top_n: int) -> list[Highlight]:
    items: list[Highlight] = []
    if top_artists:
        a = top_artists[0]
        items.append(Highlight(
            "🎤", "Top artist", a.name,
            f"{plural(a.streams, 'stream')} · {format_duration(a.minutes)} · {a.share}% of everything"))
    if top_tracks:
        t = top_tracks[0]
        items.append(Highlight(
            "🎵", "Top track", t.name,
            f"by {t.artist} · played {plural(t.streams, 'time')}"))
    icon, persona, why = _personality(ov.peak_hour)
    items.append(Highlight(
        icon, "Listening personality", persona,
        f"{why} Peak hour: {ov.peak_hour:02d}:00, favourite day: {WEEKDAYS[ov.peak_weekday]}."))
    if ov.longest_streak:
        items.append(Highlight(
            "🔥", "Longest streak", plural(ov.longest_streak, "day"),
            f"Music every single day from {ov.longest_streak_start} to {ov.longest_streak_end}."))
    if top_days:
        d = top_days[0]
        items.append(Highlight(
            "📅", "Biggest day", datetime.fromisoformat(d.date).strftime("%A, %d %B %Y"),
            f"{plural(d.streams, 'stream')} and {format_duration(d.minutes)} of music"
            + (f", mostly {d.top_artist}." if d.top_artist else ".")))
    items.append(Highlight(
        "🧭", "Explorer score", f"{format_number(ov.unique_artists)} artists",
        f"Your top {top_n} artists cover {ov.top_artists_share}% of your streams"
        + (f"; {plural(ov.one_off_artists, 'artist')} got just a single play." if ov.one_off_artists else ".")))
    if ov.longest_stream:
        s = ov.longest_stream
        items.append(Highlight(
            "⌛", "Longest session", format_duration(s.minutes),
            f"Your longest single stream: {s.track} by {s.artist}."))
    return items


def compute_statistics(frame: pd.DataFrame, *, top_n: int = 10, key: str = ALL_TIME,
                       label: str = "All time", year: int | None = None) -> WrappedStatistics:
    """Compute every statistic for the given (already filtered) streams frame."""
    if frame.empty:
        raise ValueError("Cannot compute statistics without any streams")

    frame = frame.assign(
        date=frame["played_at"].dt.date,
        hour=frame["played_at"].dt.hour,
        weekday=frame["played_at"].dt.weekday,
        month=frame["played_at"].dt.strftime("%Y-%m"),
    )
    total_streams = len(frame)
    total_ms = float(frame["ms_played"].sum())
    total_minutes = _minutes(total_ms)

    # Rankings ------------------------------------------------------------
    artists = _aggregate(frame, ["artist"]).rename_axis("name")
    tracks = _aggregate(frame, ["track", "artist"]).reset_index().rename(columns={"track": "name"})
    tracks = tracks.set_index("name")

    top_artists = _ranking(artists, "streams", total_streams, top_n)
    top_artists_by_time = _ranking(artists, "ms", total_ms, top_n)
    least_streamed = _ranking(artists, "streams", total_streams, top_n, ascending=True)
    top_tracks = _ranking(tracks, "streams", total_streams, top_n, with_artist=True)
    top_tracks_by_time = _ranking(tracks, "ms", total_ms, top_n, with_artist=True)

    albums_frame = frame.dropna(subset=["album"])
    top_albums: list[RankedItem] = []
    if not albums_frame.empty:
        albums = _aggregate(albums_frame, ["album", "artist"]).reset_index()
        albums = albums.rename(columns={"album": "name"}).set_index("name")
        top_albums = _ranking(albums, "streams", total_streams, top_n, with_artist=True)

    # Time series ---------------------------------------------------------
    per_day = _aggregate(frame, ["date"]).sort_index()
    day_top_artist = (
        frame.groupby(["date", "artist"]).size().reset_index(name="n")
        .sort_values(["date", "n", "artist"], ascending=[True, False, True])
        .drop_duplicates("date").set_index("date")["artist"]
    )
    start, end = frame["date"].min(), frame["date"].max()
    calendar = pd.date_range(start, end, freq="D").date
    per_day_full = per_day.reindex(calendar, fill_value=0)
    daily = [
        DayStat(day.isoformat(), int(row.streams), _minutes(row.ms),
                day_top_artist.get(day) if row.streams else None)
        for day, row in per_day_full.iterrows()
    ]
    top_days = sorted((d for d in daily if d.streams), key=lambda d: (-d.streams, -d.minutes, d.date))[:top_n]

    weeks = per_day_full.groupby(
        [day - pd.Timedelta(days=day.weekday()) for day in per_day_full.index]).sum()
    weekly = [
        Bucket(monday.isoformat(), f"Week of {monday.strftime('%d %b %Y')}", int(row.streams), _minutes(row.ms))
        for monday, row in weeks.iterrows()
    ]

    per_month = _aggregate(frame, ["month"]).sort_index()
    monthly = [
        Bucket(month, f"{MONTHS[int(month[5:]) - 1]} {month[:4]}", int(row.streams), _minutes(row.ms))
        for month, row in per_month.iterrows()
    ]
    per_weekday = _aggregate(frame, ["weekday"]).reindex(range(7), fill_value=0)
    weekdays = [Bucket(i, WEEKDAYS[i], int(r.streams), _minutes(r.ms)) for i, r in per_weekday.iterrows()]
    per_hour = _aggregate(frame, ["hour"]).reindex(range(24), fill_value=0)
    hours = [Bucket(h, f"{h:02d}:00", int(r.streams), _minutes(r.ms)) for h, r in per_hour.iterrows()]
    heat = frame.groupby(["weekday", "hour"]).size()
    heatmap = [HeatCell(w, h, int(heat.get((w, h), 0))) for w in range(7) for h in range(24)]

    # Overview ------------------------------------------------------------
    streak, streak_start, streak_end = _longest_streak(frame["date"])
    longest = frame.loc[frame["ms_played"].idxmax()]
    active_days = int(per_day["streams"].gt(0).sum())
    days_in_period = len(calendar)
    if year is not None:
        # A year view covers the whole year, unless the export ends/starts within it.
        days_in_period = len(pd.date_range(max(pd.Timestamp(year, 1, 1).date(), start),
                                           min(pd.Timestamp(year, 12, 31).date(), end)))
    overview = Overview(
        total_streams=total_streams,
        total_minutes=total_minutes,
        unique_artists=len(artists),
        unique_tracks=len(tracks),
        unique_albums=int(albums_frame.groupby(["album", "artist"]).ngroups) if not albums_frame.empty else None,
        active_days=active_days,
        days_in_period=days_in_period,
        active_day_share=_pct(active_days, days_in_period),
        average_stream_minutes=round(total_ms / total_streams / 60_000, 2),
        average_minutes_per_active_day=_minutes(total_ms / active_days),
        streams_per_artist=round(total_streams / len(artists), 1),
        streams_per_track=round(total_streams / len(tracks), 1),
        top_artists_share=round(sum(a.share for a in top_artists), 1),
        one_off_artists=int(artists["streams"].eq(1).sum()),
        longest_streak=streak,
        longest_streak_start=streak_start,
        longest_streak_end=streak_end,
        longest_stream=Stream(str(longest["track"]), str(longest["artist"]),
                              _minutes(longest["ms_played"]), longest["played_at"].isoformat()),
        first_stream=frame["played_at"].iloc[0].isoformat(),
        last_stream=frame["played_at"].iloc[-1].isoformat(),
        peak_hour=int(per_hour["streams"].idxmax()),
        peak_weekday=int(per_weekday["streams"].idxmax()),
    )

    return WrappedStatistics(
        key=key, label=label, year=year,
        period_start=start.isoformat(), period_end=end.isoformat(),
        overview=overview,
        highlights=_highlights(overview, top_artists, top_tracks, top_days, top_n),
        top_artists=top_artists, top_artists_by_time=top_artists_by_time,
        least_streamed_artists=least_streamed,
        top_tracks=top_tracks, top_tracks_by_time=top_tracks_by_time, top_albums=top_albums,
        top_days=top_days, daily=daily, weekly=weekly, monthly=monthly, weekdays=weekdays, hours=hours,
        heatmap=heatmap,
    )


def build_report(frame: pd.DataFrame, *, top_n: int = 10, year: int | None = None) -> Report:
    """Build the full report: an all-time view plus one view per year.

    If ``year`` is given, that year becomes the default view.
    """
    if frame.empty:
        raise ValueError("Cannot build a report without any streams")
    years = sorted(int(y) for y in frame["played_at"].dt.year.unique())
    if year is not None and year not in years:
        raise ValueError(f"No streams in {year}. Available years: {', '.join(map(str, years))}")

    views = {ALL_TIME: compute_statistics(frame, top_n=top_n)}
    for y in years:
        subset = frame[frame["played_at"].dt.year == y]
        views[str(y)] = compute_statistics(subset, top_n=top_n, key=str(y), label=str(y), year=y)

    tzinfo = frame["played_at"].dt.tz
    return Report(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        timezone=str(getattr(tzinfo, "key", None) or frame["played_at"].iloc[-1].tzname() or "UTC"),
        top_n=top_n,
        years=years,
        default_view=str(year) if year is not None else ALL_TIME,
        views=views,
    )
