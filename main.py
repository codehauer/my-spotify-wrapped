"""Backwards compatible entry point: ``python main.py -d DATA -s OUT_FOLDER``.

Prefer the ``spotify-wrapped`` command (``uv run spotify-wrapped --help``).
"""

import argparse
import sys

from spotify_wrapped.cli import main as cli_main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create the HTML report (legacy interface).")
    parser.add_argument("-d", "--data_path", required=True)
    parser.add_argument("-s", "--out_path", required=True)
    args = parser.parse_args()
    sys.exit(cli_main(["web", "--data", args.data_path, "--output", args.out_path]))
