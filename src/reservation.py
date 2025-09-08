import json
from pathlib import Path
from playwright.sync_api import Page

RESERVATION_PATH = "reservation.json"

def reserve_slot(page: Page, centre: str, slot_time: str):
    """
    Reserve a given slot and stop at payment page.
    """
    print(f"📝 Reserving slot at {centre} - {slot_time}")

    # Navigate to slot details (example selector placeholders)
    page.click(f"text={centre}")
    page.click(f"text={slot_time}")
    page.click("button#reserve-slot")

    # Stop at payment page
    page.wait_for_url("**/payment*")

    reservation = {
        "centre": centre,
        "slot": slot_time,
        "status": "reserved - awaiting payment"
    }

    Path(RESERVATION_PATH).write_text(json.dumps(reservation, indent=2))
    print(f"✅ Reservation details saved in {RESERVATION_PATH}")

    return reservation
