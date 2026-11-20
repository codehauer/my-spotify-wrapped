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

from .enrich import apply_genres
from .genres import ArtistGenre, BY_NAME
from .loader import normalize, parse_records

_ADJECTIVES = ["Velvet", "Neon", "Paper", "Silver", "Midnight", "Golden", "Hollow", "Electric",
               "Quiet", "Wild", "Crystal", "Lunar", "Static", "Copper", "Glass", "Northern"]
_NOUNS = ["Harbor", "Foxes", "Satellites", "Gardens", "Echoes", "Tigers", "Lanterns", "Waves",
          "Pilots", "Rivers", "Ghosts", "Horizons", "Owls", "Machines", "Parade", "Comets"]
_WORDS = ["Summer", "Light", "Heart", "Road", "Dream", "Fire", "Night", "Rain", "Home", "Gold",
          "Stars", "Ocean", "Signal", "Shadow", "Bloom", "City", "Motion", "Echo", "Sky", "Youth"]
# Relative listening intensity per hour of the day (evening heavy).
_HOUR_WEIGHTS = [2, 1, 1, 0.5, 0.5, 1, 3, 6, 8, 7, 6, 6, 7, 6, 6, 7, 8, 10, 12, 13, 12, 10, 7, 4]
# Demo genres: (genre, how many artists, the hours it is played most).
_DEMO_GENRES = [
    ("Pop", 26, range(10, 20)),
    ("Hip-Hop & Rap", 20, range(16, 24)),
    ("Electronic & Dance", 16, [21, 22, 23, 0, 1, 2, 3, 4]),
    ("Indie & Alternative", 16, range(7, 13)),
    ("Rock", 12, range(12, 19)),
    ("R&B & Soul", 10, range(19, 24)),
    ("Folk & Singer-Songwriter", 8, range(5, 10)),
    ("Classical & Soundtrack", 6, range(6, 10)),
    ("Schlager & Party", 4, [20, 21, 22, 23, 0]),
    ("Jazz & Blues", 2, range(8, 11)),
]


def demo_genres(seed: int = 7) -> dict[str, ArtistGenre]:
    """The (fictional) genre of every demo artist."""
    rng = random.Random(seed)
    artists = rng.sample([f"{a} {n}" for a in _ADJECTIVES for n in _NOUNS], 120)
    genres = random.Random(seed + 1).sample([g for g, count, _ in _DEMO_GENRES for _ in range(count)], len(artists))
    profiles = {}
    jitter = random.Random(seed + 2)
    for artist, name in zip(artists, genres):
        genre = BY_NAME[name]
        valence = min(max(genre.valence + jitter.uniform(-0.15, 0.15), 0.0), 1.0)
        profiles[artist] = ArtistGenre(name, round(valence, 3), genre.energy)
    return profiles


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
    # Genres follow the time of day (more techno at night, more folk in the morning).
    genre_of = {a: g.genre for a, g in demo_genres(seed).items()}
    peak_hours = {g: set(hours) for g, _, hours in _DEMO_GENRES}
    hour_weights = [
        [w * (4.0 if hour in peak_hours.get(genre_of.get(a, ""), ()) else 1.0) for w, (a, *_) in zip(weights, catalog)]
        for hour in range(24)
    ]

    records: list[dict[str, Any]] = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        if rng.random() < 0.12:  # some days without music
            continue
        weekend = day.weekday() >= 5
        for _ in range(int(rng.gauss(38 if weekend else 28, 10)) if rng.random() > 0.03 else int(rng.gauss(95, 20))):
            hour = rng.choices(range(24), _HOUR_WEIGHTS)[0]
            played_at = day.replace(hour=hour, minute=rng.randint(0, 59), second=rng.randint(0, 59))
            artist, track, album, length = rng.choices(catalog, hour_weights[hour])[0]
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


def demo_streams(timezone_name: str | None = "UTC", with_genres: bool = True) -> pd.DataFrame:
    """Return the demo history as a normalized streams frame (with genre columns by default)."""
    frame = parse_records(generate_records())
    assert frame is not None
    frame = normalize(frame, timezone_name)
    return apply_genres(frame, demo_genres()) if with_genres else frame
