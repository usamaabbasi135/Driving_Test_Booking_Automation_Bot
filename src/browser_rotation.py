from datetime import datetime, timedelta
from playwright.async_api import Page

class BrowserRotationManager:
    """
    Manages automatic browser rotation to reduce detection risk.
    
    This class implements a timer-based browser switching mechanism that
    alternates between Chrome and Edge every 15 minutes. This helps make
    the automation appear more like multiple users rather than a single bot.
    """
    
    def __init__(self, initial_browser="chrome"):
        """
        Initialize the browser rotation manager.
        
        Args:
            initial_browser: Starting browser type ("chrome" or "edge")
        """
        self.current_browser = initial_browser
        self.session_start_time = datetime.now()
        self.session_duration_minutes = 15  # Switch browsers every 15 minutes
        
    def should_switch_browser(self):
        """
        Checks if 15 minutes have elapsed since the last browser switch.
        
        Returns:
            bool: True if it's time to switch browsers, False otherwise
        """
        elapsed = datetime.now() - self.session_start_time
        return elapsed.total_seconds() > (self.session_duration_minutes * 60)
    
    def switch_browser(self):
        """
        Switches to the alternate browser type and resets the timer.
        
        Alternates between Chrome and Edge. If currently using Chrome,
        switches to Edge, and vice versa.
        
        Returns:
            str: The new browser type after switching
        """
        self.current_browser = "edge" if self.current_browser == "chrome" else "chrome"
        self.session_start_time = datetime.now()
        print(f"Switching to {self.current_browser} browser")
        return self.current_browser