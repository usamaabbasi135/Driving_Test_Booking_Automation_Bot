import asyncio
from playwright.async_api import Page
from src.reservation import handle_reservation_page,handle_successful_reservation_and_continue,instant_reserve,verify_booking_success
from src.discord_notification import handle_booking_success
from src.browser_rotation import BrowserRotationManager
from src.auth import start_now_and_login_with_browser_type

async def booking_system_with_browser_rotation(page: Page, centres: list[str], attempts_per_batch: int = 50, 
                                              break_minutes: int = 10, discord_webhook: str = None,
                                              max_bookings: int = 5, initial_browser="edge"):
    """
    Main booking automation system with intelligent browser rotation and multi-centre search.
    
    This function implements the core booking logic:
    - Processes test centres in batches to avoid overwhelming the system
    - Automatically switches between Chrome and Edge every 15 minutes to reduce detection risk
    - Continuously searches for available slots across multiple test centres
    - Automatically reserves slots when found and sends Discord notifications
    - Takes breaks between cycles to appear more human-like
    
    Args:
        page: Initial Playwright page object (may be replaced during browser rotation)
        centres: List of test centre names to search
        attempts_per_batch: Number of search attempts per centre batch before moving on
        break_minutes: Minutes to wait between complete cycles through all centres
        discord_webhook: Discord webhook URL for sending booking notifications
        max_bookings: Maximum number of bookings to make before stopping
        initial_browser: Starting browser type ("chrome" or "edge")
        
    Returns:
        bool: True if booking process completed (regardless of number of bookings made)
    """
    browser_manager = BrowserRotationManager(initial_browser)
    total_centres = len(centres)
    batch_size = 3  # Process 3 centres at a time
    cycle_count = 1
    bookings_made = 0
    
    # Track current browser session state
    current_browser = None
    current_context = None
    current_page = page
    current_p = None
    current_batch_start = 0
    centres_added = False
    
    # Main loop: continue until maximum bookings reached
    while bookings_made < max_bookings:
        print(f"\nCYCLE {cycle_count} - Bookings made: {bookings_made}/{max_bookings}")
        
        # Process all centres in batches
        while current_batch_start < total_centres and bookings_made < max_bookings:
            # Check if 15 minutes have elapsed and browser should be rotated
            if browser_manager.should_switch_browser():
                print("15 minutes elapsed - switching browsers...")
                
                # Clean up current browser session
                if current_browser:
                    try:
                        await current_browser.close()
                        await current_p.stop()
                    except:
                        pass
                
                # Switch to the other browser type (Chrome <-> Edge)
                browser_manager.switch_browser()
                
                # Launch new browser and re-authenticate
                current_browser, current_context, current_page, current_p = await start_now_and_login_with_browser_type(browser_manager.current_browser)
                
                # Reset flag so centres are re-added in the new browser session
                centres_added = False
            
            # Calculate current batch of centres to process
            current_batch_end = min(current_batch_start + batch_size, total_centres)
            current_batch = centres[current_batch_start:current_batch_end]
            
            batch_number = (current_batch_start // batch_size) + 1
            total_batches = (total_centres + batch_size - 1) // batch_size
            print(f"\nCycle {cycle_count} - Batch {batch_number}/{total_batches}: {current_batch}")
            print(f"Using browser: {browser_manager.current_browser}")
            
            # Add test centres to the search form if not already added
            if not centres_added:
                # Clear any existing centres first
                await remove_all_test_centres(current_page)
                await asyncio.sleep(2)
                
                # Add the current batch of centres to the search form
                added_count = await add_test_centres_sequential(current_page, current_batch)
                if added_count == 0:
                    # If no centres could be added, skip to next batch
                    current_batch_start += batch_size
                    continue
                
                centres_added = True
            
            # Search for available slots with the current batch of centres
            slot_found = await search_for_available_slots(current_page, max_attempts=attempts_per_batch, discord_webhook=discord_webhook)
            
            if slot_found:
                bookings_made += 1
                print(f"BOOKING #{bookings_made} SUCCESSFUL on {browser_manager.current_browser}!")
                
                # Handle the successful reservation and continue searching
                result = await handle_successful_reservation_and_continue(current_page, discord_webhook)
                
                if result == "CONTINUE_SEARCH":
                    print(f"Continuing to search for booking #{bookings_made + 1}...")
                    continue
                else:
                    return True
            
            # Move to next batch of centres
            current_batch_start += batch_size
            centres_added = False  # Reset for next batch
        
        # If we haven't reached max bookings, take a break before next cycle
        if bookings_made < max_bookings:
            print(f"\nCycle {cycle_count} completed - {bookings_made} bookings made")
            print(f"Waiting {break_minutes} minutes before next cycle...")
            
            # Countdown timer during break period
            for remaining in range(break_minutes * 60, 0, -60):
                minutes_left = remaining // 60
                print(f"Next cycle in {minutes_left} minute(s)...")
                await asyncio.sleep(60)
                
                # Check if browser should be rotated during the break period
                if browser_manager.should_switch_browser():
                    print("Browser switch time during break...")
                    
                    if current_browser:
                        try:
                            await current_browser.close()
                            await current_p.stop()
                        except:
                            pass
                    
                    browser_manager.switch_browser()
                    current_browser, current_context, current_page, current_p = await start_now_and_login_with_browser_type(browser_manager.current_browser)
            
            cycle_count += 1
            current_batch_start = 0  # Reset for next cycle
    
    print(f"MAXIMUM BOOKINGS REACHED: {bookings_made} slots reserved!")
    
    # Clean up final browser session
    if current_browser:
        try:
            await current_browser.close()
            await current_p.stop()
        except:
            pass
    
    return True


async def add_test_centres_sequential(page: Page, centres: list[str], max_to_add: int = 3):
    """
    Adds multiple test centres to the booking form one by one.
    
    The DVSA booking system allows searching multiple test centres simultaneously.
    This function adds centres sequentially, waiting for the form to update after
    each addition to ensure proper synchronization with the website.
    
    Args:
        page: Playwright page object
        centres: List of test centre names to add
        max_to_add: Maximum number of centres to add (default 3)
        
    Returns:
        int: Number of centres successfully added
    """
    added_count = 0
    
    for centre in centres[:max_to_add]:
        try:
            print(f"Adding test centre {added_count + 1}/{max_to_add}: {centre}")
            
            # Step 1: Focus and clear the autocomplete input field
            autocomplete_input = "input#auto-add_testcentre"
            await page.focus(autocomplete_input)
            await page.fill(autocomplete_input, "")
            
            # Step 2: Type the centre name character by character with delay
            # This simulates human typing and helps trigger autocomplete suggestions
            await page.type(autocomplete_input, centre, delay=50)
            await asyncio.sleep(1)
            
            # Step 3: Try to select the centre directly from dropdown
            try:
                await page.select_option("select#add_testcentre", label=centre)
                print(f"Direct selection successful for: {centre}")
            except:
                # Step 4: Alternative method - use keyboard navigation if direct selection fails
                await page.press(autocomplete_input, "Tab")
                await asyncio.sleep(0.5)
            
            # Step 5: Click the submit button to add the centre
            await page.click("input#submitAddAdditionalTestCentre")
            print(f"Clicked submit for: {centre}")
            
            # Step 6: Wait for the page to fully update after adding the centre
            # This is critical - the form needs time to process the addition
            await asyncio.sleep(3)
            
            # Step 7: Verify the centre was successfully added by checking page content
            page_content = await page.content()
            if centre in page_content:
                print(f"Confirmed {centre} was added to the page")
                added_count += 1
            else:
                print(f"Could not confirm {centre} was added")
                
        except Exception as e:
            print(f"Could not add {centre}: {e}")
            continue
    
    print(f"Successfully added {added_count} test centres")
    return added_count


    
async def search_for_available_slots(page, max_attempts: int = 100, discord_webhook: str = None):
    """
    Rapidly searches for available test slots by checking calendar weeks.
    
    This function implements the core slot-finding logic:
    - Checks the current calendar view for "green boxes" (available slots)
    - If found, immediately clicks to reserve
    - If not found, moves to the next week and repeats
    - Continues until a slot is found or max attempts reached
    
    Speed is critical here because test slots are often booked within seconds
    of becoming available, so the function prioritizes speed over error handling.
    
    Args:
        page: Playwright page object on the slot search results page
        max_attempts: Maximum number of weeks to check before giving up
        discord_webhook: Not used in this function, but kept for compatibility
        
    Returns:
        bool: True if an available slot was found and clicked, False otherwise
    """
    print("Starting search for available slots...")

    for attempt in range(1, max_attempts + 1):
        try:
            print(f"Attempt {attempt}/{max_attempts}: Checking calendar...")
            
            # Check for green calendar boxes indicating available slots
            green_boxes = await check_for_green_calendar_boxes(page)

            if green_boxes:
                print("GREEN BOX FOUND! Clicking...")
                # Click the first available slot immediately
                await green_boxes[0].click()

                # Wait for reserve button to appear and click it as fast as possible
                # Speed is critical - slots can be taken in seconds
                try:
                    reserve_button = page.locator(
                        "a:has-text('Reserve'), input[value*='Reserve']"
                    ).first

                    await reserve_button.wait_for(state="visible", timeout=300)
                    await reserve_button.click(timeout=50)

                    print("RESERVE BUTTON CLICKED INSTANTLY!")

                    # Return immediately - notification will be handled by calling function
                    return True

                except Exception as e:
                    print(f"Reserve button not clickable fast enough: {e}")
                    return False

            # No green slots found in current week - move to next week
            await page.click("a#searchForWeeklySlotsNextAvailable")
            await page.wait_for_load_state("networkidle")  # Wait for page to load

        except Exception as e:
            print(f"Error in attempt {attempt}: {e}")
            continue

    return False


async def check_for_green_calendar_boxes(page: Page):
    """
    Checks the calendar view for available test slots (green boxes).
    
    The function implements a "rewind" feature:
    - If the calendar shows a week that's not in 2025, it rewinds back to the current week
    - This prevents searching in past weeks where slots are no longer valid
    - Only searches in 2025 weeks (or current year) where slots are bookable
    
    Green boxes (td.day.slotsavailable) indicate available test slots that can be reserved.
    
    Args:
        page: Playwright page object on the slot search results page
        
    Returns:
        list: List of Playwright locators for available slot elements, or empty list if none found
    """
    try:
        # Extract the week header to determine which week/year is currently displayed
        week_header = (await page.locator("div.span-7 p.centre.bold").inner_text()).strip()
        print(f"Week header: {week_header}")

        # If we're viewing a week that's not in 2025, rewind back to current week
        # This happens when the calendar navigation goes too far forward
        if "2025" not in week_header:
            print("Not a 2025 week, rewinding...")
            # Click "previous week" button repeatedly until we reach current week
            while True:
                try:
                    # Check if previous week button exists
                    if await page.locator("a#searchForWeeklySlotsPreviousWeek").count() == 0:
                        break
                    await page.click("a#searchForWeeklySlotsPreviousWeek")
                    await asyncio.sleep(0.2)
                except:
                    break
            print("Reached current week")
            return []

        # Find all green calendar boxes (available slots) in the current week
        # The selector "td.day.slotsavailable a" targets clickable available slot elements
        available_cells = await page.locator("td.day.slotsavailable a").all()
        if available_cells:
            print(f"Found {len(available_cells)} green slots in 2025")
        else:
            print("No green slots found in this week")
        return available_cells

    except Exception as e:
        print(f"Error in slot check: {e}")
        return []


async def remove_all_test_centres(page: Page):
    """
    Removes all test centres that are currently added to the booking form.
    
    This function is called when switching between batches of centres or when
    starting a new browser session. It ensures a clean slate before adding
    new centres to search.
    
    Args:
        page: Playwright page object on the booking form page
        
    Returns:
        bool: True if removal completed (or no centres to remove), False on error
    """
    try:
        print("Removing all current test centres...")
        
        # Find all remove buttons for test centres
        # The selector targets delete icons with IDs containing 'removeTestCentre_'
        remove_buttons = await page.locator("a.deleteIcon[id*='removeTestCentre_']").all()
        
        if not remove_buttons:
            print("No test centres to remove")
            return True
        
        print(f"Found {len(remove_buttons)} test centres to remove")
        
        # Click each remove button sequentially
        for i, button in enumerate(remove_buttons, 1):
            try:
                print(f"Removing test centre {i}/{len(remove_buttons)}...")
                await button.click()
                await asyncio.sleep(1)  # Wait between removals for page to update
                print(f"Removed test centre {i}")
            except Exception as e:
                print(f"Could not remove test centre {i}: {e}")
        
        print("All test centres removed successfully")
        return True
        
    except Exception as e:
        print(f"Error removing test centres: {e}")
        return False

