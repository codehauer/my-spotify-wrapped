"""Generates a realistic, entirely fictional streaming history.

Used by the ``--demo`` flag and the tests, so the UIs can be tried without an
actual Spotify export.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .loader import normalize, parse_records

_ADJECTIVES = ["Velvet", "Neon", "Paper", "Silver", "Midnight", "Golden", "Hollow", "Electric",
               "Quiet", "Wild", "Crystal", "Lunar", "Static", "Copper", "Glass", "Northern"]
_NOUNS = ["Harbor", "Foxes", "Satellites", "Gardens", "Echoes", "Tigers", "Lanterns", "Waves",
          "Pilots", "Rivers", "Ghosts", "Horizons", "Owls", "Machines", "Parade", "Comets"]
_WORDS = ["Summer", "Light", "Heart", "Road", "Dream", "Fire", "Night", "Rain", "Home", "Gold",
          "Stars", "Ocean", "Signal", "Shadow", "Bloom", "City", "Motion", "Echo", "Sky", "Youth"]
# Relative listening intensity per hour of the day (evening heavy).
_HOUR_WEIGHTS = [2, 1, 1, 0.5, 0.5, 1, 3, 6, 8, 7, 6, 6, 7, 6, 6, 7, 8, 10, 12, 13, 12, 10, 7, 4]


def generate_records(*, days: int = 540, seed: int = 7, end: datetime | None = None,
                     extended: bool = True) -> list[dict[str, Any]]:
    """Return raw export records in the extended (default) or account data format."""
    rng = random.Random(seed)
    end = end or datetime(2025, 12, 31, 23, 0, tzinfo=timezone.utc)
    start = end - timedelta(days=days)

    artist_names = rng.sample([f"{a} {n}" for a in _ADJECTIVES for n in _NOUNS], 120)
    catalog = []
    for artist in artist_names:
        albums = [" ".join(rng.sample(_WORDS, 2)) for _ in range(rng.randint(1, 3))]
        for _ in range(rng.randint(4, 14)):
            title = " ".join(rng.sample(_WORDS, rng.randint(1, 3)))
            catalog.append((artist, title, rng.choice(albums), rng.randint(120_000, 330_000)))
    # Zipf-like popularity: a few favourites, a long tail.
    artist_weight = {a: 1 / (i + 1) ** 1.1 for i, a in enumerate(artist_names)}
    weights = [artist_weight[a] * rng.uniform(0.2, 1.0) for a, *_ in catalog]

    records: list[dict[str, Any]] = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        if rng.random() < 0.12:  # some days without music
            continue
        weekend = day.weekday() >= 5
        for _ in range(int(rng.gauss(38 if weekend else 28, 10)) if rng.random() > 0.03 else int(rng.gauss(95, 20))):
            hour = rng.choices(range(24), _HOUR_WEIGHTS)[0]
            played_at = day.replace(hour=hour, minute=rng.randint(0, 59), second=rng.randint(0, 59))
            artist, track, album, length = rng.choices(catalog, weights)[0]
            ms = length if rng.random() < 0.7 else rng.randint(1_000, length)
            if extended:
                records.append({
                    "ts": played_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "platform": "android",
                    "ms_played": ms,
                    "master_metadata_track_name": track,
                    "master_metadata_album_artist_name": artist,
                    "master_metadata_album_album_name": album,
                    "skipped": ms < length,
                })
            else:
                records.append({
                    "endTime": played_at.strftime("%Y-%m-%d %H:%M"),
                    "artistName": artist, "trackName": track, "msPlayed": ms,
                })
    # A podcast episode, which must be ignored by the loader.
    if extended:
        records.append({"ts": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "ms_played": 1_800_000,
                        "master_metadata_track_name": None, "master_metadata_album_artist_name": None,
                        "episode_name": "A fictional podcast"})
    return records


def write_sample_export(directory: str | Path, **kwargs: Any) -> Path:
    """Write a fake export to ``directory`` and return the directory."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    name = "Streaming_History_Audio_demo_0.json" if kwargs.get("extended", True) else "StreamingHistory0.json"
    (directory / name).write_text(json.dumps(generate_records(**kwargs)), encoding="utf-8")
    return directory


def demo_streams(timezone_name: str | None = "UTC") -> pd.DataFrame:
    """Return the demo history as a normalized streams frame."""
    frame = parse_records(generate_records())
    assert frame is not None
    return normalize(frame, timezone_name)
