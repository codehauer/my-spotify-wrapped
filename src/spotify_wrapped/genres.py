"""Genre taxonomy, mood and "holy trinity" profiles.

The Spotify export contains no genres and no audio features. Genres are looked
up per artist (see :mod:`spotify_wrapped.enrich`) as free-form tags, e.g.
``"german hip hop"`` or ``"dream pop"``. This module folds those tags into a
small set of :data:`GENRES` and attaches a rough profile to each of them:

* ``valence`` (0 = sad, 1 = happy) and ``energy`` (0 = calm, 1 = intense),
  typical values for the genre in the spirit of Spotify's audio features;
* how *atzig*, *fotzig* and *mausig* the genre is (0–1 each), the German meme
  trinity (https://atzigfotzigmausig.de/):

  - **atzig**: like an "Atze": loud, rowdy party energy. Techno, Schlager,
    Ballermann, Metal, anything you'd hear at 3 am at a rave or a beer tent.
  - **fotzig**: sassy, bitchy, self-confident diva or gangster attitude.
    Rap, Trap, R&B, Reggaeton, diva pop.
  - **mausig**: cute, soft, cosy and a bit dreamy. Indie, singer-songwriter,
    acoustic, classical, lo-fi.

All of this is a heuristic: it describes genres, not individual songs.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

OTHER = "Other"


@dataclass(frozen=True)
class Genre:
    name: str
    keywords: tuple[str, ...]
    valence: float
    energy: float
    atzig: float
    fotzig: float
    mausig: float


GENRES: tuple[Genre, ...] = (
    Genre("Pop", ("pop", "dance pop", "synth pop", "synthpop", "electropop", "k pop", "j pop", "teen pop",
                  "europop", "boy band", "girl group", "deutschpop", "schlagerpop", "latin pop"),
          0.72, 0.65, 0.35, 0.6, 0.55),
    Genre("Hip-Hop & Rap", ("hip hop", "rap", "trap", "drill", "grime", "boom bap", "deutschrap", "cloud rap",
                            "gangsta rap", "german hip hop", "conscious hip hop"),
          0.5, 0.75, 0.55, 0.9, 0.1),
    Genre("Electronic & Dance", ("electronic", "electronica", "electro", "techno", "house", "deep house",
                                 "tech house", "trance", "edm", "dance", "drum and bass", "dnb", "dubstep",
                                 "hardstyle", "hardcore techno", "rave", "eurodance", "gabber", "schranz",
                                 "breakbeat", "uk garage", "big room", "electro house", "synthwave"),
          0.62, 0.88, 0.9, 0.35, 0.1),
    Genre("Rock", ("rock", "classic rock", "hard rock", "grunge", "britpop", "garage rock", "krautrock",
                   "deutschrock", "psychedelic rock", "blues rock", "stoner rock"),
          0.52, 0.75, 0.6, 0.35, 0.25),
    Genre("Indie & Alternative", ("indie", "alternative", "indie pop", "indie rock", "shoegaze", "dream pop",
                                  "bedroom pop", "lo fi", "lofi", "post rock", "post punk", "new wave",
                                  "art pop", "chamber pop", "slowcore", "indietronica"),
          0.45, 0.5, 0.2, 0.3, 0.8),
    Genre("R&B & Soul", ("r&b", "rnb", "rhythm and blues", "soul", "neo soul", "funk", "motown", "disco",
                         "contemporary r&b", "alternative r&b"),
          0.65, 0.55, 0.2, 0.75, 0.45),
    Genre("Latin & Reggae", ("latin", "reggaeton", "reggae", "dancehall", "afrobeats", "afrobeat", "salsa",
                             "bachata", "cumbia", "dembow", "moombahton", "latin trap", "urbano latino"),
          0.8, 0.78, 0.6, 0.75, 0.25),
    Genre("Schlager & Party", ("schlager", "partyschlager", "ballermann", "volksmusik", "apres ski",
                               "après ski", "oktoberfest", "stimmungsmusik", "malle", "party"),
          0.85, 0.8, 1.0, 0.2, 0.25),
    Genre("Metal", ("metal", "heavy metal", "metalcore", "deathcore", "thrash metal", "death metal",
                    "black metal", "doom metal", "power metal", "nu metal", "djent"),
          0.3, 0.95, 0.85, 0.4, 0.05),
    Genre("Punk & Emo", ("punk", "pop punk", "punk rock", "emo", "post hardcore", "hardcore", "ska",
                         "skate punk", "deutschpunk", "midwest emo"),
          0.42, 0.85, 0.7, 0.5, 0.2),
    Genre("Folk & Singer-Songwriter", ("folk", "singer songwriter", "acoustic", "country", "americana",
                                       "bluegrass", "chanson", "liedermacher", "indie folk", "folk pop"),
          0.45, 0.3, 0.1, 0.15, 0.9),
    Genre("Jazz & Blues", ("jazz", "blues", "swing", "bossa nova", "bebop", "lounge", "smooth jazz",
                           "vocal jazz", "big band"),
          0.55, 0.35, 0.1, 0.45, 0.6),
    Genre("Classical & Soundtrack", ("classical", "orchestral", "opera", "baroque", "romantic era",
                                     "soundtrack", "score", "film score", "video game music", "ambient",
                                     "neoclassical", "modern classical", "piano", "new age", "musical"),
          0.4, 0.2, 0.05, 0.1, 0.85),
)

BY_NAME = {g.name: g for g in GENRES}

# Mood tags shift an artist's valence away from its genre default.
_HAPPY_TAGS = {"happy", "upbeat", "feel good", "fun", "cheerful", "summer", "uplifting", "joyful"}
_SAD_TAGS = {"sad", "melancholic", "melancholy", "depressive", "depressing", "dark", "gloomy", "sad songs",
             "heartbreak", "dramatic", "doom"}


def _normalize(tag: str) -> str:
    return re.sub(r"[\s_\-/]+", " ", tag.casefold()).strip()


_KEYWORDS: list[tuple[str, re.Pattern[str], Genre]] = sorted(
    ((kw, re.compile(rf"(?<![\w&]){re.escape(kw)}(?![\w&])"), g) for g in GENRES for kw in g.keywords),
    key=lambda item: -len(item[0]),
)


def classify_tag(tag: str) -> Genre | None:
    """Map one free-form tag to a genre. The longest matching keyword wins,
    so ``"indie pop"`` is Indie and ``"pop punk"`` is Punk."""
    text = _normalize(tag)
    if text in BY_NAME:
        return BY_NAME[text]
    for name, genre in BY_NAME.items():
        if text == name.casefold():
            return genre
    for _, pattern, genre in _KEYWORDS:
        if pattern.search(text):
            return genre
    return None


@dataclass(frozen=True)
class ArtistGenre:
    """The genre and mood estimate for one artist."""

    genre: str
    valence: float
    energy: float


def profile_from_tags(tags: Iterable[tuple[str, int] | str]) -> ArtistGenre | None:
    """Pick the dominant genre of weighted tags (``(tag, votes)`` or plain strings)."""
    weights: dict[str, float] = {}
    mood = 0.0
    for item in tags:
        tag, votes = (item, 1) if isinstance(item, str) else item
        votes = max(int(votes), 1)
        text = _normalize(tag)
        if text in _HAPPY_TAGS:
            mood += 0.12
        if text in _SAD_TAGS:
            mood -= 0.12
        genre = classify_tag(text)
        if genre is not None:
            weights[genre.name] = weights.get(genre.name, 0) + votes
    if not weights:
        return None
    # Ties are broken by taxonomy order, so the result is deterministic.
    order = {g.name: i for i, g in enumerate(GENRES)}
    best = BY_NAME[max(weights, key=lambda n: (weights[n], -order[n]))]
    valence = min(max(best.valence + max(min(mood, 0.25), -0.25), 0.0), 1.0)
    return ArtistGenre(best.name, round(valence, 3), best.energy)
