import asyncio
from playwright.async_api import Page
from src.reservation import handle_reservation_page,handle_successful_reservation_and_continue,instant_reserve,verify_booking_success
from src.discord_notification import handle_booking_success
from src.browser_rotation import BrowserRotationManager
from src.auth import start_now_and_login_with_browser_type

# Updated main booking function
async def booking_system_with_browser_rotation(page: Page, centres: list[str], attempts_per_batch: int = 50, 
                                              break_minutes: int = 10, discord_webhook: str = None,
                                              max_bookings: int = 5,initial_browser="edge"):
    """
    Booking system with automatic browser switching every 15 minutes
    """
    browser_manager = BrowserRotationManager(initial_browser)
    total_centres = len(centres)
    batch_size = 3
    cycle_count = 1
    bookings_made = 0
    
    # Current browser session variables
    current_browser = None
    current_context = None
    current_page = page
    current_p = None
    current_batch_start = 0
    centres_added = False
    
    while bookings_made < max_bookings:
        print(f"\nCYCLE {cycle_count} - Bookings made: {bookings_made}/{max_bookings}")
        
        while current_batch_start < total_centres and bookings_made < max_bookings:
            # Check if we need to switch browsers
            if browser_manager.should_switch_browser():
                print("⏰ 15 minutes elapsed - switching browsers...")
                
                # Close current browser if exists
                if current_browser:
                    try:
                        await current_browser.close()
                        await current_p.stop()
                    except:
                        pass
                
                # Switch browser type
                browser_manager.switch_browser()
                
                # Launch new browser and login
                current_browser, current_context, current_page, current_p = await start_now_and_login_with_browser_type(browser_manager.current_browser)
                
                # Reset centres flag to re-add them in new browser
                centres_added = False
            
            current_batch_end = min(current_batch_start + batch_size, total_centres)
            current_batch = centres[current_batch_start:current_batch_end]
            
            batch_number = (current_batch_start // batch_size) + 1
            total_batches = (total_centres + batch_size - 1) // batch_size
            print(f"\n🔍 Cycle {cycle_count} - Batch {batch_number}/{total_batches}: {current_batch}")
            print(f"🌐 Using browser: {browser_manager.current_browser}")
            
            # Add centres if not already added or if browser switched
            if not centres_added:
                await remove_all_test_centres(current_page)
                await asyncio.sleep(2)
                
                added_count = await add_test_centres_sequential(current_page, current_batch)
                if added_count == 0:
                    current_batch_start += batch_size
                    continue
                
                centres_added = True
            
            # Search for slots with current browser
            slot_found = await search_for_available_slots(current_page, max_attempts=attempts_per_batch, discord_webhook=discord_webhook)
            
            if slot_found:
                bookings_made += 1
                print(f"✅ BOOKING #{bookings_made} SUCCESSFUL on {browser_manager.current_browser}!")
                
                # Send notification and continue
                result = await handle_successful_reservation_and_continue(current_page, discord_webhook)
                
                if result == "CONTINUE_SEARCH":
                    print(f"🔄 Continuing to search for booking #{bookings_made + 1}...")
                    continue
                else:
                    return True
            
            current_batch_start += batch_size
            centres_added = False  # Reset for next batch
        
        if bookings_made < max_bookings:
            print(f"\n📊 Cycle {cycle_count} completed - {bookings_made} bookings made")
            print(f"⏱️ Waiting {break_minutes} minutes before next cycle...")
            
            for remaining in range(break_minutes * 60, 0, -60):
                minutes_left = remaining // 60
                print(f"Next cycle in {minutes_left} minute(s)...")
                await asyncio.sleep(60)
                
                # Check for browser switch during wait
                if browser_manager.should_switch_browser():
                    print("⏰ Browser switch time during break...")
                    
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
    
    print(f"🎉 MAXIMUM BOOKINGS REACHED: {bookings_made} slots reserved!")
    
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
    Adds test centres one by one, waiting for form update after each addition.
    """
    added_count = 0
    
    for centre in centres[:max_to_add]:
        try:
            print(f"➕ Adding test centre {added_count + 1}/{max_to_add}: {centre}")
            
            # Step 1: Focus and clear the autocomplete input
            autocomplete_input = "input#auto-add_testcentre"
            await page.focus(autocomplete_input)
            await page.fill(autocomplete_input, "")
            
            # Step 2: Type the centre name slowly
            await page.type(autocomplete_input, centre, delay=50)
            await asyncio.sleep(1)
            
            # Step 3: Try direct selection first
            try:
                await page.select_option("select#add_testcentre", label=centre)
                print(f"✅ Direct selection successful for: {centre}")
            except:
                # Step 4: Alternative - use keyboard navigation
                await page.press(autocomplete_input, "Tab")
                await asyncio.sleep(0.5)
            
            # Step 5: Click submit button
            await page.click("input#submitAddAdditionalTestCentre")
            print(f"🖱️ Clicked submit for: {centre}")
            
            # Step 6: CRITICAL - Wait for page to fully update
            await asyncio.sleep(3)
            
            # Step 7: Verify the centre was added by checking if it appears in the page
            # Look for the centre name in the page content or added centres list
            page_content = await page.content()
            if centre in page_content:
                print(f"✅ Confirmed {centre} was added to the page")
                added_count += 1
            else:
                print(f"⚠️ Could not confirm {centre} was added")
                
        except Exception as e:
            print(f"❌ Could not add {centre}: {e}")
            continue
    
    print(f"📋 Successfully added {added_count} test centres")
    return added_count


    
async def search_for_available_slots(page, max_attempts: int = 100, discord_webhook: str = None):
    """Updated search function with Discord notifications and verification"""
    print("🔍 Starting search for available slots...")
    
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"🔄 Attempt {attempt}/{max_attempts}: Checking calendar...")
            green_boxes = await check_for_green_calendar_boxes(page)
            
            if green_boxes:
                print("🎯 GREEN BOX FOUND! Clicking...")
                await green_boxes[0].click()
                await asyncio.sleep(0.5)  # Wait longer for page to load
                
                # Try instant reserve first
                if await instant_reserve(page):
                    print("🚀 RESERVE BUTTON CLICKED!")
                    
                    # Wait for page to update after reservation
                    await asyncio.sleep(1)  # Just 1 second for page to update
                    if discord_webhook:
                        success = await handle_booking_success(page, discord_webhook)
                        if success:
                            print("✅ Notification sent for confirmed booking")
                            return True
                        else:
                            print("⚠️ No notification sent - booking not confirmed")
                
                # Fallback to handle_reservation_page
                result = await handle_reservation_page(page, discord_webhook)
                if result == "RESERVATIONS_MADE":
                    return True
                elif result == "RETURNED_TO_SEARCH":
                    continue
                else:
                    break
            
            # Continue searching
            await page.click("a#searchForWeeklySlotsNextAvailable")
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Error in attempt {attempt}: {e}")
            continue
    
    return False

async def check_for_green_calendar_boxes(page: Page):
    """
    Generic function to find available slots (green boxes) without hardcoding IDs.
    """
    try:
        # Method 1: Look for table cells with "slotsavailable" class (the green boxes)
        available_cells = await page.locator("td.day.slotsavailable").all()
        
        if available_cells:
            print(f"Found {len(available_cells)} green boxes (slotsavailable)")
            # Get the clickable links inside these cells
            available_links = []
            for cell in available_cells:
                links = await cell.locator("a").all()
                available_links.extend(links)
            return available_links
        
        # Method 2: Look for links that contain "view" text (available slots show "view")
        view_links = await page.locator("td.day a:has-text('view')").all()
        if view_links:
            print(f"Found {len(view_links)} 'view' links in calendar")
            return view_links
        
        # Method 3: Look for calendar day cells that don't have "none" class
        non_empty_cells = await page.locator("td.day:not(.none):not(.nonenonotif) a").all()
        if non_empty_cells:
            print(f"Found {len(non_empty_cells)} non-empty calendar cells")
            return non_empty_cells
            
        return []
        
    except Exception as e:
        print(f"Error checking for green boxes: {e}")
        return []

async def remove_all_test_centres(page: Page):
    """
    Removes all currently added test centres by clicking the remove buttons.
    """
    try:
        print("🗑️ Removing all current test centres...")
        
        # Find all remove buttons for test centres
        remove_buttons = await page.locator("a.deleteIcon[id*='removeTestCentre_']").all()
        
        if not remove_buttons:
            print("ℹ️ No test centres to remove")
            return True
        
        print(f"🔍 Found {len(remove_buttons)} test centres to remove")
        
        # Click each remove button
        for i, button in enumerate(remove_buttons, 1):
            try:
                print(f"🗑️ Removing test centre {i}/{len(remove_buttons)}...")
                await button.click()
                await asyncio.sleep(1)  # Wait between removals
                print(f"✅ Removed test centre {i}")
            except Exception as e:
                print(f"❌ Could not remove test centre {i}: {e}")
        
        print("✅ All test centres removed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error removing test centres: {e}")
        return False

