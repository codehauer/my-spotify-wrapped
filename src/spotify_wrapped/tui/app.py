"""The terminal user interface (built with Textual)."""

from __future__ import annotations

from datetime import date

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.theme import Theme
from textual.widgets import Footer, Label, Select, TabbedContent, TabPane

from ..formatting import format_duration, format_number, plural
from ..statistics import Report, WrappedStatistics
from .widgets import TopDaysTable, ColumnChart, Heatmap, HighlightCard, HorizontalBars, RankingTable, Section, StatCard

THEMES = [
    Theme(
        name="wrapped-dark", dark=True,
        primary="#1ED760", secondary="#B49BFC", accent="#F573A0",
        warning="#FFC864", error="#F15E6C", success="#1ED760",
        foreground="#EDEDED", background="#121212", surface="#1C1C1C", panel="#262626",
    ),
    Theme(
        name="wrapped-light", dark=False,
        primary="#0E8A3E", secondary="#6B45D9", accent="#C2185B",
        warning="#B26A00", error="#C62828", success="#0E8A3E",
        foreground="#191414", background="#F7F7F5", surface="#FFFFFF", panel="#ECECE8",
    ),
]


def _date(iso: str) -> str:
    return date.fromisoformat(iso[:10]).strftime("%d %b %Y")


class ViewPane(TabPane):
    """A tab whose content is rebuilt whenever the selected year changes."""

    stats: reactive[WrappedStatistics | None] = reactive(None, recompose=True)

    def __init__(self, title: str, id: str) -> None:
        super().__init__(title, id=id)

    def compose(self) -> ComposeResult:
        if self.stats is not None:
            with VerticalScroll():
                yield from self.build(self.stats)

    def build(self, s: WrappedStatistics) -> ComposeResult:
        raise NotImplementedError


class OverviewPane(ViewPane):
    def build(self, s: WrappedStatistics) -> ComposeResult:
        o = s.overview
        with Grid(classes="stat-grid"):
            yield StatCard("Streams", format_number(o.total_streams),
                           f"{o.average_stream_minutes:.1f} min per stream")
            yield StatCard("Listening time", format_duration(o.total_minutes),
                           f"{format_number(o.total_minutes)} minutes")
            yield StatCard("Artists", format_number(o.unique_artists),
                           f"{o.streams_per_artist:.1f} streams each")
            yield StatCard("Tracks", format_number(o.unique_tracks),
                           f"{o.streams_per_track:.1f} streams each")
            yield StatCard("Active days", f"{o.active_days} / {o.days_in_period}",
                           f"{o.active_day_share}% of the period")
            yield StatCard("Longest streak", plural(o.longest_streak, "day"),
                           f"{format_duration(o.average_minutes_per_active_day)} per active day")
        with Grid(classes="highlight-grid"):
            for highlight in s.highlights:
                yield HighlightCard(highlight)


class ArtistsPane(ViewPane):
    def build(self, s: WrappedStatistics) -> ComposeResult:
        with Horizontal(classes="columns"):
            yield Section(f"Top {len(s.top_artists)} artists · by streams", RankingTable(s.top_artists))
            yield Section(f"Top {len(s.top_artists_by_time)} artists · by listening time",
                          RankingTable(s.top_artists_by_time, metric="minutes"))
        yield Section("Least streamed artists", RankingTable(s.least_streamed_artists),
                      subtitle="the long tail of your library")


class TracksPane(ViewPane):
    def build(self, s: WrappedStatistics) -> ComposeResult:
        yield Section(f"Top {len(s.top_tracks)} tracks · by streams", RankingTable(s.top_tracks))
        yield Section(f"Top {len(s.top_tracks_by_time)} tracks · by listening time",
                      RankingTable(s.top_tracks_by_time, metric="minutes"))
        if s.top_albums:
            yield Section(f"Top {len(s.top_albums)} albums", RankingTable(s.top_albums))


