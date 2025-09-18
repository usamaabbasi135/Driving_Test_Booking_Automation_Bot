import asyncio, random, yaml

async def human_wait(min_sec=1, max_sec=3):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

def load_centres():
    with open("centres.yaml", "r") as f:
        return yaml.safe_load(f)["centres"]

async def fill_initial_booking(page, centre_name: str):
    """
    Fill the first booking form with Car, No Instructor, No Special Needs, and one test centre.
    """
    print(f"📝 Filling booking form for first centre: {centre_name}")

    # Car category
    await page.select_option("#businessBookingTestCategoryRecordId", "TC-B")
    await human_wait(1, 3)

    # Select centre from dropdown (Choose from either)
    await page.select_option("#favtestcentres", label=centre_name)
    await human_wait(1, 3)

    # Instructor = No instructor
    await page.select_option("select[name='businessSlotSearchCriteria.instructorPRN']", "-1")
    await human_wait(1, 2)


    # Special needs = No
    await page.check("#specialNeedsChoice-noneeds")
    await human_wait(1, 2)

    # Submit the form
    await page.click("#submitSlotSearch")
    await page.wait_for_load_state("networkidle")

    print(f"✅ Submitted booking form for {centre_name}, now on results page")

    return page
