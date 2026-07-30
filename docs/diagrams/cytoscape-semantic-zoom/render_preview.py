from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent


def main() -> None:
    html = (ROOT / "tusk-cytoscape-architecture.html").resolve().as_uri()
    output = ROOT / "tusk-arch-agent-orchestrator.png"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1)
        page.goto(html, wait_until="load")
        page.wait_for_selector("#search")
        page.fill("#search", "AgentOrchestrator")
        page.press("#search", "Enter")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(output), full_page=False)
        browser.close()

    print(f"wrote {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
