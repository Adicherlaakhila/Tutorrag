"""Capture genuine TutorRAG UI screenshots with Playwright."""

from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "screenshots"
ARTIFACTS = Path("/opt/cursor/artifacts")
BASE = "http://127.0.0.1:8501"


def save(page, name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    page.screenshot(path=str(path), full_page=True)
    artifact = ARTIFACTS / name
    artifact.write_bytes(path.read_bytes())
    print(f"Saved {path}")
    return path


def fill_nickname(page, value: str) -> None:
    box = page.locator('input[aria-label="Nickname *"]').first
    if box.count() == 0:
        box = page.locator("section[data-testid='stSidebar'] input").first
    box.wait_for(timeout=15000)
    box.click()
    box.fill("")
    box.type(value, delay=40)
    box.press("Tab")
    time.sleep(0.5)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_selector("text=TutorRAG", timeout=30000)
        time.sleep(1.5)

        fill_nickname(page, "Alex")
        save(page, "01_learner_profile_form.png")

        page.get_by_role("button", name="Save profile").click()
        page.wait_for_selector("text=Active profile", timeout=20000)
        time.sleep(1)
        save(page, "02_home_with_integrity_notice.png")

        # Out-of-syllabus chat
        chat = page.get_by_placeholder("Type your Science doubt here…")
        chat.click()
        chat.fill("Explain the complete process of human digestion in the stomach.")
        chat.press("Enter")
        page.wait_for_selector("text=outside", timeout=30000)
        time.sleep(1.2)
        save(page, "05_out_of_syllabus_handling.png")

        # Practice quiz
        page.get_by_role("tab", name="Practice Quiz").click()
        time.sleep(1)
        page.get_by_role("button", name="Generate 5-question quiz").click()
        page.wait_for_selector("text=Submit quiz", timeout=20000)
        time.sleep(1)

        groups = page.locator('div[role="radiogroup"]')
        for i in range(groups.count()):
            labels = groups.nth(i).locator("label")
            target = 1 if i % 2 else 0
            if labels.count() > target:
                labels.nth(target).click(force=True)
            time.sleep(0.25)

        page.get_by_role("button", name="Submit quiz").click()
        page.wait_for_selector("text=Score:", timeout=30000)
        # Scroll score into view for a clearer screenshot
        page.locator("text=Score:").first.scroll_into_view_if_needed()
        time.sleep(1)
        save(page, "04_practice_quiz_feedback.png")

        # Mobile view of chat
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_role("tab", name="Doubt Chat").click()
        time.sleep(1)
        save(page, "06_mobile_responsive_view.png")

        browser.close()
        print("Done")


if __name__ == "__main__":
    main()
