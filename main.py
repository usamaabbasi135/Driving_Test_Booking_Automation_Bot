from src.auth import login_and_navigate
from src.slot_checker import search_slots

if __name__ == "__main__":
    page, context = login_and_navigate()
    slots = search_slots(page)
    print(slots)
