"""GUI 截图：访问 http://127.0.0.1:8000/ 并截 5 个视图。"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    page = ctx.new_page()

    page.goto("http://127.0.0.1:8000/")
    page.wait_for_load_state("networkidle")
    time.sleep(1.2)

    page.screenshot(path="/tmp/gui-timeline.png", full_page=False)
    print("ok timeline")

    page.click('[data-view="programs"]')
    time.sleep(0.6)
    page.screenshot(path="/tmp/gui-programs.png", full_page=False)
    print("ok programs")

    page.click('[data-view="sources"]')
    time.sleep(0.6)
    page.screenshot(path="/tmp/gui-sources.png", full_page=False)
    print("ok sources")

    page.click('[data-view="jobs"]')
    time.sleep(0.6)
    page.screenshot(path="/tmp/gui-jobs.png", full_page=False)
    print("ok jobs")

    page.click('[data-view="channels"]')
    time.sleep(0.6)
    page.screenshot(path="/tmp/gui-channels.png", full_page=False)
    print("ok channels")

    browser.close()
print("Done.")
