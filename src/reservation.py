from playwright.sync_api import Page
import asyncio
from src.discord_notification import extract_booking_details, send_discord_notification, handle_booking_success

async def instant_reserve(page: Page):
    """
    Attempts to reserve a slot by directly firing the HTTP request instead of clicking.
    
    This is an alternative reservation method that bypasses the UI click and directly
    sends the reservation request. This can be faster than clicking, but is not always
    reliable as some websites require actual UI interactions.
    
    Args:
        page: Playwright page object
        
    Returns:
        bool: True if reservation request was successful, False otherwise
    """
    try:
        # Find the first Reserve link or button on the page
        reserve_locator = page.locator("a:has-text('Reserve'), input[value*='Reserve']")
        href = await reserve_locator.first.get_attribute("href")

        if href:
            print(f"Direct reserve attempt -> {href}")
            
            # Fire the HTTP request directly instead of clicking the button
            response = await page.request.get(href)
            print("Reserve request fired, status:", response.status)

            if response.status == 200:
                return True
            else:
                print("Reserve request failed, status:", response.status)
                return False

        print("No reserve link found on page")
        return False

    except Exception as e:
        print("Error in instant_reserve:", e)
        return False

async def return_to_search_results(page: Page):
    """
    Returns to the slot search results page and rewinds to the current week.
    
    After an unsuccessful reservation attempt or when no slots are found,
    this function navigates back to the search results view and ensures
    the calendar is showing the current week (not a future week).
    
    Args:
        page: Playwright page object
        
    Returns:
        str: "RETURNED_TO_SEARCH" on success, "ERROR" on failure
    """
    try:
        print("Clicking 'Return to search results'...")
        
        return_button = "a:has-text('Return to search results')"
        await page.click(return_button)
        await asyncio.sleep(2)
        
        print("Returned to search results")
        
        # Rewind calendar back to current week by clicking "previous week" repeatedly
        # This ensures we're searching in the correct time period
        print("Going back to current week...")
        while True:
            try:
                previous_button = await page.locator("a#searchForWeeklySlotsPreviousWeek").count()
                if previous_button == 0:
                    break
                
                await page.click("a#searchForWeeklySlotsPreviousWeek")
                await asyncio.sleep(0.5)
                
            except:
                break
        
        print("Reached current week")
        return "RETURNED_TO_SEARCH"
        
    except Exception as e:
        print(f"Error returning to search results: {e}")
        return "ERROR"

async def handle_reservation_page(page: Page, discord_webhook: str = None):
    """
    Handles the reservation page that appears after clicking an available slot.
    
    When a green calendar box is clicked, the page shows available time slots
    for that day. This function finds and clicks all "Reserve" buttons to
    attempt to reserve slots, then sends Discord notifications if successful.
    
    Args:
        page: Playwright page object on the reservation page
        discord_webhook: Discord webhook URL for sending booking notifications
        
    Returns:
        str: "RESERVATIONS_MADE" if successful, or result from return_to_search_results()
    """
    try:
        print("Checking reservation page for available slots...")
        
        # Look for all reserve buttons on the page (there may be multiple time slots)
        all_reserve_buttons = await page.locator("a:has-text('Reserve'), input[value*='Reserve']").all()
        
        if all_reserve_buttons:
            print(f"Found {len(all_reserve_buttons)} reserve elements - clicking all!")
            
            # Click all reserve buttons as quickly as possible
            reserved_count = 0
            for i, button in enumerate(all_reserve_buttons, 1):
                try:
                    await button.click()
                    reserved_count += 1
                except:
                    continue
            
            if reserved_count > 0:
                print(f"SUCCESS! Reserved {reserved_count} slots!")
                
                # Send Discord notification with booking details
                if discord_webhook:
                    await handle_booking_success(page, discord_webhook)
                
                return "RESERVATIONS_MADE"
            else:
                print("Could not reserve any slots")
                return await return_to_search_results(page)
        
        # If no reserve buttons found, return to search
        print("No reserve buttons found - returning to search")
        return await return_to_search_results(page)
        
    except Exception as e:
        print(f"Error handling reservation page: {e}")
        return await return_to_search_results(page)

async def handle_successful_reservation_and_continue(page, discord_webhook: str):
    """
    Handles a successful reservation by sending notifications and continuing the search.
    
    After successfully reserving a slot, this function:
    1. Extracts booking details from the page
    2. Sends a Discord notification with the booking information
    3. Clicks the button to continue searching for additional slots
    4. Returns to the search results to continue the automation
    
    This allows the bot to make multiple bookings in a single session.
    
    Args:
        page: Playwright page object on the reservation confirmation page
        discord_webhook: Discord webhook URL for sending notifications
        
    Returns:
        str: "CONTINUE_SEARCH" if successfully continued, "SEARCH_COMPLETED" otherwise
    """
    print("Reservation successful! Sending notification and continuing search...")
    
    # Extract booking details and send Discord notification
    booking_details = await extract_booking_details(page)
    notification_sent = await send_discord_notification(discord_webhook, booking_details, page.url)
    
    if notification_sent:
        print("Discord notification sent!")
    
    # Click "Yes, add another test" button to continue searching for more slots
    try:
        add_another_button = await page.locator("a#submitDismissReservedSlotMessage").count()
        if add_another_button > 0:
            await page.click("a#submitDismissReservedSlotMessage")
            print("Clicked 'Yes, add another test' - continuing search...")
            await asyncio.sleep(2)
            return "CONTINUE_SEARCH"
        else:
            # Alternative: click "Return to search results" if the other button isn't available
            return_button = await page.locator("a:has-text('Return to search results')").count()
            if return_button > 0:
                await page.click("a:has-text('Return to search results')")
                print("Clicked 'Return to search results' - continuing search...")
                await asyncio.sleep(2)
                return "CONTINUE_SEARCH"
    except Exception as e:
        print(f"Error continuing search: {e}")
    
    return "SEARCH_COMPLETED"

async def verify_booking_success(page: Page):
    """
    Verifies that a booking was actually successful by checking for confirmation elements.
    
    After clicking a reserve button, this function checks multiple indicators
    to confirm the booking was successful:
    - Countdown timer (appears when a slot is reserved)
    - Reserved tests table (shows booked slots in sidebar)
    - Confirmation text on the page
    
    Args:
        page: Playwright page object after reservation attempt
        
    Returns:
        bool: True if booking confirmation is found, False otherwise
    """
    try:
        # Wait for page to fully load after clicking reserve
        await asyncio.sleep(3)
        
        # Check for countdown timer (appears when slot is successfully reserved)
        timer_element = await page.locator("#minutesToTimeout").count()
        if timer_element > 0:
            print("Countdown timer found - booking confirmed")
            return True
        
        # Check for reserved tests table with actual booking entry
        reserved_test = await page.locator("td[headers='dateTime']").count()
        if reserved_test > 0:
            print("Reserved test found in sidebar - booking confirmed")
            return True
        
        # Check for booking confirmation message text
        confirmation_text = await page.locator("text=reserved").count()
        if confirmation_text > 0:
            print("Reservation confirmation text found")
            return True
        
        print("No booking confirmation found")
        return False
        
    except Exception as e:
        print(f"Error verifying booking: {e}")
        return False