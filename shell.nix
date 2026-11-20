{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "my-spotify-wrapped";

  buildInputs = with pkgs; [
    uv          # Python dependencies: `uv sync`, then `uv run spotify-wrapped --help`
    nodejs_22   # only needed to rebuild the web UI (web/)
  ];

  shellHook = ''
    echo "My Spotify Wrapped dev shell – try: uv run spotify-wrapped tui --demo"
  '';
}
