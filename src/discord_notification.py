import requests
import json
from datetime import datetime
import asyncio

async def verify_booking_exists(page):
    """Check if booking actually exists in the reserved tests sidebar"""
    try:
        # Check for countdown timer
        timer = await page.locator("#minutesToTimeout").count()
        if timer > 0:
            return True
            
        # Check for reserved test in sidebar
        reserved_test = await page.locator("td[headers='dateTime']").count()
        return reserved_test > 0
        
    except:
        return False

async def send_discord_notification(webhook_url: str, booking_details: dict, page_url: str = None):
    # Simple notification format
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
    Enhanced extraction with all available booking details
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
    Handle successful booking with professional notifications
    """
    print("🎉 Booking successful! Sending notifications...")
    
    # Verify booking exists first
    if not await verify_booking_exists(page):
        print("❌ No confirmed booking found - not sending notification")
        return False

    # Wait a moment for page to fully load
    await asyncio.sleep(2)
    
    # Extract booking information
    booking_details = await extract_booking_details(page)
    current_page_url = page.url
    
    # Send notification to admin (you)
    admin_sent = await send_discord_notification(discord_webhook_url, booking_details, current_page_url)
    
    # Send to client if separate webhook provided
    client_sent = True
    if client_webhook_url and client_webhook_url != discord_webhook_url:
        client_sent = await send_discord_notification(client_webhook_url, booking_details, current_page_url)
    
    # Print booking summary
    print("\n" + "="*60)
    print("BOOKING CONFIRMATION SUMMARY")
    print("="*60)
    print(f"Centre: {booking_details['centre']}")
    print(f"Date: {booking_details['date']}")
    print(f"Time: {booking_details['time']}")
    print(f"Fee: {booking_details['fee']}")
    print(f"Reference: {booking_details['reference']}")
    print(f"Page URL: {current_page_url}")
    print("="*60)
    
    return admin_sent and client_sent