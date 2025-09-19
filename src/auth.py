import asyncio
import random
import subprocess
import time
import yaml
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

CONFIG_PATH = "config.yaml"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE_PATH = r"C:\chrome-profile"

PROFILE_PATH_NEW = r"C:\chrome-profile-new"  # Add new profile path

# Change these at the top of your file
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PROFILE_PATH_2 = r"C:\edge-profile"  # Use different profile path for Edge

async def human_wait(min_sec=2, max_sec=5):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def launch_chrome():
    """Launch Chrome with remote debugging enabled"""
    print("🚀 Launching Chrome with remote debugging...")
    cmd = [
        CHROME_PATH,
        "--remote-debugging-port=9222",
        f"--user-data-dir={PROFILE_PATH}"
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

def launch_edge():
    """Launch Edge with remote debugging enabled"""
    print("🚀 Launching Edge with remote debugging...")
    cmd = [
        EDGE_PATH,
        "--remote-debugging-port=9222",
        f"--user-data-dir={PROFILE_PATH_2}"
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

# Add this function after your other helper functions
async def handle_already_signed_in_page(page):
    """Handle the 'You are already signed in' page"""
    try:
        already_signed_in = await page.locator("h1:has-text('You are already signed in')").count()
        
        if already_signed_in > 0:
            print("📋 Handling 'You are already signed in' page...")
            await page.click("input#confirm-Stay")
            print("✅ Selected 'Stay signed in'")
            await page.click("button#continue")
            print("✅ Clicked Continue")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error handling signed in page: {e}")
        return False

async def start_now_and_login():
    """Login flow + open booking form in new tab"""
    config = load_config()
    launch_chrome()

    stealth = Stealth()
    p = await stealth.use_async(async_playwright()).__aenter__()
    print("🔗 Connecting to launched Chrome...")
    browser = await p.chromium.connect_over_cdp("http://localhost:9222")

    # Attach to most recent context
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = context.pages[-1] if context.pages else await context.new_page()

    # Step 1: GOV.UK booking page
    await page.goto("https://www.gov.uk/book-pupil-driving-test")
    for y in range(0, 1500, 400):
        await page.mouse.wheel(0, y)
        await human_wait(1, 2)

    # Step 2: Click Start now
    await page.wait_for_selector("a.govuk-button", timeout=15000)
    await human_wait(2, 4)
    await page.click("a.govuk-button")

    # Step 3: Government Gateway login
    await page.wait_for_selector("input[name='user_id']", timeout=20000)

    # Detect prefilled values
    user_value = await page.eval_on_selector("input[name='user_id']", "el => el.value")
    pass_value = await page.eval_on_selector("input[name='password']", "el => el.value")

    if not user_value.strip():
        print("📝 Filling username...")
        await page.click("input[name='user_id']")  # Focus the field
        await page.keyboard.press("Control+a")     # Select all
        await page.keyboard.press("Delete")        # Clear
        for char in config["credentials"]["user_id"]:
            await page.type("input[name='user_id']", char, delay=random.randint(120, 280))
        await human_wait(1, 2)

    if not pass_value.strip():
        print("📝 Filling password...")
        await page.click("input[name='password']")
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Delete")
        for char in config["credentials"]["password"]:
            await page.type("input[name='password']", char, delay=random.randint(120, 280))
        await human_wait(1, 2)

    # Submit login
    await page.click("button[type='submit']")
    await page.wait_for_load_state("networkidle")
    await human_wait(5, 8)

    print("📍 Active URL after login:", page.url)

    # Step 4: Open booking form in NEW TAB
    print("🆕 Opening booking form in new tab...")
    booking_url = "https://driver-services.dvsa.gov.uk/obs-web/pages/home"
    new_page = await context.new_page()
    await new_page.goto(booking_url)
    await new_page.wait_for_load_state("domcontentloaded")

    await handle_already_signed_in_page(new_page)
    # Step 5: Confirm form exists
    try:
        await new_page.wait_for_selector("form#slotSearchCommand", timeout=20000)
        print("✅ Booking form detected in new tab")
    except Exception as e:
        print(f"⚠️ Booking form not detected: {e}")

    return browser, context, new_page,p
