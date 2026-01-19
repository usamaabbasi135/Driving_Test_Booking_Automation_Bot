import logging
import random
import time

# Configure logging to write to a file
logging.basicConfig(
    filename="dvsa_bot.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def log(msg: str):
    """
    Logs a message to both console and log file.
    
    Args:
        msg: Message string to log
    """
    print(msg)
    logging.info(msg)

def random_wait(min_sec=2, max_sec=6):
    """
    Creates a random delay to simulate human behavior.
    
    This function is used to add variability to automation timing,
    making actions appear more natural and less bot-like.
    
    Args:
        min_sec: Minimum wait time in seconds
        max_sec: Maximum wait time in seconds
    """
    time.sleep(random.uniform(min_sec, max_sec))
