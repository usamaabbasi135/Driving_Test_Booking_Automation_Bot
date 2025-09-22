from datetime import datetime, timedelta
from playwright.async_api import Page

class BrowserRotationManager:
    def __init__(self, initial_browser="chrome"):
        self.current_browser = initial_browser
        self.session_start_time = datetime.now()
        self.session_duration_minutes = 15
        
    def should_switch_browser(self):
        """Check if 15 minutes have passed"""
        elapsed = datetime.now() - self.session_start_time
        return elapsed.total_seconds() > (self.session_duration_minutes * 60)
    
    def switch_browser(self):
        """Switch to next browser and reset timer"""
        self.current_browser = "edge" if self.current_browser == "chrome" else "chrome"
        self.session_start_time = datetime.now()
        print(f"🔄 Switching to {self.current_browser} browser")
        return self.current_browser