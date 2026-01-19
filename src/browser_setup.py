import subprocess
import time
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

class BrowserManager:
    def __init__(self):
        self.chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        self.edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        self.profile_path = r"C:\browser-profile"
    
    async def launch_browser(self, browser_type="chrome"):
        if browser_type == "chrome":
            return await self._launch_chrome()
        elif browser_type == "edge":
            return await self._launch_edge()
    
    def _launch_chrome(self):
        cmd = [self.chrome_path, "--remote-debugging-port=9222", f"--user-data-dir={self.profile_path}"]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)
    
    def _launch_edge(self):
        cmd = [self.edge_path, "--remote-debugging-port=9223", f"--user-data-dir={self.profile_path}-edge"]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)