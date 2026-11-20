"""Command line entry point: ``spotify-wrapped {tui,web,json}``."""

from __future__ import annotations

import argparse
import shlex
import sys
import webbrowser
from pathlib import Path

from .enrich import DEFAULT_ARTIST_LIMIT, add_genres
from .loader import NoStreamingHistoryError, load_streams
from .sample import demo_streams
from .statistics import Report, build_report


def _add_data_arguments(parser: argparse.ArgumentParser) -> None:
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("-d", "--data", type=Path, metavar="PATH",
                        help="your unpacked Spotify export (folder or single JSON file)")
    source.add_argument("--demo", action="store_true", help="use a generated, fictional history instead")
    parser.add_argument("-y", "--year", type=int, help="year to show first (default: all time)")
    parser.add_argument("-n", "--top", type=int, default=10, metavar="N", help="length of rankings (default: 10)")
    parser.add_argument("--timezone", metavar="TZ",
                        help="timezone for hours and days, e.g. Europe/Berlin (default: this computer's)")
    parser.add_argument("-g", "--genres", nargs="?", const="musicbrainz", metavar="SOURCE",
                        help="add genre, mood and atzig/fotzig/mausig statistics: look up artist genres on "
                             "MusicBrainz (default, sends artist names, results are cached) or read them "
                             "from a JSON file {artist: genre or [tags]}")
    parser.add_argument("--genre-artists", type=int, default=DEFAULT_ARTIST_LIMIT, metavar="N",
                        help=f"look up the N most played artists on MusicBrainz (default: {DEFAULT_ARTIST_LIMIT})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spotify-wrapped",
        description="Visualize your Spotify data export – in the terminal or in the browser.",
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    tui = commands.add_parser("tui", help="explore your statistics in the terminal")
    _add_data_arguments(tui)
    tui.add_argument("--serve", action="store_true", help="serve the terminal UI in the browser (textual-serve)")
    tui.add_argument("--port", type=int, default=8000, help="port for --serve (default: 8000)")

    web = commands.add_parser("web", help="create a self-contained HTML report")
    _add_data_arguments(web)
    web.add_argument("-o", "--output", type=Path, default=Path("spotify_wrapped.html"),
                     help="output file or folder (default: ./spotify_wrapped.html)")
    web.add_argument("--open", action="store_true", help="open the report in your browser")

    json_cmd = commands.add_parser("json", help="export the raw statistics as JSON")
    _add_data_arguments(json_cmd)
    json_cmd.add_argument("-o", "--output", type=Path, help="output file (default: stdout)")
    return parser


def load_report(args: argparse.Namespace) -> Report:
    frame = demo_streams(args.timezone) if args.demo else load_streams(args.data, args.timezone)
    if args.genres and not args.demo:
        frame = add_genres(frame, args.genres, limit=args.genre_artists)
    return build_report(frame, top_n=args.top, year=args.year)


def _forwarded_data_args(args: argparse.Namespace) -> list[str]:
    forwarded = ["--demo"] if args.demo else ["--data", str(Path(args.data).resolve())]
    if args.year:
        forwarded += ["--year", str(args.year)]
    if args.timezone:
        forwarded += ["--timezone", args.timezone]
    if args.genres:
        source = args.genres if args.genres == "musicbrainz" else str(Path(args.genres).resolve())
        forwarded += ["--genres", source, "--genre-artists", str(args.genre_artists)]
    return forwarded + ["--top", str(args.top)]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "tui" and args.serve:
            from textual_serve.server import Server

            command = shlex.join([sys.executable, "-m", "spotify_wrapped", "tui", *_forwarded_data_args(args)])
            Server(command, port=args.port, title="My Spotify Wrapped").serve()
            return 0

        report = load_report(args)

        if args.command == "tui":
            from .tui import run_tui

            run_tui(report)
        elif args.command == "web":
            from .web import write_html_report

            path = write_html_report(report, args.output)
            print(f"Wrote your report to {path}")
            if args.open:
                webbrowser.open(path.resolve().as_uri())
        elif args.command == "json":
            if args.output:
                args.output.write_text(report.to_json(indent=2), encoding="utf-8")
                print(f"Wrote statistics to {args.output}", file=sys.stderr)
            else:
                print(report.to_json(indent=2))
    except (NoStreamingHistoryError, ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
