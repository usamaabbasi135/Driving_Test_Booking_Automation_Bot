import logging
import random
import time

logging.basicConfig(
    filename="dvsa_bot.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def log(msg: str):
    print(msg)
    logging.info(msg)

def random_wait(min_sec=2, max_sec=6):
    time.sleep(random.uniform(min_sec, max_sec))
