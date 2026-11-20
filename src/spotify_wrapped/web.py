"""The web UI: a single, self-contained HTML file with the statistics embedded.

The page itself is a React app (Meta Astryx components + TanStack Charts) living
in ``web/``. ``npm run build`` compiles it into ``web_template/index.html``
inside this package; this module only injects the statistics JSON into it.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from .statistics import Report

PLACEHOLDER = '"__WRAPPED_DATA__"'


class MissingWebBuildError(RuntimeError):
    pass


def render_html(report: Report) -> str:
    """Return the complete HTML page for ``report``."""
    template = files("spotify_wrapped").joinpath("web_template/index.html")
    if not template.is_file():
        raise MissingWebBuildError(
            "The web UI has not been built yet. Run `npm install && npm run build` in the web/ folder."
        )
    html = template.read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        raise MissingWebBuildError("The web UI template does not contain the data placeholder.")
    # Escape "</" so track names can never close the surrounding <script> element.
    payload = report.to_json().replace("</", "<\\/")
    return html.replace(PLACEHOLDER, payload, 1)


def write_html_report(report: Report, output: str | Path) -> Path:
    """Write the report to ``output`` (a file, or a folder that receives ``spotify_wrapped.html``)."""
    output = Path(output)
    if output.is_dir() or output.suffix.lower() not in {".html", ".htm"}:
        output.mkdir(parents=True, exist_ok=True)
        output = output / "spotify_wrapped.html"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(report), encoding="utf-8")
    return output