class TimelinePane(ViewPane):
    def build(self, s: WrappedStatistics) -> ComposeResult:
        busiest = max(s.weekly, key=lambda b: b.streams)
        yield Section(
            "Streams per week",
            ColumnChart(s.weekly, label_every=max(len(s.weekly) // 6, 1), gap=len(s.weekly) <= 30,
                        short_label=lambda b: _date(str(b.key)), id="weekly-chart"),
            subtitle=f"busiest week: {_date(str(busiest.key))} ({format_number(busiest.streams)} streams)",
        )
        yield Section("Streams per month", ColumnChart(
            s.monthly, label_every=max(len(s.monthly) // 6, 1), short_label=lambda b: b.label, id="monthly-chart"))
        yield Section("Your biggest days", TopDaysTable(s.top_days))


class HabitsPane(ViewPane):
    def build(self, s: WrappedStatistics) -> ComposeResult:
        o = s.overview
        yield Section("When do you listen?", ColumnChart(s.hours, label_every=3), id="hours",
                      subtitle=f"peak at {o.peak_hour:02d}:00")
        with Horizontal(classes="columns"):
            yield Section("Weekdays", HorizontalBars(s.weekdays), id="weekdays")
            yield Section("Weekday × hour", Heatmap(s.heatmap), id="heatmap")


class WrappedApp(App[None]):
    """My Spotify Wrapped – terminal edition."""

    CSS_PATH = "wrapped.tcss"
    TITLE = "My Spotify Wrapped"
    HORIZONTAL_BREAKPOINTS = [(0, "-narrow"), (110, "-wide")]
    BINDINGS = [
        Binding("1", "show_tab('overview')", "Overview"),
        Binding("2", "show_tab('artists')", "Artists"),
        Binding("3", "show_tab('tracks')", "Tracks"),
        Binding("4", "show_tab('timeline')", "Timeline"),
        Binding("5", "show_tab('habits')", "Habits"),
        Binding("left_square_bracket", "cycle_view(-1)", "Prev year", key_display="["),
        Binding("right_square_bracket", "cycle_view(1)", "Next year", key_display="]"),
        Binding("t", "toggle_dark", "Light/Dark"),
        Binding("q", "quit", "Quit"),
    ]

    view_key: reactive[str] = reactive("all", init=False)

    def __init__(self, report: Report) -> None:
        super().__init__()
        self.report = report
        for theme in THEMES:
            self.register_theme(theme)
        self.theme = "wrapped-dark"
        self.view_keys = ["all", *map(str, report.years)]

    def compose(self) -> ComposeResult:
        with Horizontal(id="topbar"):
            yield Label("♫ [b]My Spotify Wrapped[/b]", id="brand")
            yield Label("", id="period")
            yield Select(
                [(self.report.views[k].label, k) for k in self.view_keys],
                value=self.report.default_view, allow_blank=False, id="view-select", compact=True,
            )
        with TabbedContent(initial="overview"):
            yield OverviewPane("Overview", id="overview")
            yield ArtistsPane("Artists", id="artists")
            yield TracksPane("Tracks", id="tracks")
            yield TimelinePane("Timeline", id="timeline")
            yield HabitsPane("Habits", id="habits")
        yield Footer()

    def on_mount(self) -> None:
        self.set_reactive(WrappedApp.view_key, self.report.default_view)
        self.watch_view_key(self.view_key)

    def watch_view_key(self, key: str) -> None:
        stats = self.report.view(key)
        for pane in self.query(ViewPane):
            pane.stats = stats
        self.query_one("#period", Label).update(
            f"{_date(stats.period_start)} – {_date(stats.period_end)} · times in {self.report.timezone}")
        self.query_one("#view-select", Select).value = key
        self.sub_title = stats.label

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "view-select" and isinstance(event.value, str):
            self.view_key = event.value

    def action_show_tab(self, tab: str) -> None:
        self.query_one(TabbedContent).active = tab

    def action_cycle_view(self, step: int) -> None:
        index = self.view_keys.index(self.view_key)
        self.view_key = self.view_keys[(index + step) % len(self.view_keys)]

    def action_toggle_dark(self) -> None:
        self.theme = "wrapped-light" if self.theme == "wrapped-dark" else "wrapped-dark"


def run_tui(report: Report) -> None:
    WrappedApp(report).run()
