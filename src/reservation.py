from playwright.sync_api import Page
import asyncio
from src.discord_notification import extract_booking_details,send_discord_notification,handle_booking_success

async def instant_reserve(page: Page):
    """Fast reservation with better error handling"""
    selectors = [
        "a:has-text('Reserve')",
        "input[value*='Reserve']", 
        "button:has-text('Reserve')"
    ]
    
    for selector in selectors:
        try:
            await page.click(selector, timeout=3000)  # Increased to 500ms
            print(f"⚡ INSTANT RESERVE CLICKED: {selector}")
            return True
        except Exception as e:
            print(f"Failed {selector}: {str(e)[:50]}")
            continue
    
    print("❌ No reserve buttons found")
    return False

async def return_to_search_results(page: Page):
    """
    Clicks the "Return to search results" button and navigates back to current week
    """
    try:
        print("🔙 Clicking 'Return to search results'...")
        
        return_button = "a:has-text('Return to search results')"
        await page.click(return_button)
        await asyncio.sleep(2)
        
        print("✅ Returned to search results")
        
        # Click previous week until button disappears
        print("⬅️ Going back to current week...")
        while True:
            try:
                previous_button = await page.locator("a#searchForWeeklySlotsPreviousWeek").count()
                if previous_button == 0:
                    break
                
                await page.click("a#searchForWeeklySlotsPreviousWeek")
                await asyncio.sleep(0.5)
                
            except:
                break
        
        print("✅ Reached current week")
        return "RETURNED_TO_SEARCH"
        
    except Exception as e:
        print(f"❌ Error returning to search results: {e}")
        return "ERROR"

async def handle_reservation_page(page: Page, discord_webhook: str = None):
    """
    Handles the reservation page after clicking a green box.
    Now includes Discord notifications when booking succeeds.
    """
    try:
        print("📋 Checking reservation page for available slots...")
        await asyncio.sleep(2)
        
        # Look for any reserve buttons on the page
        all_reserve_buttons = await page.locator("a:has-text('Reserve'), input[value*='Reserve']").all()
        
        if all_reserve_buttons:
            print(f"🎯 Found {len(all_reserve_buttons)} reserve elements - clicking all!")
            
            reserved_count = 0
            for i, button in enumerate(all_reserve_buttons, 1):
                try:
                    await button.click()
                    reserved_count += 1
                    await asyncio.sleep(0.5)
                except:
                    continue
            
            if reserved_count > 0:
                print(f"🎉 SUCCESS! Reserved {reserved_count} slots!")
                
                # ADD THIS: Send Discord notification
                if discord_webhook:
                    await handle_booking_success(page, discord_webhook)
                
                return "RESERVATIONS_MADE"
            else:
                print("❌ Could not reserve any slots")
                return await return_to_search_results(page)
        
        # If no reserve buttons found
        print("❌ No reserve buttons found - returning to search")
        return await return_to_search_results(page)
        
    except Exception as e:
        print(f"❌ Error handling reservation page: {e}")
        return await return_to_search_results(page)

async def handle_successful_reservation_and_continue(page, discord_webhook: str):
    """
    Handle successful reservation, send notification, then continue searching
    """
    print("🎉 Reservation successful! Sending notification and continuing search...")
    
    # Send Discord notification
    booking_details = await extract_booking_details(page)
    notification_sent = await send_discord_notification(discord_webhook, booking_details, page.url)
    
    if notification_sent:
        print("✅ Discord notification sent!")
    
    # Click "Yes, add another test" to continue searching
    try:
        add_another_button = await page.locator("a#submitDismissReservedSlotMessage").count()
        if add_another_button > 0:
            await page.click("a#submitDismissReservedSlotMessage")
            print("🔄 Clicked 'Yes, add another test' - continuing search...")
            await asyncio.sleep(2)
            return "CONTINUE_SEARCH"
        else:
            # Alternative: click "Return to search results" if available
            return_button = await page.locator("a:has-text('Return to search results')").count()
            if return_button > 0:
                await page.click("a:has-text('Return to search results')")
                print("🔄 Clicked 'Return to search results' - continuing search...")
                await asyncio.sleep(2)
                return "CONTINUE_SEARCH"
    except Exception as e:
        print(f"Error continuing search: {e}")
    
    return "SEARCH_COMPLETED"

async def verify_booking_success(page: Page):
    """
    Verify that booking was actually successful by checking for confirmation elements
    """
    try:
        # Wait for page to load after clicking reserve
        await asyncio.sleep(3)
        
        # Check for countdown timer (indicates successful reservation)
        timer_element = await page.locator("#minutesToTimeout").count()
        if timer_element > 0:
            print("✅ Countdown timer found - booking confirmed")
            return True
        
        # Check for reserved tests table with actual booking
        reserved_test = await page.locator("td[headers='dateTime']").count()
        if reserved_test > 0:
            print("✅ Reserved test found in sidebar - booking confirmed")
            return True
        
        # Check for booking confirmation message
        confirmation_text = await page.locator("text=reserved").count()
        if confirmation_text > 0:
            print("✅ Reservation confirmation text found")
            return True
        
        print("❌ No booking confirmation found")
        return False
        
    except Exception as e:
        print(f"❌ Error verifying booking: {e}")
        return False