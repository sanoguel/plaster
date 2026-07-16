import json
import os
import shutil
from pathlib import Path
from plaster.utils import log_event

# Paths remain consistent with your existing logic
CONFIG_DIR = Path(os.path.expanduser("~/.config/plaster"))
CACHE_DIR = Path(os.path.expanduser("~/.cache/plaster"))
CONFIG_PATH = CONFIG_DIR / "config.json"
CACHE_PATH = CACHE_DIR / "plaster.json"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / 'assets'

def initialize_environment():
    """Ensures directories exist and config is initialized from template."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize config from template if it doesn't exist
    if not CONFIG_PATH.exists():
        template_path = ASSETS_DIR / "plaster.json"
        if template_path.exists():
            shutil.copy(template_path, CONFIG_PATH)
            log_event(f"Initialized new configuration at {CONFIG_PATH}")
        else:
            log_event(f"Warning: Template not found at {template_path}")

def load_config():
    """Loads existing configuration."""
    if not CONFIG_PATH.exists():
        initialize_environment()
        
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

# Automatically run initialization on import
initialize_environment()
