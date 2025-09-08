import yaml
import os
from playwright.sync_api import sync_playwright

CONFIG_PATH = "config.yaml"
COOKIES_PATH = "cookies.json"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def save_cookies(context):
    context.storage_state(path=COOKIES_PATH)

def load_cookies(playwright, browser):
    if os.path.exists(COOKIES_PATH):
        return browser.new_context(storage_state=COOKIES_PATH)
    else:
        return browser.new_context()

def login_and_navigate():
    config = load_config()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = load_cookies(p, browser)
        page = context.new_page()

        # Go to login
        page.goto(config["urls"]["login_page"])

        # If already logged in (cookies worked), just return
        if "Book a driving test" in page.content():
            print("✅ Already logged in with cookies")
            return page, context

        # Perform login
        page.fill("input[name='username']", config["credentials"]["username"])
        page.fill("input[name='password']", config["credentials"]["password"])
        page.click("button[type='submit']")

        # Wait for navigation
        page.wait_for_load_state("networkidle")

        # Navigate to booking page
        page.goto(config["urls"]["booking_page"])
        page.wait_for_load_state("networkidle")

        # Save cookies
        save_cookies(context)

        print("✅ Login & navigation successful")
        return page, context
