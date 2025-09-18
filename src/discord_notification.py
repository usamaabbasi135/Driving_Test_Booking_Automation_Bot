import requests
import json
from datetime import datetime
import asyncio

async def send_discord_notification(webhook_url: str, booking_details: dict, page_url: str = None):
    """
    Enhanced Discord notification with all extracted details
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    embed = {
        "title": "🎯 DRIVING TEST BOOKING CONFIRMED",
        "description": "**URGENT:** A driving test slot has been successfully reserved. Complete payment immediately!",
        "color": 0x00FF00,
        "timestamp": datetime.now().isoformat(),
        "fields": [
            {"name": "📍 Test Centre", "value": booking_details.get('centre', 'Not specified'), "inline": True},
            {"name": "📅 Test Date", "value": booking_details.get('formatted_date', booking_details.get('date', 'Not specified')), "inline": True},
            {"name": "🕐 Test Time", "value": booking_details.get('time', 'Not specified'), "inline": True},
            {"name": "💰 Test Fee", "value": "£62.00 (Standard Car Test)", "inline": True},
            {"name": "🔢 Slot ID", "value": booking_details.get('slot_id', 'Not available'), "inline": True},
            {"name": "⏰ Time Remaining", "value": booking_details.get('time_remaining', '15 minutes'), "inline": True},
            {"name": "📋 Full Date & Time", "value": booking_details.get('full_datetime', 'Check booking page'), "inline": False},
            {"name": "🔗 Execution Reference", "value": booking_details.get('reference', 'Check booking page'), "inline": True},
            {"name": "⚡ Status", "value": "**RESERVED - PAYMENT PENDING**", "inline": True},
            {"name": "⚠️ CRITICAL REMINDER", "value": f"You have **{booking_details.get('time_remaining', '15 minutes')}** to complete payment or the slot will be released!", "inline": False}
        ],
        "footer": {"text": f"Booking System • {current_time}"}
    }
    
    if page_url:
        embed["fields"].append({
            "name": "🔗 Complete Payment Now",
            "value": f"[Click here to complete payment]({page_url})",
            "inline": False
        })
    
    payload = {
        "content": "@everyone **DRIVING TEST RESERVED - PAYMENT REQUIRED NOW**",
        "embeds": [embed]
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
            'slot_id': 'Not available'
        }


async def handle_booking_success(page, discord_webhook_url: str, client_webhook_url: str = None):
    """
    Handle successful booking with professional notifications
    """
    print("🎉 Booking successful! Sending notifications...")
    
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

