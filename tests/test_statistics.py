import json

import pytest

from spotify_wrapped.loader import NoStreamingHistoryError, load_streams
from spotify_wrapped.sample import demo_streams, write_sample_export
from spotify_wrapped.statistics import build_report

MIN = 60_000


def account(end_time: str, artist: str, track: str, ms: int) -> dict:
    return {"endTime": end_time, "artistName": artist, "trackName": track, "msPlayed": ms}


@pytest.fixture
def export_dir(tmp_path):
    """A tiny export in the account format plus files the loader must ignore."""
    streams = [
        account("2023-12-31 22:00", "Alpha", "One", 3 * MIN),
        account("2024-01-01 10:00", "Alpha", "One", 3 * MIN),
        account("2024-01-01 11:00", "Alpha", "Two", 4 * MIN),
        account("2024-01-02 20:00", "Beta", "Three", 10 * MIN),
        account("2024-01-04 20:30", "Alpha", "One", 2 * MIN),
        account("2024-01-04 20:31", "Gamma", "Four", 0),  # zero playtime is dropped
    ]
    (tmp_path / "StreamingHistory0.json").write_text(json.dumps(streams))
    # Duplicate of the first stream (overlapping exports) is dropped too.
    (tmp_path / "StreamingHistory1.json").write_text(json.dumps(streams[:1]))
    (tmp_path / "Userdata.json").write_text(json.dumps({"username": "x"}))
    (tmp_path / "Playlist1.json").write_text(json.dumps({"playlists": []}))
    (tmp_path / "notes.json").write_text("not json")
    return tmp_path


def test_loader_normalizes_and_filters(export_dir):
    frame = load_streams(export_dir, timezone="UTC")
    assert list(frame.columns) == ["played_at", "artist", "track", "album", "ms_played"]
    assert len(frame) == 5
    assert frame["played_at"].is_monotonic_increasing
    assert str(frame["played_at"].dt.tz) == "UTC"


def test_loader_converts_timezone(export_dir):
    frame = load_streams(export_dir, timezone="Europe/Berlin")
    assert frame["played_at"].iloc[0].hour == 23


def test_loader_without_history(tmp_path):
    (tmp_path / "Userdata.json").write_text("{}")
    with pytest.raises(NoStreamingHistoryError):
        load_streams(tmp_path)


def test_report_numbers(export_dir):
    report = build_report(load_streams(export_dir, timezone="UTC"), top_n=3)
    assert report.years == [2023, 2024]
    assert set(report.views) == {"all", "2023", "2024"}

    view = report.view()
    ov = view.overview
    assert ov.total_streams == 5
    assert ov.total_minutes == 22.0
    assert ov.unique_artists == 2
    assert ov.unique_tracks == 3
    assert ov.unique_albums is None
    assert ov.active_days == 4  # Dec 31, Jan 1, Jan 2, Jan 4
    assert ov.days_in_period == 5
    assert ov.longest_streak == 3
    assert (ov.longest_streak_start, ov.longest_streak_end) == ("2023-12-31", "2024-01-02")
    assert ov.longest_stream.track == "Three"
    assert ov.one_off_artists == 1

    assert [(a.name, a.streams, a.share) for a in view.top_artists] == [("Alpha", 4, 80.0), ("Beta", 1, 20.0)]
    assert view.top_artists_by_time[0].name == "Alpha"  # 12 min vs 10 min
    assert view.least_streamed_artists[0].name == "Beta"
    assert (view.top_tracks[0].name, view.top_tracks[0].artist, view.top_tracks[0].streams) == ("One", "Alpha", 3)
    assert view.top_tracks_by_time[0].name == "Three"

    # Daily series is zero-filled across the whole period.
    assert [d.streams for d in view.daily] == [1, 2, 1, 0, 1]
    assert view.top_days[0].date == "2024-01-01"
    assert view.top_days[0].top_artist == "Alpha"
    assert len(view.hours) == 24 and len(view.weekdays) == 7 and len(view.heatmap) == 7 * 24
    assert sum(c.streams for c in view.heatmap) == 5
    assert ov.peak_hour == 20

    year = report.view(2024)
    assert year.overview.total_streams == 4
    assert year.year == 2024
    assert year.overview.days_in_period == 4  # Jan 1 until the end of the export


def test_report_is_json_serializable_and_has_highlights():
    report = build_report(demo_streams(), top_n=5)
    data = json.loads(report.to_json())
    assert data["schema_version"] == 1
    view = data["views"]["all"]
    assert len(view["top_artists"]) == 5
    assert view["top_albums"], "the extended format carries album names"
    assert {h["title"] for h in view["highlights"]} >= {"Top artist", "Top track", "Longest streak"}


def test_extended_export_roundtrip(tmp_path):
    write_sample_export(tmp_path / "Spotify Extended Streaming History", days=30)
    frame = load_streams(tmp_path)
    assert len(frame) > 100
    assert frame["album"].notna().all()


def test_unknown_year():
    with pytest.raises(ValueError, match="Available years"):
        build_report(demo_streams(), year=1999)
