import os
import json
from datetime import datetime
from plaster.config import CONFIG_PATH, CACHE_PATH
from plaster.utils import log_event

def check_special_days():
    """
    Checks if today matches any user-defined special day in the config.
    Returns the wallpaper path if matched, otherwise None.
    """
    if not os.path.exists(CONFIG_PATH):
        return None

    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        log_event(f"Error reading config for special days: {e}")
        return None

    special_days = config.get("special_days", [])
    if not special_days:
        return None

    today_str = datetime.now().strftime("%m-%d")

    for event in special_days:
        event_date = event.get("date")
        if event_date == today_str:
            wallpaper_path = event.get("wallpaper_path")
            log_event(f"Special Day matched: {event.get('name')} -> {wallpaper_path}")
            return wallpaper_path

    return None

def add_special_day(name: str, date_str: str, wallpaper_path: str, target: str = "config"):
    """
    Safely adds a new special day to either the config or cache JSON file
    using an atomic write pattern (temp file + rename).
    """
    path = CONFIG_PATH if target == "config" else CACHE_PATH
    
    # 1. Load existing data or initialize a base structure
    data = {"special_days": []}
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            log_event(f"Error reading {path} for update, resetting structure: {e}")

    # 2. Build the new entry
    new_entry = {
        "name": name,
        "date": date_str,  # Expected format: "MM-DD"
        "wallpaper_path": wallpaper_path,
        "created_at": datetime.now().isoformat()
    }

    # 3. Append to the list
    data.setdefault("special_days", []).append(new_entry)

    # 4. Atomic write via a temporary file to prevent corruption
    temp_path = f"{path}.tmp"
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        os.replace(temp_path, path)
        log_event(f"Successfully added special day '{name}' to {target}.")
    except Exception as e:
        log_event(f"Failed to write special day to {path}: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
