from __future__ import annotations
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

WIDTHS = [320, 360, 390, 430, 768, 1024, 1280, 1440]


def reset_scroll(page) -> None:
    page.evaluate("""() => {
      window.scrollTo(0, 0);
      document.querySelectorAll('*').forEach((element) => {
        if (element.scrollTop) element.scrollTop = 0;
      });
    }""")


def ensure_sidebar_open(page) -> None:
    sidebar = page.locator("[data-testid='stSidebar']")
    if sidebar.get_attribute("aria-expanded") == "false":
        page.locator("button[data-testid='stBaseButton-headerNoPadding']").nth(1).click()


def ensure_sidebar_closed(page) -> None:
    sidebar = page.locator("[data-testid='stSidebar']")
    if sidebar.get_attribute("aria-expanded") == "true":
        page.locator("button[data-testid='stBaseButton-headerNoPadding']").nth(2).click()


def check_widths(page, name: str, widths: list[int], report: list[dict], errors: list[str]) -> None:
    for width in widths:
        page.set_viewport_size({"width": width, "height": 960})
        measurements = page.evaluate("""() => ({viewport: innerWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth})""")
        measurements["width"] = width
        measurements["page"] = name
        measurements["overflow"] = measurements["document"] > width or measurements["body"] > width
        report.append(measurements)
        if measurements["overflow"]:
            errors.append(f"{name} horizontal overflow at {width}px: {measurements}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Pip viewport overflow and save a screenshot gallery.")
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    gallery = root / "docs" / "screenshots"
    gallery.mkdir(parents=True, exist_ok=True)
    report: list[dict] = []
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page = context.new_page()
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.goto(args.url, wait_until="domcontentloaded", timeout=120_000)
        page.get_by_role("heading", name="A tiny dip in starlight could reveal a whole new world.").wait_for(timeout=120_000)
        if not page.title().startswith("Pip"):
            errors.append(f"Unexpected page title: {page.title()}")
        if not page.locator("link[rel='shortcut icon']").get_attribute("href").startswith("data:image/svg+xml"):
            errors.append("Pip SVG favicon was not loaded.")
        page.wait_for_timeout(900)
        for width in WIDTHS:
            page.set_viewport_size({"width": width, "height": 960})
            page.wait_for_timeout(250)
            measurements = page.evaluate("""() => ({
                viewport: window.innerWidth,
                document: document.documentElement.scrollWidth,
                body: document.body.scrollWidth,
                hero: Math.round(document.querySelector('.pip-hero').getBoundingClientRect().width),
                art: Boolean(document.querySelector('.pip-art')?.naturalWidth)
            })""")
            measurements["width"] = width
            measurements["page"] = "Discover"
            measurements["overflow"] = measurements["document"] > width or measurements["body"] > width
            report.append(measurements)
            if measurements["overflow"]:
                errors.append(f"Discover horizontal overflow at {width}px: {measurements}")
            if width in (390, 768, 1440):
                if width == 390:
                    if page.locator("[data-testid='stSidebar']").get_attribute("aria-expanded") != "false":
                        errors.append("The mobile navigation drawer should start collapsed.")
                    ensure_sidebar_open(page)
                    if not page.get_by_text("Candidate Explorer", exact=True).is_visible():
                        errors.append("Mobile navigation drawer did not reveal its routes.")
                    page.screenshot(path=str(gallery / "discover-nav-390.png"), animations="disabled")
                    ensure_sidebar_closed(page)
                if width == 1440:
                    ensure_sidebar_open(page)
                reset_scroll(page)
                page.screenshot(path=str(gallery / f"discover-{width}.png"), full_page=True, animations="disabled")
        # The landing showcase runs the actual cached science pipeline.
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_role("button", name="Run the real Kepler-10 example").click()
        page.get_by_text("Analysis completed on real Kepler Q17 observations", exact=False).wait_for(timeout=120_000)
        check_widths(page, "Kepler-10 showcase", WIDTHS, report, errors)
        page.set_viewport_size({"width": 1440, "height": 1000})
        for tab_name in ("Raw light curve", "Cleaned light curve", "Folded transit"):
            page.get_by_role("tab", name=tab_name).click()
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.get_by_role("tab", name=tab_name).scroll_into_view_if_needed()
            page.screenshot(path=str(gallery / f"showcase-{tab_name.split()[0].lower()}-1440.png"), animations="disabled")
        page.set_viewport_size({"width": 390, "height": 960})
        page.get_by_role("tab", name="Raw light curve").scroll_into_view_if_needed()
        page.get_by_role("tab", name="Raw light curve").click()
        page.screenshot(path=str(gallery / "showcase-raw-390.png"), animations="disabled")
        # Analyze Star reuses that real session result and preserves the workflow.
        page.get_by_role("button", name="Explore the stars →").click()
        page.get_by_role("button", name="Run BLS analysis").wait_for(timeout=30_000)
        page.get_by_text("Best BLS period:", exact=False).wait_for(timeout=120_000)
        page.wait_for_timeout(700)
        check_widths(page, "Analyze Star", WIDTHS, report, errors)
        for width in (390, 768, 1440):
            page.set_viewport_size({"width": width, "height": 960})
            if width == 1440:
                ensure_sidebar_open(page)
            reset_scroll(page)
            page.screenshot(path=str(gallery / f"analyze-{width}.png"), full_page=True, animations="disabled")
        page.set_viewport_size({"width": 1440, "height": 1000})
        ensure_sidebar_open(page)
        page.get_by_text("Signal Investigation", exact=True).click()
        page.get_by_text("Independent Transit Least Squares verification", exact=False).wait_for(timeout=30_000)
        chart_count = page.locator(".js-plotly-plot").count()
        if chart_count < 1:
            errors.append("Signal Investigation did not render a Plotly chart.")
        check_widths(page, "Signal Investigation", WIDTHS, report, errors)
        page.set_viewport_size({"width": 390, "height": 960})
        page.wait_for_timeout(400)
        measurements = page.evaluate("""() => ({viewport: innerWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth})""")
        measurements["width"] = 390
        measurements["page"] = "Signal Investigation"
        measurements["overflow"] = measurements["document"] > 390 or measurements["body"] > 390
        report.append(measurements)
        if measurements["overflow"]:
            errors.append(f"Signal Investigation horizontal overflow at 390px: {measurements}")
        reset_scroll(page)
        page.screenshot(path=str(gallery / "signal-390.png"), full_page=True, animations="disabled")
        for label, heading in [
            ("Candidate Explorer", "Candidate Explorer"),
            ("Planet Recovery Lab", "Planet Recovery Lab"),
            ("Model Performance", "Model Performance"),
            ("Research & Methods", "Research & Methods"),
        ]:
            page.set_viewport_size({"width": 1440, "height": 1000})
            ensure_sidebar_open(page)
            page.get_by_text(label, exact=True).click()
            page.get_by_role("heading", name=heading).wait_for(timeout=30_000)
            check_widths(page, heading, WIDTHS, report, errors)
            if heading == "Candidate Explorer":
                page.set_viewport_size({"width": 390, "height": 960})
                page.wait_for_timeout(300)
                mobile_card = page.locator(".candidate-mobile").is_visible()
                if not mobile_card:
                    errors.append("Candidate Explorer mobile card is not visible at 390px.")
                reset_scroll(page)
                page.screenshot(path=str(gallery / "candidate-390.png"), full_page=True, animations="disabled")
            if heading == "Planet Recovery Lab":
                action = page.get_by_role("button", name="Inject & recover")
                try:
                    action.wait_for(state="visible", timeout=30_000)
                except Exception:
                    errors.append("Planet Recovery Lab did not expose its injection/recovery action.")
            if heading == "Model Performance" and not page.get_by_text("catalogue benchmark", exact=False).is_visible():
                errors.append("Model Performance benchmark provenance is not visible.")
            if heading == "Research & Methods" and not page.get_by_text("Simple guide", exact=False).is_visible():
                errors.append("Research & Methods simple guide is unavailable.")
        context.close()
        browser.close()
    (gallery / "viewport_report.json").write_text(json.dumps({"widths_tested": WIDTHS, "checks": report, "browser_errors": errors}, indent=2), encoding="utf-8")
    print(json.dumps({"screenshots": len(list(gallery.glob("*.png"))), "charts_rendered": chart_count, "checks": report, "errors": errors}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
