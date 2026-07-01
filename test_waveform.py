"""Browser tests for waveform editor behavior."""
import json
import sys
import time

from playwright.sync_api import sync_playwright


URL = "http://127.0.0.1:8082/recordings/1"
ERRORS: list[str] = []
LOGS: list[str] = []


def run() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        page.on("console", lambda msg: LOGS.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: ERRORS.append(f"pageerror: {err}"))

        page.goto(URL, wait_until="networkidle", timeout=30000)

        # Wait for waveform ready (status hidden, duration shown)
        page.wait_for_function(
            """() => {
                const t = document.querySelector('#time-display')?.textContent || '';
                return t.includes('/') && !t.startsWith('0:00.000 / 0:00.000');
            }""",
            timeout=30000,
        )
        time_display = page.locator("#time-display").inner_text()
        print(f"OK  time display: {time_display}")

        # Wave should be wider than viewport when zoomed (scrollable)
        wave_width = page.evaluate("() => document.querySelector('#waveform')?.scrollWidth || 0")
        viewport = page.viewport_size["width"]
        print(f"INFO waveform scrollWidth: {wave_width}px (viewport {viewport}px)")
        if wave_width > viewport:
            print("OK  waveform is horizontally scrollable/zoomed")
        else:
            print("WARN waveform fits viewport — may be hard to edit long files")

        # Zoom in
        page.click("#btn-zoom-in")
        page.wait_for_timeout(200)
        zoom_label = page.locator("#zoom-label").inner_text()
        wave_width2 = page.evaluate("() => document.querySelector('#waveform')?.scrollWidth || 0")
        print(f"OK  zoom in -> {zoom_label}, width {wave_width2}px")

        region_count = page.locator('#waveform [part*="region"]').count()
        print(f"INFO region elements in DOM: {region_count}")

        # Navigation + chunk play
        page.click("#btn-prev-seg")
        page.wait_for_timeout(200)
        nav = page.locator("#seg-nav-label").inner_text()
        print(f"OK  segment nav -> {nav}")

        page.select_option("#playback-speed", "0.75")
        page.click("#btn-play-chunk")
        page.wait_for_timeout(600)
        chunk_label = page.locator("#btn-play-chunk").inner_text()
        print(f"OK  chunk play -> {chunk_label}")

        page.click("#btn-play")
        page.wait_for_timeout(300)
        play_label = page.locator("#btn-play").inner_text()
        print(f"OK  play all -> {play_label}")

        # Click first segment in list
        seg_items = page.locator("#segment-list li[data-id]")
        seg_count = seg_items.count()
        print(f"INFO segment list items: {seg_count}")
        if seg_count:
            first_id = seg_items.first.get_attribute("data-id")
            seg_items.first.click()
            page.wait_for_timeout(300)
            panel_hidden = page.locator("#editor-panel").is_hidden()
            start_val = page.locator("#seg-start").input_value()
            print(f"OK  click segment {first_id}: panel open={not panel_hidden}, start={start_val}")

        # Check for JS errors
        if ERRORS:
            print("FAIL JS errors:")
            for e in ERRORS:
                print(" ", e)
        else:
            print("OK  no JS page errors")

        err_logs = [l for l in LOGS if l.startswith("[error]")]
        if err_logs:
            print("WARN console errors:")
            for l in err_logs[:10]:
                print(" ", l)

        browser.close()

    return 1 if ERRORS else 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except Exception as exc:
        print(f"FAIL test exception: {exc}")
        sys.exit(2)