"""Loading of Spotify data exports.

Spotify hands out two different exports, both of which are supported:

* **Account data** (``StreamingHistory0.json``, ``StreamingHistory_music_0.json``):
  ``{"endTime": "2022-01-01 12:34", "artistName": ..., "trackName": ..., "msPlayed": ...}``
* **Extended streaming history** (``Streaming_History_Audio_2021_0.json``):
  ``{"ts": "2021-01-01T12:34:56Z", "ms_played": ...,
  "master_metadata_track_name": ..., "master_metadata_album_artist_name": ..., ...}``

Every record is normalized into one :class:`pandas.DataFrame` with the columns
listed in :data:`COLUMNS`. Podcast episodes and other non-music entries are dropped.
Other JSON files of the export (``Userdata.json``, ``Playlist1.json``, ...) are ignored.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
from dateutil import tz

COLUMNS = ["played_at", "artist", "track", "album", "ms_played"]
"""Columns of the normalized streams frame.

``played_at`` is a timezone-aware timestamp of when the stream *ended*.
"""


class NoStreamingHistoryError(ValueError):
    """Raised when no streaming history could be found at the given location."""


def _classify(records: list[Any]) -> str | None:
    """Return the export format of a parsed JSON file or ``None`` if unknown."""
    if not records or not isinstance(records, list) or not isinstance(records[0], dict):
        return None
    sample = records[0]
    if "ts" in sample and "ms_played" in sample:
        return "extended"
    if "endTime" in sample and "msPlayed" in sample and "artistName" in sample:
        return "account"
    return None


def _normalize_account(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame.from_records(records)
    return pd.DataFrame(
        {
            # Account data timestamps are UTC without a marker.
            "played_at": pd.to_datetime(frame["endTime"], utc=True, format="mixed"),
            "artist": frame["artistName"],
            "track": frame["trackName"],
            "album": None,
            "ms_played": frame["msPlayed"],
        }
    )


def _normalize_extended(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame.from_records(records)

    def get(column: str) -> pd.Series | None:
        return frame[column] if column in frame else None

    return pd.DataFrame(
        {
            "played_at": pd.to_datetime(frame["ts"], utc=True, format="mixed"),
            "artist": get("master_metadata_album_artist_name"),
            "track": get("master_metadata_track_name"),
            "album": get("master_metadata_album_album_name"),
            "ms_played": frame["ms_played"],
        }
    )


def parse_records(records: Any) -> pd.DataFrame | None:
    """Parse the content of one export file; returns ``None`` for unrelated files."""
    kind = _classify(records)
    if kind == "account":
        return _normalize_account(records)
    if kind == "extended":
        return _normalize_extended(records)
    return None


def _json_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    yield from sorted(p for p in path.rglob("*.json") if p.is_file())


def load_streams(path: str | Path, timezone: str | tzinfo | None = None) -> pd.DataFrame:
    """Load every streaming history file at ``path`` (a file or a directory).

    Directories are searched recursively, so the unpacked Spotify archive can be
    passed directly. ``timezone`` controls in which timezone hours and days are
    evaluated; it defaults to the timezone of this computer.
    """
    path = Path(path).expanduser()
    if not path.exists():
        raise NoStreamingHistoryError(f"'{path}' does not exist")

    frames: list[pd.DataFrame] = []
    for file in _json_files(path):
        try:
            records = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        parsed = parse_records(records)
        if parsed is not None:
            frames.append(parsed)

    if not frames:
        raise NoStreamingHistoryError(
            f"No Spotify streaming history found in '{path}'. Expected files like "
            "'StreamingHistory0.json' or 'Streaming_History_Audio_*.json'."
        )

    return normalize(pd.concat(frames, ignore_index=True), timezone)


def normalize(frame: pd.DataFrame, timezone: str | tzinfo | None = None) -> pd.DataFrame:
    """Clean a frame with :data:`COLUMNS` (drop podcasts, duplicates, sort, convert tz)."""
    frame = frame.dropna(subset=["artist", "track"])
    frame = frame[frame["ms_played"] > 0]
    # The same stream can appear in overlapping exports.
    frame = frame.drop_duplicates(subset=["played_at", "artist", "track"])

    if timezone is None:
        target: str | tzinfo = tz.tzlocal()
    elif isinstance(timezone, str):
        try:
            target = ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError(f"Unknown timezone '{timezone}'") from error
    else:
        target = timezone
    frame = frame.assign(
        played_at=frame["played_at"].dt.tz_convert(target),
        ms_played=frame["ms_played"].astype("int64"),
        artist=frame["artist"].astype(str),
        track=frame["track"].astype(str),
    )
    return frame.sort_values("played_at").reset_index(drop=True)[COLUMNS]
