from playwright.sync_api import Page
import asyncio
from src.discord_notification import extract_booking_details,send_discord_notification

async def return_to_search_results(page: Page):
    """
    Clicks the "Return to search results" button to go back to calendar.
    """
    try:
        print("🔙 Clicking 'Return to search results'...")
        
        # Look for the return button
        return_button = "a:has-text('Return to search results')"
        await page.click(return_button)
        await asyncio.sleep(2)
        
        print("✅ Returned to search results")
        return "RETURNED_TO_SEARCH"
        
    except Exception as e:
        print(f"❌ Error returning to search results: {e}")
        return "ERROR"

async def handle_reservation_page(page: Page):
    """
    Handles the reservation page - finds and clicks ALL available reserve buttons quickly.
    """
    try:
        print("📋 Checking reservation page for available slots...")
        await asyncio.sleep(2)
        
        # Look for the booking table
        booking_table = await page.locator("table#displaySlot").count()
        if booking_table > 0:
            print("📅 Found booking table, looking for reserve buttons...")
            
            # Find ALL reserve buttons/links in the table
            reserve_buttons = await page.locator("table#displaySlot a:has-text('Reserve')").all()
            
            if reserve_buttons:
                print(f"🎯 Found {len(reserve_buttons)} reserve button(s) - clicking ALL quickly!")
                
                # Click ALL reserve buttons as fast as possible
                reserved_count = 0
                for i, button in enumerate(reserve_buttons, 1):
                    try:
                        print(f"⚡ Clicking reserve button {i}/{len(reserve_buttons)}...")
                        await button.click()
                        reserved_count += 1
                        # Very short wait between clicks to be fast
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"❌ Failed to click reserve button {i}: {e}")
                        continue
                
                if reserved_count > 0:
                    print(f"🎉 SUCCESS! Reserved {reserved_count} test slots!")
                    await asyncio.sleep(2)  # Wait for page to process
                    return "RESERVATIONS_MADE"
                else:
                    print("❌ Could not reserve any slots")
                    return await return_to_search_results(page)
            else:
                print("❌ No reserve buttons found in table")
                return await return_to_search_results(page)
        
        # Alternative: Look for any reserve buttons on the page
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
                return "RESERVATIONS_MADE"
        
        # If no reserve buttons found
        print("❌ No reserve buttons found - returning to search")
        return await return_to_search_results(page)
        
    except Exception as e:
        print(f"❌ Error handling reservation page: {e}")
        return await return_to_search_results(page)

async def reserve_all_available_slots(page: Page):
    """
    Alternative faster approach - find and click ALL reserve buttons immediately.
    """
    try:
        print("⚡ SPEED RESERVATION - Finding all reserve buttons...")
        
        # Get all reserve buttons at once
        all_reserves = await page.locator(
            "a:has-text('Reserve'), "
            "input[value*='Reserve'], "
            "button:has-text('Reserve')"
        ).all()
        
        if not all_reserves:
            print("❌ No reserve buttons found")
            return False
        
        print(f"🎯 Found {len(all_reserves)} reserve options - RAPID FIRE CLICKING!")
        
        # Click them all as fast as possible
        tasks = []
        for i, button in enumerate(all_reserves):
            # Create concurrent click tasks for maximum speed
            task = asyncio.create_task(click_reserve_button(button, i+1))
            tasks.append(task)
        
        # Execute all clicks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        print(f"🎉 RAPID RESERVATION COMPLETE! {success_count}/{len(all_reserves)} successful!")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ Speed reservation error: {e}")
        return False

async def click_reserve_button(button, index):
    """
    Helper function to click a single reserve button.
    """
    try:
        await button.click()
        print(f"✅ Reserved slot {index}")
        return True
    except Exception as e:
        print(f"❌ Failed slot {index}: {e}")
        return False
    

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