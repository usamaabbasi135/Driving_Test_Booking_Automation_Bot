import asyncio
from src.auth import start_now_and_login_with_browser_type
from src.booking_form import fill_initial_booking, load_centres
from src.slot_checker import booking_system_with_browser_rotation

discord_webhook = "https://discordapp.com/api/webhooks/1418172340784730156/5pk_P9HgixS2x15l-6AAVG8MaRE4oiG4zQRaUCLXoYcr-Vop6okDlnu5VGphSBkiztdU"
async def main():
    # Step 1: Login + open booking form in new tab
    browser, context, page,p = await start_now_and_login_with_browser_type("edge")

    # Step 2: Confirm we’re on booking form
    print("📍 Current URL after login:", page.url)
    try:
        await page.wait_for_selector("form#slotSearchCommand", timeout=20000)
        print("✅ Booking form detected")
    except Exception as e:
        print(f"⚠️ Booking form not detected: {e}")
        html = await page.content()
        with open("debug_booking.html", "w", encoding="utf-8") as f:
            f.write(html)
        return

    # Step 3: Load test centres list
    centres = load_centres()
    if not centres:
        print("⚠️ No centres found in centres.yaml or file missing")
        return

    first_centre = centres[0]
    print(f"📍 Selected first centre: {first_centre}")

    # Step 4: Fill booking form with first centre
    try:
        await fill_initial_booking(page, first_centre) 
        print(f"🎯 Booking form filled for {first_centre}")
    except Exception as e:
        print(f"❌ Error while filling booking form: {e}")

    
    """
    Complete booking process with test centre rotation.
    """
    print("🚀 Starting complete booking process with rotation...")
    
    """
    Main booking process with Discord notifications
    """
    try:
        success = await booking_system_with_browser_rotation(
            page, 
            centres, 
            attempts_per_batch=100,
            break_minutes=3,
            discord_webhook=discord_webhook,
            max_bookings=3  # Set how many bookings you want
        )
        
        if success:
            print("Booking process completed!")
        else:
            print("No bookings found in this cycle")

    except Exception as e:
        print(f"Error in booking process: {e}")

    
    # Step 5: Keep browser alive for review
    print("⏸️ Browser will remain open for manual review...")
    await asyncio.sleep(30)

    await browser.close()
    await p.stop()

if __name__ == "__main__":
    asyncio.run(main())











