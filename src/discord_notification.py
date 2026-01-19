import requests
import json
from datetime import datetime
import asyncio

async def verify_booking_exists(page):
    """
    Verifies that a booking actually exists on the page before sending notifications.
    
    This prevents false notifications by checking for actual confirmation elements:
    - Countdown timer (appears when slot is reserved)
    - Reserved test entry in the sidebar table
    
    Args:
        page: Playwright page object
        
    Returns:
        bool: True if booking confirmation is found, False otherwise
    """
    try:
        # Check for countdown timer element
        timer = await page.locator("#minutesToTimeout").count()
        if timer > 0:
            return True
            
        # Check for reserved test entry in the sidebar table
        reserved_test = await page.locator("td[headers='dateTime']").count()
        return reserved_test > 0
        
    except:
        return False

async def send_discord_notification(webhook_url: str, booking_details: dict, page_url: str = None):
    """
    Sends a Discord notification with booking confirmation details.
    
    Formats the booking information into a readable message and posts it
    to the specified Discord webhook URL. The notification includes:
    - Date and time of the test
    - Test type (e.g., Car standard)
    - Test centre name
    - Booking fee
    
    Args:
        webhook_url: Discord webhook URL to send the notification to
        booking_details: Dictionary containing booking information
        page_url: Optional URL of the booking page (not currently used in message)
        
    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    # Format booking details into a tab-separated message
    message = f"{booking_details.get('full_datetime', 'Unknown')}\t{booking_details.get('test_type', 'Car standard')}\t{booking_details.get('centre', 'Unknown')}\t£62.00"

    payload = {
        "content": f"**BOOKING CONFIRMED**\n```{message}```"
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        return response.status_code == 204
    except Exception as e:
        print(f"Discord notification error: {e}")
        return False

async def extract_booking_details(page):
    """
    Extracts all available booking details from the reservation confirmation page.
    
    This function scrapes various elements on the page to gather comprehensive
    booking information including:
    - Test centre name
    - Date and time of the test
    - Test type (Car standard, etc.)
    - Countdown timer (time remaining to complete booking)
    - Slot ID and booking reference
    
    Args:
        page: Playwright page object on the reservation confirmation page
        
    Returns:
        dict: Dictionary containing all extracted booking details
    """
    try:
        booking_details = {}
        
        # Extract centre and date from heading
        try:
            centre_text = await page.locator("h3").first.text_content()
            if "at " in centre_text:
                booking_details['centre'] = centre_text.split("at ")[-1]
            if "on " in centre_text and "at " in centre_text:
                booking_details['date'] = centre_text.split("on ")[1].split(" at ")[0]
        except:
            booking_details['centre'] = "Check booking page"
            booking_details['date'] = "Check booking page"
        
        # Extract actual reserved test details from the sidebar
        try:
            # Get test date and time from reserved tests table
            date_time_cell = await page.locator("td[headers='dateTime']").text_content()
            if date_time_cell:
                booking_details['full_datetime'] = date_time_cell.strip()
                # Parse "Tue 03 Feb 2026 10:04" format
                parts = date_time_cell.strip().split()
                if len(parts) >= 4:
                    booking_details['formatted_date'] = f"{parts[1]} {parts[2]} {parts[3]}"
                    booking_details['time'] = parts[4] if len(parts) > 4 else "Check booking page"
        except:
            booking_details['full_datetime'] = "Check booking page"
            booking_details['time'] = "Check booking page"

        # Get test type
        try:
            test_type_cell = await page.locator("td[headers='slotType']").text_content()
            if test_type_cell:
                booking_details['test_type'] = test_type_cell.strip()
            else:
                booking_details['test_type'] = "Car standard"
        except:
            booking_details['test_type'] = "Car standard"
        
        # Extract test centre from reserved tests table
        try:
            centre_cell = await page.locator("td.searchcriteria span.bold").text_content()
            if centre_cell:
                centre_lines = centre_cell.strip().split('\n')
                if centre_lines:
                    booking_details['centre'] = centre_lines[0].strip()
        except:
            pass
        
        # Extract countdown timer
        try:
            timer_text = await page.locator("#minutesToTimeout").text_content()
            if timer_text:
                booking_details['time_remaining'] = f"{timer_text} minutes"
        except:
            booking_details['time_remaining'] = "15 minutes"
        
        # Generate slot ID from remove link
        try:
            remove_link = await page.locator("a[id*='releaseReservedSlot_']").get_attribute("id")
            if remove_link:
                slot_id = remove_link.split("_")[-1]
                booking_details['slot_id'] = slot_id
        except:
            booking_details['slot_id'] = "Check booking page"
        
        # Get booking reference from URL
        try:
            current_url = page.url
            if "execution=" in current_url:
                execution_id = current_url.split("execution=")[1].split("&")[0]
                booking_details['reference'] = f"EXEC-{execution_id}"
        except:
            booking_details['reference'] = "Check booking page"
        
        return booking_details
        
    except Exception as e:
        print(f"Error extracting booking details: {e}")
        return {
            'centre': 'Not specified',
            'date': 'Not specified', 
            'time': 'Not specified',
            'fee': '£62.00',
            'reference': 'Check booking page',
            'time_remaining': '15 minutes',
            'slot_id': 'Not available',
            'test_type': 'Car standard'
        }


async def handle_booking_success(page, discord_webhook_url: str, client_webhook_url: str = None):
    """
    Handles successful booking by verifying and sending notifications.
    
    This is the main function called after a successful reservation. It:
    1. Verifies the booking actually exists on the page
    2. Extracts all booking details
    3. Sends Discord notifications to specified webhooks
    4. Prints a summary of the booking to the console
    
    Args:
        page: Playwright page object on the reservation confirmation page
        discord_webhook_url: Primary Discord webhook URL for notifications
        client_webhook_url: Optional secondary webhook URL for client notifications
        
    Returns:
        bool: True if notifications were sent successfully, False otherwise
    """
    print("Booking successful! Sending notifications...")
    
    # Verify booking exists before sending notification
    if not await verify_booking_exists(page):
        print("No confirmed booking found - not sending notification")
        return False

    # Wait for page to fully load all booking details
    await asyncio.sleep(2)
    
    # Extract all available booking information from the page
    booking_details = await extract_booking_details(page)
    current_page_url = page.url
    
    # Send notification to primary webhook (admin/owner)
    admin_sent = await send_discord_notification(discord_webhook_url, booking_details, current_page_url)
    
    # Send to client webhook if a separate one is provided
    client_sent = True
    if client_webhook_url and client_webhook_url != discord_webhook_url:
        client_sent = await send_discord_notification(client_webhook_url, booking_details, current_page_url)
    
    # Print booking summary to console for immediate visibility
    print("\n" + "="*60)
    print("BOOKING CONFIRMATION SUMMARY")
    print("="*60)
    print(f"Centre: {booking_details['centre']}")
    print(f"Date: {booking_details['date']}")
    print(f"Time: {booking_details['time']}")
    print(f"Fee: {booking_details.get('fee', '£62.00')}")
    print(f"Reference: {booking_details['reference']}")
    print(f"Page URL: {current_page_url}")
    print("="*60)
    
    return admin_sent and client_sent