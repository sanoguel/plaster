import os
import json
import random
import subprocess
import re
import time
import shutil
from datetime import datetime, timezone
from plaster.special_days import check_special_days
from plaster.seasons import get_astronomical_season
from plaster.daynight import get_day_night_status
from plaster.config import CONFIG_PATH, CACHE_PATH
from plaster.utils import log_event

def get_wallpaper_directory(mode="auto"):
    if not os.path.exists(CONFIG_PATH):
        return "/usr/share/backgrounds/gnome/"
        
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    mapping = config.get("mapping", {})
    root = config.get("root_wallpaper_dir", "")
    
    # Track if we are using the 'Static' path to avoid appending Day/Night
    is_static = False
    
    # 1. Determine base path
    target_dir = None
    modal = "🖼️"
    
    # Priority 0: Special Days Override (only if mode is auto)
    if mode == "auto":
        special_wallpaper = check_special_days()
        if special_wallpaper:
            # If special_wallpaper returns a full file path, you can split 
            # it or return the directory and handle direct file selection.
            # Assuming special_wallpaper gives a directory or file:
            if os.path.isfile(special_wallpaper):
                return os.path.dirname(special_wallpaper), "🥳"
            elif os.path.isdir(special_wallpaper):
                return special_wallpaper, "🥳"
    
    
    # Priority 1: Month
    if mode == "auto":
        month_name = datetime.now().strftime("%B")
        target_dir = mapping.get("months", {}).get(month_name)
        modal = "🗓️"
        log_event(f"Month value is: {month_name} and directory is {target_dir}")
    
    # Priority 2: Season
    if not target_dir and mode == "auto":
        season_name = get_astronomical_season()
        target_dir = mapping.get("seasons", {}).get(season_name)
        if target_dir in ("winter", "spring", "summer", "autumn"):
            match season_name:
                case "Winter":
                    modal = "❄️"
                case "Spring":
                    modal = "🌷"
                case "Summer":
                    modal = "🏖️"
                case "Autumn":
                    modal = "🍁"
        log_event(f"Season value is: {season_name} and directory is {target_dir} and modal is {modal}")
            
    # Priority 3: Static (Used by Auto-fallback or Static Mode)
    if not target_dir:
        target_dir = mapping.get("static", config.get("static_wallpaper_dir", ""))
        is_static = True
        modal = "📁"
    
    # 2. Finalize Path
    if not target_dir:
        target_dir = get_system_default_wallpaper()
        modal = "G"
        return target_dir, modal
        
    
    full_path = os.path.join(root, target_dir)
    
    # 3. Append Day/Night only if NOT static and NOT fallback
    if not is_static:
        status = get_day_night_status()
        full_path = os.path.join(full_path, status)
    return full_path, modal

def apply_wallpaper(file_path):
    """Applies the wallpaper using gsettings."""
    uri = f"file://{file_path}"
    try:
        subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri], check=True)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri], check=True)
        subprocess.run(["wal", "-c"], check=True)
        subprocess.run(["wal", "-i", file_path], check=True)
        time.sleep(0.5)
        sync_rgb_colors()
        log_event(f"Successfully set wallpaper to: {file_path}")
    except subprocess.CalledProcessError as e:
        log_event(f"Error setting wallpaper: {e}")
    
def resolve_and_update_cache(mode=None):
    if not mode:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                try:
                    config = json.load(f)
                    mode = config.get("mode", "auto")
                except:
                    mode = "auto"
        else:
            mode = "auto"
            
    # Load full config to sync parameters into cache
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            try:
                config = json.load(f)
            except:
                pass

    path, modal = get_wallpaper_directory(mode=mode)
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    status = get_day_night_status()
    if status == "Day":
        time_of_day = "🌞"
    elif status == "Night":
        time_of_day = "🌛"
    
    # Check if path exists and has images
    if not os.path.exists(path):
        return
        
    all_files = [f for f in os.listdir(path) if f.lower().endswith(('.jpg', '.png'))]
    
    if not all_files:
        return # Handle empty directory gracefully
        
    selected_file = os.path.join(path, random.choice(all_files))
    apply_wallpaper(selected_file)
    log_event(f"Wallpaper rotated to: {selected_file}")
    
    # Load existing cache to preserve structure
    data = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, 'r') as f:
            try: data = json.load(f)
            except: pass
            
    # Comprehensive update: sync both active rotation results and configuration parameters
    data.update({
        "current_wallpaper": selected_file,
        "current_wallpaper_dir": path,
        "modal": modal,
        "time_of_day": time_of_day,
        "day_or_night": status,
        "season": get_astronomical_season(),
        "mode": mode,
        "change_interval_minutes": config.get("change_interval_minutes", 5),
        "root_wallpaper_dir": config.get("root_wallpaper_dir", ""),
        "static_wallpaper_dir": config.get("static_wallpaper_dir", ""),
        "location": config.get("location", {}),
        "mapping": config.get("mapping", {}),
        "last_updated": current_time
    })
    
    # Save back to cache file
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, indent=4)
        
def sync_rgb_colors():
    # Skip if openrgb is not installed on the system
    if not shutil.which("openrgb"):
        log_event("OpenRGB not found on this system; skipping RGB sync.")
        return
    colors_file = os.path.expanduser("~/.cache/wal/colors.sh")
    
    # 1. Read the file
    with open(colors_file, 'r') as f:
        content = f.read()
    
    # 2. Flexible regex to find color1="[HEX]" or color1='[HEX]'
    match = re.search(r'color1=["\']#?([0-9a-fA-F]{6})["\']', content)
    
    if match:
        clean_color = match.group(1)
        log_event(f"DEBUG: Successfully extracted color: {clean_color}")
        
        # 3. Use absolute path to be safe
        try:
            subprocess.run(["/usr/bin/openrgb", "--mode", "direct", "--color", clean_color], check=True)
            log_event(f"OpenRGB successfully set to {clean_color}")
        except subprocess.CalledProcessError as e:
            log_event(f"OpenRGB command failed: {e}")
    else:
        log_event("ERROR: Could not locate color1 in ~/.cache/wal/colors.sh")
        
def get_system_default_wallpaper():
    try:
        # Query gsettings for the current GNOME background URI
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.background", "picture-uri"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        uri = result.stdout.strip().strip("'").strip('"')
        if uri.startswith("file://"):
            file_path = uri[7:]
            if os.path.exists(file_path):
                return os.path.dirname(file_path)
    except Exception:
        pass
    
    # Absolute last resort fallback directories if gsettings fails
    for fallback in ["/usr/share/backgrounds/gnome", "/usr/share/backgrounds"]:
        if os.path.exists(fallback):
            return fallback
            
    return ""
