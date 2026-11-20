import json

import pytest

from spotify_wrapped.cli import main
from spotify_wrapped.enrich import MusicBrainzLookup, add_genres, apply_genres, genres_from_file, musicbrainz_tags
from spotify_wrapped.genres import ArtistGenre, classify_tag, profile_from_tags
from spotify_wrapped.loader import load_streams
from spotify_wrapped.sample import demo_streams
from spotify_wrapped.statistics import build_report

MIN = 60_000


@pytest.mark.parametrize(("tag", "genre"), [
    ("german hip hop", "Hip-Hop & Rap"),
    ("Deutschrap", "Hip-Hop & Rap"),
    ("indie pop", "Indie & Alternative"),
    ("pop punk", "Punk & Emo"),
    ("pop rock", "Rock"),
    ("dance-pop", "Pop"),
    ("electropop", "Pop"),
    ("hardcore techno", "Electronic & Dance"),
    ("R&B", "R&B & Soul"),
    ("Schlager", "Schlager & Party"),
    ("singer-songwriter", "Folk & Singer-Songwriter"),
    ("Metal", "Metal"),
])
def test_classify_tag(tag, genre):
    assert classify_tag(tag).name == genre


def test_classify_unknown_tag():
    assert classify_tag("german") is None
    assert classify_tag("trapped in a scrap yard") is None  # keywords only match whole words
    assert classify_tag("scrapbook") is None


def test_profile_from_tags_weighs_votes_and_mood():
    profile = profile_from_tags([("rock", 2), ("hip hop", 5), ("german", 9), ("sad", 1)])
    assert profile.genre == "Hip-Hop & Rap"
    assert profile.valence < 0.5  # the genre default, nudged down by "sad"
    assert profile_from_tags(["german", "female vocalists"]) is None


def search_result(*artists):
    return {"artists": list(artists)}


def test_musicbrainz_prefers_exact_name_with_tags():
    calls = []

    def fetch(url):
        calls.append(url)
        return search_result(
            {"name": "Alpha Band", "score": 100, "tags": [{"name": "metal", "count": 3}]},
            {"name": "Alpha", "score": 95, "tags": []},
            {"name": "Alpha", "score": 90, "tags": [{"name": "dream pop", "count": 2}, {"name": "sad", "count": 1}]},
        )

    assert musicbrainz_tags("Alpha", fetch_json=fetch) == [("dream pop", 2), ("sad", 1)]
    assert "fmt=json" in calls[-1]
    # No exact name match: fall back to a near-certain search hit.
    assert musicbrainz_tags('AC/DC "live"', fetch_json=fetch) == [("metal", 3)]
    assert "AC%5C%2FDC+%5C%22live%5C%22" in calls[-1]  # Lucene special characters are escaped


def test_musicbrainz_lookup_is_cached(tmp_path):
    calls = []

    def fetch(artist):
        calls.append(artist)
        return [("techno", 1)] if artist == "Alpha" else None

    cache = tmp_path / "cache.json"
    first = MusicBrainzLookup(cache, fetch=fetch, delay=0, log=lambda _: None).lookup(["Alpha", "Beta"])
    assert first == {"Alpha": ArtistGenre("Electronic & Dance", 0.62, 0.88), "Beta": None}
    again = MusicBrainzLookup(cache, fetch=fetch, delay=0, log=lambda _: None).lookup(["Alpha", "Beta"])
    assert again == first
    assert calls == ["Alpha", "Beta"]


def test_musicbrainz_lookup_survives_network_errors(tmp_path):
    def fetch(artist):
        raise OSError("offline")

    lookup = MusicBrainzLookup(tmp_path / "cache.json", fetch=fetch, delay=0, log=lambda _: None)
    assert lookup.lookup(["A", "B", "C", "D"]) == {}


def test_genres_from_file(tmp_path):
    path = tmp_path / "genres.json"
    path.write_text(json.dumps({"Alpha": "Hip-Hop & Rap", "Beta": ["acoustic", "happy"], "Gamma": []}))
    genres = genres_from_file(path)
    assert genres["Alpha"].genre == "Hip-Hop & Rap"
    assert genres["Beta"].genre == "Folk & Singer-Songwriter"
    assert genres["Gamma"] is None


@pytest.fixture
def party_export(tmp_path):
    def stream(end, artist, ms=4 * MIN):
        return {"endTime": end, "artistName": artist, "trackName": f"{artist} song", "msPlayed": ms}

    streams = [stream(f"2024-03-0{d} {h:02d}:30", "Raver") for d in (1, 2) for h in (22, 23, 0, 1)]
    streams += [stream("2024-03-03 09:00", "Cosy", 3 * MIN), stream("2024-03-03 09:10", "Unknown")]
    (tmp_path / "StreamingHistory0.json").write_text(json.dumps(streams))
    (tmp_path / "genres.json").write_text(json.dumps({"Raver": ["techno"], "Cosy": ["folk"]}))
    return tmp_path


def test_taste_statistics(party_export):
    frame = add_genres(load_streams(party_export / "StreamingHistory0.json", timezone="UTC"),
                       str(party_export / "genres.json"))
    taste = build_report(frame).view().taste
    assert taste is not None
    assert [g.genre for g in taste.genres] == ["Electronic & Dance", "Folk & Singer-Songwriter"]
    assert sum(g.share for g in taste.genres) == pytest.approx(100, abs=0.2)
    assert taste.coverage == pytest.approx(100 * 35 / 39, abs=0.1)  # "Unknown" has no genre
    assert taste.trinity.dominant == "atzig"
    assert all(0 <= v <= 100 for v in (taste.trinity.atzig, taste.trinity.fotzig, taste.trinity.mausig))
    hour_23 = {c.genre: c.share for c in taste.genre_hours if c.hour == 23}
    assert hour_23 == {"Electronic & Dance": 100.0, "Folk & Singer-Songwriter": 0.0}
    assert len(taste.mood_heatmap) == 7 * 24
    assert len(taste.mood_hours) == 24
    # Too few streams at 09:00 to rate the mood.
    assert next(m for m in taste.mood_hours if m.hour == 9).happiness is None


def test_report_without_genres_has_no_taste():
    report = build_report(demo_streams(with_genres=False))
    assert report.view().taste is None
    assert "Holy trinity" not in {h.title for h in report.view().highlights}


def test_demo_report_has_taste():
    view = build_report(demo_streams()).view()
    assert view.taste is not None
    assert len(view.taste.genres) == 8 and view.taste.genres[-1].genre == "Other"
    assert {"Top genre", "Holy trinity", "Listening mood"} <= {h.title for h in view.highlights}
    json.loads(build_report(demo_streams()).to_json())


def test_apply_genres_keeps_unknown_artists():
    frame = apply_genres(demo_streams(with_genres=False), {})
    assert frame["genre"].isna().all()


def test_cli_with_genre_file(party_export, capsys):
    assert main(["json", "--data", str(party_export / "StreamingHistory0.json"), "--timezone", "UTC",
                 "--genres", str(party_export / "genres.json")]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["views"]["all"]["taste"]["trinity"]["dominant"] == "atzig"
