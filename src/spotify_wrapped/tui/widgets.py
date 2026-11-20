"""Reusable widgets that render parts of :class:`~spotify_wrapped.statistics.WrappedStatistics`."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from rich.text import Text
from textual.app import ComposeResult
from textual.color import Color
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import DataTable, Label, Static

from ..formatting import format_duration, format_number
from ..statistics import Bucket, DayStat, HeatCell, Highlight, RankedItem
from datetime import date

_HORIZONTAL_BLOCKS = " ▏▎▍▌▋▊▉█"
_VERTICAL_BLOCKS = " ▁▂▃▄▅▆▇█"
WEEKDAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def horizontal_bar(value: float, maximum: float, width: int) -> str:
    """Render ``value`` as a bar of up to ``width`` cells using eighth blocks."""
    if maximum <= 0 or width <= 0:
        return ""
    eighths = round(max(value, 0) / maximum * width * 8)
    full, rest = divmod(eighths, 8)
    return "█" * full + (_HORIZONTAL_BLOCKS[rest] if rest else "")


class ThemedWidget(Widget):
    """A widget whose rendering depends on theme colors and must refresh on theme changes."""

    def on_mount(self) -> None:
        self.watch(self.app, "theme", self._on_theme_change, init=False)

    def _on_theme_change(self) -> None:
        self.refresh()

    def color(self, name: str = "primary") -> Color:
        return Color.parse(self.app.theme_variables[name])


class Section(Vertical):
    """A titled, bordered panel."""

    def __init__(self, title: str, *children: Widget, subtitle: str = "", **kwargs) -> None:
        super().__init__(*children, **kwargs)
        self.border_title = title
        self.border_subtitle = subtitle


class StatCard(Vertical):
    """A KPI tile: label, big value and an optional caption."""

    def __init__(self, label: str, value: str, caption: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._label, self._value, self._caption = label, value, caption

    def compose(self) -> ComposeResult:
        yield Label(self._label, classes="stat-label")
        yield Label(self._value, classes="stat-value")
        if self._caption:
            yield Label(self._caption, classes="stat-caption")


class HighlightCard(Vertical):
    def __init__(self, highlight: Highlight, **kwargs) -> None:
        super().__init__(**kwargs)
        self.highlight = highlight

    def compose(self) -> ComposeResult:
        h = self.highlight
        yield Label(f"{h.icon} {h.title.upper()}", classes="highlight-title")
        yield Label(h.value, classes="highlight-value")
        yield Static(h.detail, classes="highlight-detail")


class FocusCursorTable(DataTable):
    """A data table that only highlights its cursor row while it has keyboard focus."""

    def __init__(self, **kwargs) -> None:
        super().__init__(cursor_type="row", zebra_stripes=True, show_cursor=False, **kwargs)

    def on_focus(self) -> None:
        self.show_cursor = True

    def on_blur(self) -> None:
        self.show_cursor = False


class RankingTable(FocusCursorTable):
    """A ranking of artists, tracks or albums with an inline bar."""

    BAR_WIDTH = 18

    def __init__(self, items: Sequence[RankedItem], metric: str = "streams", **kwargs) -> None:
        super().__init__(**kwargs)
        self.items = list(items)
        self.metric = metric

    def on_mount(self) -> None:
        has_artist = any(i.artist for i in self.items)
        self.add_column("#", key="rank")
        self.add_column("Name", key="name")
        if has_artist:
            self.add_column("Artist", key="artist")
        self.add_column("Streams", key="streams")
        self.add_column("Time", key="time")
        self.add_column("", key="bar", width=self.BAR_WIDTH)
        self._fill_rows(has_artist)
        self.watch(self.app, "theme", lambda _: self._fill_rows(has_artist), init=False)

    def _fill_rows(self, has_artist: bool) -> None:
        self.clear()
        primary = self.app.theme_variables["primary"]
        values = [i.streams if self.metric == "streams" else i.minutes for i in self.items]
        maximum = max(values, default=0)
        for item, value in zip(self.items, values):
            row: list[str | Text] = [Text(str(item.rank), style="bold"), Text(item.name, style="bold")]
            if has_artist:
                row.append(Text(item.artist or "", style="dim"))
            row += [
                Text(format_number(item.streams), justify="right"),
                Text(format_duration(item.minutes), justify="right"),
                Text(horizontal_bar(value, maximum, self.BAR_WIDTH), style=primary),
            ]
            self.add_row(*row, key=f"{item.rank}")


class TopDaysTable(FocusCursorTable):
    """The days with the most streams."""

    def __init__(self, days: Sequence[DayStat], **kwargs) -> None:
        super().__init__(**kwargs)
        self.days = list(days)

    def on_mount(self) -> None:
        self.add_columns("#", "Day", "Streams", "Time", "Top artist")
        for rank, day in enumerate(self.days, start=1):
            self.add_row(
                Text(str(rank), style="bold"),
                Text(date.fromisoformat(day.date).strftime("%a, %d %b %Y"), style="bold"),
                Text(format_number(day.streams), justify="right"),
                Text(format_duration(day.minutes), justify="right"),
                Text(day.top_artist or "", style="dim"),
            )


class HorizontalBars(ThemedWidget):
    """Labelled horizontal bars, e.g. for weekdays."""

    DEFAULT_CSS = "HorizontalBars { height: auto; }"

    def __init__(self, buckets: Sequence[Bucket], highlight_max: bool = True, **kwargs) -> None:
        super().__init__(**kwargs)
        self.buckets = list(buckets)
        self.highlight_max = highlight_max

    def get_content_height(self, container, viewport, width: int) -> int:  # noqa: D401
        return len(self.buckets)

    def render(self) -> Text:
        label_width = max((len(b.label) for b in self.buckets), default=0)
        value_width = max((len(format_number(b.streams)) for b in self.buckets), default=0)
        bar_width = max(self.size.width - label_width - value_width - 4, 1)
        maximum = max((b.streams for b in self.buckets), default=0)
        primary = self.color("primary")
        muted = self.color("background").blend(primary, 0.55)
        text = Text()
        for b in self.buckets:
            is_max = self.highlight_max and b.streams == maximum
            text.append(f"{b.label:<{label_width}} ", style="bold" if is_max else "")
            bar = horizontal_bar(b.streams, maximum, bar_width)
            text.append(f"{bar:<{bar_width}}", style=(primary if is_max else muted).rich_color.name)
            text.append(f" {format_number(b.streams):>{value_width}}\n", style="dim")
        text.rstrip()
        return text


class ColumnChart(ThemedWidget):
    """A vertical bar chart (e.g. streams per hour) drawn with eighth blocks."""

    DEFAULT_CSS = "ColumnChart { height: 12; }"

    def __init__(self, buckets: Sequence[Bucket], label_every: int = 3,
                 short_label: Callable[[Bucket], str] | None = None, gap: bool = True, **kwargs) -> None:
        super().__init__(**kwargs)
        self.buckets = list(buckets)
        self.gap = gap
        self.label_every = label_every
        self.short_label: Callable[[Bucket], str] = short_label or (lambda b: str(b.key))

    def render(self) -> Text:
        count = len(self.buckets)
        if not count:
            return Text("No data")
        width = max(self.size.width, count)
        chart_height = max(self.size.height - 1, 1)
        # Columns are stretched proportionally so the chart always fills the full width.
        starts = [i * width // count for i in range(count + 1)]
        maximum = max(b.streams for b in self.buckets) or 1
        heights = [round(b.streams / maximum * chart_height * 8) for b in self.buckets]
        peak = max(range(count), key=lambda i: heights[i])
        primary = self.color("primary")
        faded = self.color("background").blend(primary, 0.55)

        text = Text()
        for row in range(chart_height, 0, -1):
            for i, h in enumerate(heights):
                span = starts[i + 1] - starts[i]
                bar_width = span - 1 if self.gap and span > 1 else span
                level = min(max(h - (row - 1) * 8, 0), 8)
                color = (primary if i == peak else faded).rich_color.name
                text.append(_VERTICAL_BLOCKS[level] * bar_width, style=color)
                text.append(" " * (span - bar_width))
            text.append("\n")
        axis = [" "] * width
        for i in range(0, count, self.label_every):
            for offset, char in enumerate(self.short_label(self.buckets[i])):
                if starts[i] + offset < width:
                    axis[starts[i] + offset] = char
        text.append("".join(axis), style="dim")
        return text


class Heatmap(ThemedWidget):
    """Weekday × hour heatmap of streams."""

    DEFAULT_CSS = "Heatmap { height: 9; }"

    def __init__(self, cells: Sequence[HeatCell], **kwargs) -> None:
        super().__init__(**kwargs)
        self.cells = list(cells)

    def render(self) -> Text:
        cell_width = max(min((self.size.width - 5) // 24, 4), 1)
        maximum = max((c.streams for c in self.cells), default=0) or 1
        grid = {(c.weekday, c.hour): c.streams for c in self.cells}
        base = self.color("surface")
        hot = self.color("primary")
        text = Text()
        header = "".join(f"{h:<{cell_width * 3}}" for h in range(0, 24, 3))
        text.append("     " + header[: cell_width * 24] + "\n", style="dim")
        for day in range(7):
            text.append(f"{WEEKDAY_SHORT[day]}  ", style="dim")
            for hour in range(24):
                value = grid.get((day, hour), 0)
                shade = base.blend(hot, 0.12 + 0.88 * (value / maximum) ** 0.8) if value else base
                text.append(" " * cell_width, style=f"on {shade.rich_color.name}")
            text.append("\n")
        text.append("     less ", style="dim")
        for step in range(6):
            text.append("  ", style=f"on {base.blend(hot, 0.12 + 0.88 * step / 5).rich_color.name}")
        text.append(" more", style="dim")
        return text
