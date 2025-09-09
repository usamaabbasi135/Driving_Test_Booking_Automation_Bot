import json
import random
import time
import yaml
from pathlib import Path
from playwright.sync_api import Page

CONFIG_PATH = "config.yaml"
OUTPUT_PATH = "available_slots.json"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def random_wait(min_sec=2, max_sec=5):
    """Random wait to avoid detection"""
    time.sleep(random.uniform(min_sec, max_sec))

def search_slots(page: Page):
    """
    Iterate through test centres, scrape available slots, and save to JSON.
    """
    config = load_config()
    booking_cfg = config["booking"]
    results = {}

    for centre in booking_cfg["centres"]:
        print(f"🔎 Checking slots at {centre}...")

        # Navigate to booking page fresh each time
        page.goto(config["urls"]["booking_page"])
        page.wait_for_load_state("networkidle")

        # Example interactions (selectors need to be updated with client access):
        page.select_option("select#category", booking_cfg["category"])
        page.click("input#no-instructor")  # selecting 'no instructor'
        page.fill("input#test-centre", centre)
        page.keyboard.press("Enter")

        page.wait_for_load_state("networkidle")
        random_wait()

        # Scrape slots (replace selector with real one)
        slots = page.locator(".slot-availability").all_text_contents()

        results[centre] = slots if slots else ["No slots available"]

        print(f"✅ {centre}: {results[centre]}")

        # Anti-bot delay
        random_wait(3, 7)

    # Save results to JSON
    Path(OUTPUT_PATH).write_text(json.dumps(results, indent=2))
    print(f"📂 Saved results to {OUTPUT_PATH}")

    return results
