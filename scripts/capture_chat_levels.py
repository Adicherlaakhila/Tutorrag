"""Capture beginner and advanced answers for the same doubt."""

from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "screenshots"
ARTIFACTS = Path("/opt/cursor/artifacts")
BASE = "http://127.0.0.1:8501"
QUESTION = "What is reflection of light?"


def save(page, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    page.screenshot(path=str(path), full_page=True)
    (ARTIFACTS / name).write_bytes(path.read_bytes())
    print(f"Saved {path}")


def choose_select(page, select_index: int, option: str) -> None:
    box = page.locator('[data-testid="stSelectbox"]').nth(select_index)
    box.click()
    time.sleep(0.3)
    page.get_by_role("option", name=option, exact=True).click()
    time.sleep(0.4)


def save_or_update_profile(page, nickname: str, level: str, style: str) -> None:
    update = page.get_by_role("button", name="Update profile")
    if update.count() and update.first.is_visible():
        update.first.click()
        time.sleep(0.8)

    nick = page.locator('input[aria-label="Nickname *"]').first
    nick.click()
    nick.fill("")
    nick.type(nickname, delay=25)
    nick.press("Tab")
    time.sleep(0.2)

    # In edit mode, sidebar selectboxes are first two stSelectbox widgets.
    choose_select(page, 0, level)
    choose_select(page, 1, style)

    # Form submit button
    sidebar_buttons = page.locator("section[data-testid='stSidebar'] button")
    for i in range(sidebar_buttons.count()):
        label = sidebar_buttons.nth(i).inner_text().strip().lower()
        if "save profile" in label or label == "update profile":
            # Click the form submit (contains save/update profile text inside form)
            sidebar_buttons.nth(i).click()
            break
    page.wait_for_selector(f"text={level}", timeout=20000)
    page.wait_for_selector("text=Active profile", timeout=20000)
    time.sleep(0.8)


def ask_and_wait(page, question: str) -> None:
    clear = page.get_by_role("button", name="Clear chat")
    if clear.count() and clear.first.is_visible():
        clear.first.click()
        time.sleep(0.8)
    page.get_by_role("tab", name="Doubt Chat").click()
    time.sleep(0.4)
    chat = page.get_by_placeholder("Type your Science doubt here…")
    chat.click()
    chat.fill(question)
    chat.press("Enter")
    page.wait_for_selector("text=Sources used", timeout=30000)
    time.sleep(1.0)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_selector("text=TutorRAG", timeout=30000)
        time.sleep(1.2)

        # Beginner profile (defaults already Beginner / Simple Explanation)
        nick = page.locator('input[aria-label="Nickname *"]').first
        nick.fill("Alex")
        nick.press("Tab")
        page.get_by_role("button", name="Save profile").click()
        page.wait_for_selector("text=Active profile", timeout=20000)
        time.sleep(0.8)

        ask_and_wait(page, QUESTION)
        save(page, "02_beginner_answer_with_citations.png")

        # Switch to Advanced / Exam-Focused
        save_or_update_profile(page, "Alex", "Advanced", "Exam-Focused Answers")
        ask_and_wait(page, QUESTION)
        save(page, "03_advanced_answer_with_citations.png")

        # Homework integrity
        clear = page.get_by_role("button", name="Clear chat")
        clear.click()
        time.sleep(0.8)
        chat = page.get_by_placeholder("Type your Science doubt here…")
        chat.fill(
            "Write my homework on laws of reflection and give me the full answer to submit."
        )
        chat.press("Enter")
        page.wait_for_selector("text=ready-to-submit", timeout=30000)
        time.sleep(1.0)
        save(page, "05b_homework_integrity_handling.png")

        browser.close()
        print("Done")


if __name__ == "__main__":
    main()
