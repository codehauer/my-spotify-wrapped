import asyncio

from spotify_wrapped.sample import demo_streams
from spotify_wrapped.statistics import build_report
from spotify_wrapped.tui import WrappedApp
from spotify_wrapped.tui.app import ViewPane


def test_tui_switches_tabs_years_and_themes():
    report = build_report(demo_streams())

    async def run() -> None:
        app = WrappedApp(report)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            for key in "123456":
                await pilot.press(key)
                await pilot.pause()
            await pilot.press("]")
            await pilot.pause()
            assert app.view_key == str(report.years[0])
            assert all(p.stats is report.view(app.view_key) for p in app.query(ViewPane))
            await pilot.press("[")
            await pilot.press("t")
            await pilot.pause()
            assert app.view_key == "all"
            assert app.theme == "wrapped-light"

    asyncio.run(run())
