import asyncio, random, yaml

async def human_wait(min_sec=1, max_sec=3):
    """
    Creates a random delay to simulate human behavior between form interactions.
    
    Args:
        min_sec: Minimum wait time in seconds
        max_sec: Maximum wait time in seconds
    """
    await asyncio.sleep(random.uniform(min_sec, max_sec))

def load_centres():
    """
    Loads the list of test centres from the centres.yaml configuration file.
    
    Returns:
        list: List of test centre names as strings
    """
    with open("centres.yaml", "r") as f:
        return yaml.safe_load(f)["centres"]

async def fill_initial_booking(page, centre_name: str):
    """
    Fills the initial booking form with search criteria.
    
    This function configures the booking form with:
    - Test category: Car (TC-B)
    - Test centre: The specified centre name
    - Instructor: No instructor selected
    - Special needs: None
    
    After filling, it submits the form to navigate to the slot search results page.
    
    Args:
        page: Playwright page object representing the booking form
        centre_name: Name of the test centre to search for
        
    Returns:
        page: The same page object after form submission
    """
    print(f"Filling booking form for first centre: {centre_name}")

    # Select car category (TC-B is the code for standard car driving test)
    await page.select_option("#businessBookingTestCategoryRecordId", "TC-B")
    await human_wait(1, 3)

    # Select the test centre from the dropdown menu
    await page.select_option("#favtestcentres", label=centre_name)
    await human_wait(1, 3)

    # Set instructor option to "No instructor" (value "-1" means no instructor)
    await page.select_option("select[name='businessSlotSearchCriteria.instructorPRN']", "-1")
    await human_wait(1, 2)

    # Check the "No special needs" radio button
    await page.check("#specialNeedsChoice-noneeds")
    await human_wait(1, 2)

    # Submit the form to search for available slots
    await page.click("#submitSlotSearch")
    await page.wait_for_load_state("networkidle")

    print(f"Submitted booking form for {centre_name}, now on results page")

    return page
