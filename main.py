import asyncio
from src.auth import start_now_and_login_with_browser_type
from src.booking_form import fill_initial_booking, load_centres
from src.slot_checker import booking_system_with_browser_rotation
from config import BROWSER_TYPE, DISCORD_WEBHOOK

# Discord webhook URL for sending booking notifications
discord_webhook = DISCORD_WEBHOOK

async def main():
    """
    Main automation function that orchestrates the entire driving test booking process.
    
    This function:
    1. Authenticates with the DVSA booking system
    2. Loads and configures test centres
    3. Fills the initial booking form
    4. Continuously searches for available test slots
    5. Automatically reserves slots when found
    6. Sends notifications via Discord when bookings are successful
    """
    
    # Step 1: Initialize browser session and authenticate with DVSA system
    # This launches the browser, navigates to the booking portal, and logs in using saved credentials
    browser, context, page, p = await start_now_and_login_with_browser_type(BROWSER_TYPE)

    # Step 2: Verify that we successfully reached the booking form page
    # The booking form is identified by the selector "form#slotSearchCommand"
    print("Current URL after login:", page.url)
    try:
        await page.wait_for_selector("form#slotSearchCommand", timeout=20000)
        print("Booking form detected")
    except Exception as e:
        # If form not found, save page HTML for debugging purposes
        print(f"Booking form not detected: {e}")
        html = await page.content()
        with open("debug_booking.html", "w", encoding="utf-8") as f:
            f.write(html)
        return

    # Step 3: Load the list of test centres from the configuration file
    # These centres define where the bot will search for available test slots
    centres = load_centres()
    if not centres:
        print("No centres found in centres.yaml or file missing")
        return

    # Use the first centre from the list for the initial booking form submission
    first_centre = centres[0]
    print(f"Selected first centre: {first_centre}")

    # Step 4: Fill the initial booking form with the first test centre
    # This sets up the search criteria: car category, test centre, no instructor, no special needs
    try:
        await fill_initial_booking(page, first_centre) 
        print(f"Booking form filled for {first_centre}")
    except Exception as e:
        print(f"Error while filling booking form: {e}")

    # Step 5: Start the automated slot searching and booking process
    # This function continuously searches for available slots across all configured test centres
    # It rotates between browsers every 15 minutes to avoid detection
    # It processes centres in batches and takes breaks between cycles
    print("Starting complete booking process with rotation...")
    
    try:
        success = await booking_system_with_browser_rotation(
            page, 
            centres, 
            attempts_per_batch=100,  # Number of search attempts before moving to next centre batch
            break_minutes=3,          # Minutes to wait between complete cycles through all centres
            discord_webhook=discord_webhook,  # Webhook URL for sending booking notifications
            max_bookings=3,           # Maximum number of bookings to make before stopping
            initial_browser=BROWSER_TYPE  # Starting browser type (chrome or edge)
        )
        
        if success:
            print("Booking process completed!")
        else:
            print("No bookings found in this cycle")

    except Exception as e:
        print(f"Error in booking process: {e}")

    # Step 6: Keep browser session open briefly for manual review if needed
    # This allows the user to verify bookings or check the final state
    print("Browser will remain open for manual review...")
    await asyncio.sleep(30)

    # Clean up: Close browser and stop Playwright process
    await browser.close()
    await p.stop()

if __name__ == "__main__":
    asyncio.run(main())











