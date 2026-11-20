# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Turns the Spotify GDPR data export (`StreamingHistory*.json` files, each a list of `{endTime, artistName, trackName, msPlayed}` records, with `endTime` formatted as `"YYYY-MM-DD HH:MM"`) into listening statistics. Python ≥3.12, dependencies managed with **uv** (`pyproject.toml` / `uv.lock`). `requirements.txt` and `shell.nix` are older setups. There are no tests.

## Commands

```bash
uv sync                                   # install dependencies
uv run main.py -d <dir_with_history_json> -s <out_dir>   # HTML report
uv run -m tui                             # Textual TUI (run from the folder that contains MyData/, see below)
uv run textual run --dev tui.py           # TUI with textual-dev live CSS/devtools
uv run texttual_server.py                 # serve the TUI in a browser via textual-serve
uv run mypy .                             # type checking (mypy is a project dependency)
```

## Architecture

There are two independent front ends that do not share analysis code:

1. **HTML report (original, 2022)**: `main.py` → `helper_functions.read_histories` loads **every** file in `-d` as JSON and concatenates them, so the directory must contain only history files. `main.py` splits the records into parallel lists, and the `data_parser.parse_*` functions turn each list into an `HTMLContainer` tree built from the small component classes in `html_components.py`. Each component renders through `__str__`. The output dir receives `spotify_stats.html`, `stream_chart.html` (a Plotly chart embedded through an iframe) and `style.css`. The CSS is hardcoded as a minified string in `main.py`. `style.css` in the repo is the source, and `compress_stylesheet.py` is a dev helper that minifies it so it can be pasted into that string.

2. **TUI (current work on the `tui-development` branch)**: `analysis.py` is a pandas script that runs at **import time**. It reads hardcoded paths `./MyData/StreamingHistory0.json` and `StreamingHistory1.json` relative to the CWD, filters to the hardcoded `YEAR` constant, and exposes the results as module-level Series/DataFrames. `tui.py` (Textual `WrappedApp`) imports those globals directly and renders them as `StatisticsTable` widgets plus a `Sparkline`. When you add a statistic, compute it in `analysis.py` and import it in `tui.py`.

`lookback.py` is a legacy console prototype. It depends on `prettytable`, which is not in the dependencies.

## Data

The user's export lives in `my_spotify_data/MyData/`. `*.json`, `data/` and `out/` are gitignored. Never commit personal streaming data.
