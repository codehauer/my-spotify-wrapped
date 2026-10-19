{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python312Packages.numpy
    pkgs.python312Packages.pandas
    pkgs.python312Packages.plotly
    pkgs.python312Packages.camelot
    pkgs.python312Packages.weasyprint
    pkgs.python312Packages.rq
    pkgs.python312Packages.redis
    pkgs.python312
    pkgs.ghostscript
    pkgs.python312Packages.ghostscript
  ];
}