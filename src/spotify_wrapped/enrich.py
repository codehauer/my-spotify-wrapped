"""Adds genre and mood columns to the streams frame.

The Spotify export has no genre information, so genres are looked up per
artist. Two sources are supported:

* ``"musicbrainz"``: the free MusicBrainz web service (no account needed).
  Only artist names are sent; results are cached on disk, so every artist is
  looked up once. MusicBrainz allows one request per second, so the first run
  takes a few minutes; only the ``limit`` most played artists are looked up.
* a JSON file mapping artist names to a genre name or a list of tags, e.g.
  ``{"Some Artist": "Hip-Hop & Rap", "Other Artist": ["dream pop", "sad"]}``.

:func:`apply_genres` adds the columns ``genre`` (one of
:data:`spotify_wrapped.genres.GENRES` or missing), ``valence`` and ``energy``.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from .genres import ArtistGenre, profile_from_tags

MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2/artist/"
USER_AGENT = "my-spotify-wrapped/0.3 (personal listening statistics)"
DEFAULT_ARTIST_LIMIT = 250

Tags = list[tuple[str, int]]
Fetcher = Callable[[str], Tags | None]


def cache_path() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "spotify-wrapped" / "musicbrainz-artists.json"


def apply_genres(frame: pd.DataFrame, genres: Mapping[str, ArtistGenre | None]) -> pd.DataFrame:
    """Return ``frame`` with ``genre``, ``valence`` and ``energy`` columns."""
    def column(attribute: str) -> pd.Series:
        values = {a: getattr(g, attribute) for a, g in genres.items() if g is not None}
        return frame["artist"].map(values)

    return frame.assign(genre=column("genre"), valence=column("valence").astype("float64"),
                        energy=column("energy").astype("float64"))


def top_artists(frame: pd.DataFrame, limit: int) -> list[str]:
    """The ``limit`` artists with the most listening time."""
    totals = frame.groupby("artist")["ms_played"].sum().sort_values(ascending=False, kind="stable")
    return [str(a) for a in totals.index[:limit]]


def genres_from_file(path: str | Path) -> dict[str, ArtistGenre | None]:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"'{path}' must contain a JSON object mapping artist names to genres or tags")
    result: dict[str, ArtistGenre | None] = {}
    for artist, value in data.items():
        tags = [value] if isinstance(value, str) else [str(v) for v in value or []]
        result[str(artist)] = profile_from_tags(tags)
    return result


# --------------------------------------------------------------------------- #
# MusicBrainz
# --------------------------------------------------------------------------- #

_LUCENE_SPECIAL = re.compile(r'([+\-&|!(){}\[\]^"~*?:\\/])')


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def musicbrainz_tags(artist: str, fetch_json: Callable[[str], Any] = _fetch_json) -> Tags | None:
    """Look up the community tags of ``artist``; ``None`` if no confident match exists."""
    escaped = _LUCENE_SPECIAL.sub(r"\\\1", artist)
    query = f'artist:"{escaped}"'
    url = f"{MUSICBRAINZ_URL}?{urllib.parse.urlencode({'query': query, 'fmt': 'json', 'limit': 5})}"
    candidates = fetch_json(url).get("artists", [])
    wanted = artist.casefold()
    exact = [c for c in candidates
             if wanted in {str(c.get("name", "")).casefold(), str(c.get("sort-name", "")).casefold()}]
    pool = exact or [c for c in candidates if int(c.get("score", 0)) >= 98]
    # Several exact matches (namesakes): the one with the most tags is usually the famous one.
    pool.sort(key=lambda c: -sum(int(t.get("count", 0)) for t in c.get("tags", [])))
    for candidate in pool:
        tags = [(str(t["name"]), int(t.get("count", 1))) for t in candidate.get("tags", []) if t.get("name")]
        if tags:
            return tags
    return None


class MusicBrainzLookup:
    """Rate limited, cached MusicBrainz tag lookups."""

    def __init__(self, cache_file: Path | None = None, fetch: Fetcher | None = None,
                 delay: float = 1.1, log: Callable[[str], None] | None = None) -> None:
        self.cache_file = cache_file or cache_path()
        self.fetch: Fetcher = fetch or musicbrainz_tags
        self.delay = delay
        self.log = log or (lambda message: print(message, file=sys.stderr))
        self.cache: dict[str, Tags | None] = {}
        if self.cache_file.is_file():
            try:
                raw = json.loads(self.cache_file.read_text(encoding="utf-8"))
                self.cache = {a: [tuple(t) for t in tags] if tags is not None else None  # type: ignore[misc]
                              for a, tags in raw.items()}
            except (json.JSONDecodeError, OSError, TypeError, ValueError):
                self.cache = {}

    def save(self) -> None:
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")

    def lookup(self, artists: list[str]) -> dict[str, ArtistGenre | None]:
        missing = [a for a in artists if a not in self.cache]
        if missing:
            self.log(f"Looking up genres of {len(missing)} artists on MusicBrainz "
                     f"(about {round(len(missing) * self.delay / 60) or 1} min, cached in {self.cache_file}) ...")
        failures = 0
        try:
            for index, artist in enumerate(missing, start=1):
                if index > 1:
                    time.sleep(self.delay)
                try:
                    self.cache[artist] = self.fetch(artist)
                    failures = 0
                except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
                    failures += 1
                    if failures >= 3:
                        self.log(f"MusicBrainz is not reachable ({error}); continuing with the genres found so far.")
                        break
                if index % 25 == 0:
                    self.log(f"  {index}/{len(missing)} artists")
                    self.save()
        except KeyboardInterrupt:
            self.log("Genre lookup interrupted; continuing with the genres found so far.")
        finally:
            if missing:
                self.save()
        return {a: profile_from_tags(self.cache[a] or []) for a in artists if a in self.cache}


def add_genres(frame: pd.DataFrame, source: str, *, limit: int = DEFAULT_ARTIST_LIMIT,
               lookup: MusicBrainzLookup | None = None) -> pd.DataFrame:
    """Add genre columns using ``source`` (``"musicbrainz"`` or a JSON file path)."""
    if source == "musicbrainz":
        genres = (lookup or MusicBrainzLookup()).lookup(top_artists(frame, limit))
    else:
        genres = genres_from_file(source)
    return apply_genres(frame, genres)
