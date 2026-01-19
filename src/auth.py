import asyncio
import random
import subprocess
import time
import yaml
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Configuration file path containing login credentials
CONFIG_PATH = "config.yaml"

# Browser executable paths and profile directories
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE_PATH = r"C:\chrome-profile"
PROFILE_PATH_NEW = r"C:\chrome-profile-new"

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PROFILE_PATH_2 = r"C:\edge-profile"

async def human_wait(min_sec=2, max_sec=5):
    """
    Simulates human-like random delays between actions.
    
    This helps make the automation appear more natural and reduces the risk
    of being detected as a bot by the website's anti-automation systems.
    
    Args:
        min_sec: Minimum wait time in seconds
        max_sec: Maximum wait time in seconds
    """
    await asyncio.sleep(random.uniform(min_sec, max_sec))

def load_config():
    """
    Loads configuration from YAML file containing login credentials.
    
    Returns:
        dict: Configuration dictionary with credentials and other settings
    """
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def launch_chrome():
    """
    Launches Chrome browser with remote debugging enabled.
    
    Remote debugging allows Playwright to connect to an existing browser instance
    rather than launching a new one. This enables using a browser with saved
    cookies and session data, which is essential for maintaining login state.
    """
    print("Launching Chrome with remote debugging...")
    cmd = [
        CHROME_PATH,
        "--remote-debugging-port=9222",  # Port for Playwright to connect
        f"--user-data-dir={PROFILE_PATH}"  # Use specific profile to preserve cookies
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)  # Wait for browser to fully start

def launch_edge():
    """
    Launches Microsoft Edge browser with remote debugging enabled.
    
    Similar to launch_chrome(), but for Edge browser. Uses a separate profile
    directory to maintain independent session data.
    """
    print("Launching Edge with remote debugging...")
    cmd = [
        EDGE_PATH,
        "--remote-debugging-port=9222",
        f"--user-data-dir={PROFILE_PATH_2}"
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

async def handle_already_signed_in_page(page):
    """
    Handles the "You are already signed in" page that sometimes appears.
    
    When the browser profile already has an active session, the DVSA website
    may show a confirmation page asking if you want to stay signed in.
    This function automatically selects "Stay signed in" and continues.
    
    Args:
        page: Playwright page object
        
    Returns:
        bool: True if the page was handled successfully, False otherwise
    """
    try:
        already_signed_in = await page.locator("h1:has-text('You are already signed in')").count()
        
        if already_signed_in > 0:
            print("Handling 'You are already signed in' page...")
            await page.click("input#confirm-Stay")
            print("Selected 'Stay signed in'")
            await page.click("button#continue")
            print("Clicked Continue")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error handling signed in page: {e}")
        return False

async def start_now_and_login_with_browser_type(browser_type):
    """
    Complete authentication flow: launches browser, logs into DVSA system, and opens booking form.
    
    This function:
    1. Launches the specified browser (Chrome or Edge) with remote debugging
    2. Connects Playwright to the browser instance
    3. Navigates to the GOV.UK booking page and clicks "Start now"
    4. Logs in using credentials from config.yaml
    5. Opens the booking form in a new tab
    6. Handles any "already signed in" prompts
    
    Args:
        browser_type: Either "chrome" or "edge" to specify which browser to use
        
    Returns:
        tuple: (browser, context, page, playwright_instance) objects for further automation
    """
    config = load_config()
    
    # Launch the appropriate browser with remote debugging enabled
    if browser_type == "chrome":
        launch_chrome()
        print("Connecting to launched Chrome...")
    else:
        launch_edge()
        print("Connecting to launched Edge...")

    # Initialize Playwright with stealth mode to avoid detection
    # Stealth mode helps make the automation less detectable by websites
    stealth = Stealth()
    p = await stealth.use_async(async_playwright()).__aenter__()
    print("Connecting to launched browser...")
    
    # Connect to the browser via Chrome DevTools Protocol (CDP)
    # Port 9222 is the default remote debugging port
    browser = await p.chromium.connect_over_cdp("http://localhost:9222")

    # Attach to the most recent browser context (or create new one if none exists)
    # This allows us to use existing tabs and cookies
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = context.pages[-1] if context.pages else await context.new_page()

    # Step 1: Navigate to the GOV.UK driving test booking page
    await page.goto("https://www.gov.uk/book-pupil-driving-test")
    
    # Simulate human scrolling behavior to make the session appear more natural
    for y in range(0, 1500, 400):
        await page.mouse.wheel(0, y)
        await human_wait(1, 2)

    # Step 2: Click the "Start now" button to begin the booking process
    await page.wait_for_selector("a.govuk-button", timeout=15000)
    await human_wait(2, 4)
    await page.click("a.govuk-button")

    # Step 3: Handle Government Gateway login page
    await page.wait_for_selector("input[name='user_id']", timeout=20000)

    # Check if username and password fields are already prefilled (from saved session)
    user_value = await page.eval_on_selector("input[name='user_id']", "el => el.value")
    pass_value = await page.eval_on_selector("input[name='password']", "el => el.value")

    # Fill username only if field is empty
    if not user_value.strip():
        print("Filling username...")
        await page.click("input[name='user_id']")  # Focus the field
        await page.keyboard.press("Control+a")     # Select all existing text
        await page.keyboard.press("Delete")        # Clear field
        # Type username character by character with random delays to simulate human typing
        for char in config["credentials"]["user_id"]:
            await page.type("input[name='user_id']", char, delay=random.randint(120, 280))
        await human_wait(1, 2)

    # Fill password only if field is empty
    if not pass_value.strip():
        print("Filling password...")
        await page.click("input[name='password']")
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Delete")
        # Type password character by character with random delays
        for char in config["credentials"]["password"]:
            await page.type("input[name='password']", char, delay=random.randint(120, 280))
        await human_wait(1, 2)

    # Submit the login form
    await page.click("button[type='submit']")
    await page.wait_for_load_state("networkidle")
    await human_wait(5, 8)

    print("Active URL after login:", page.url)

    # Step 4: Open the booking form in a new tab
    # This keeps the login session active while working with the booking form
    print("Opening booking form in new tab...")
    booking_url = "https://driver-services.dvsa.gov.uk/obs-web/pages/home"
    new_page = await context.new_page()
    await new_page.goto(booking_url)
    await new_page.wait_for_load_state("domcontentloaded")

    # Handle any "already signed in" prompts that may appear
    await handle_already_signed_in_page(new_page)
    
    # Step 5: Verify that the booking form is loaded and accessible
    try:
        await new_page.wait_for_selector("form#slotSearchCommand", timeout=20000)
        print("Booking form detected in new tab")
    except Exception as e:
        print(f"Booking form not detected: {e}")

    return browser, context, new_page, p
