# utils.py
import os
import getpass
from datetime import datetime

LOG_DIR = os.path.expanduser("~/.local/state/plaster")
LOG_FILE = os.path.join(LOG_DIR, "plaster.log")

def log_event(message):
    """Global logging utility."""
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = getpass.getuser()
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp},{user},{message}\n")
