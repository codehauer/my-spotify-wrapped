# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Turns the Spotify GDPR data export into listening statistics, shown in a terminal UI (Textual) or a self-contained web page (React). Two export formats are supported: "Account data" (`StreamingHistory*.json`, records `{endTime: "YYYY-MM-DD HH:MM", artistName, trackName, msPlayed}`) and "Extended streaming history" (`Streaming_History_Audio_*.json`, records with `ts`, `ms_played`, `master_metadata_*`). Python ≥3.12, dependencies managed with **uv**. The web UI needs Node.js 22+ only when it is changed.

## Commands

```bash
uv sync                                              # install dependencies
uv run spotify-wrapped tui --data <export_dir>       # terminal UI (--demo for fictional data)
uv run spotify-wrapped tui --demo --serve            # TUI in the browser via textual-serve
uv run spotify-wrapped web --data <export_dir> -o out/   # single-file HTML report
uv run spotify-wrapped json --demo                   # raw statistics as JSON
uv run spotify-wrapped web --data <export_dir> --genres  # + genres/mood/trinity (MusicBrainz lookup, cached)
uv run python main.py -d <export_dir> -s <out_dir>   # legacy interface, same as `web`
uv run pytest                                        # tests
uv run mypy                                          # type checking (configured in pyproject.toml)
cd web && npm install && npm run demo-data && npm run dev   # web UI dev server
cd web && npm run build                              # type-check + rebuild the committed web template
```

## Architecture

All processing lives in one place; the UIs only display its result.

- `src/spotify_wrapped/loader.py`: `load_streams(path, timezone)` recursively reads every JSON file, keeps only files in a known export format, and normalizes them to a DataFrame (`played_at` tz-aware, `artist`, `track`, `album`, `ms_played`). Podcasts, zero-length plays and duplicates are dropped. Timezone defaults to the local machine's.
- `src/spotify_wrapped/enrich.py`: optional `add_genres(frame, source)` adds `genre`, `valence`, `energy` columns per artist, from MusicBrainz tags (rate limited, cached in `~/.cache/spotify-wrapped/`) or a JSON file. `genres.py` folds free-form tags into 13 genres, each with a valence/energy estimate and an atzig/fotzig/mausig profile. Tests must never hit the network: pass a fake `fetch`.
- `src/spotify_wrapped/statistics.py`: `build_report(frame, top_n, year)` returns a `Report` of frozen dataclasses: one `WrappedStatistics` per view (`"all"` plus one per year), including the human-readable `highlights` and the optional `taste` (genres, mood, trinity; `None` without genre columns). **Add new statistics here**, then display them in both UIs.
- `src/spotify_wrapped/tui/`: Textual app (`app.py`, widgets in `widgets.py`, styles in `wrapped.tcss`). Each tab is a `ViewPane` that recomposes when the selected year changes.
- `web/`: React + Meta Astryx (`@astryxdesign/core`, neutral theme) + TanStack Charts (`@tanstack/charts`). `web/src/types.ts` mirrors the Python dataclasses; keep both in sync. `npm run build` produces one inlined HTML file at `src/spotify_wrapped/web_template/index.html` (committed so users don't need Node). `web.py` replaces the `"__WRAPPED_DATA__"` placeholder in it with the report JSON.
- `src/spotify_wrapped/cli.py`: the `spotify-wrapped` entry point. `sample.py` generates the fictional `--demo` history used by tests, including fictional artist genres.

## Data

The user's export lives in `my_spotify_data/MyData/`. `*.json`, `my_spotify_data/`, `data/` and `out/` are gitignored. Never commit personal streaming data; use `--demo` / `spotify_wrapped.sample` for examples, tests and screenshots.
