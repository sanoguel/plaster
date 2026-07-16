import json
import os

CONFIG_PATH = os.path.expanduser("~/.config/plaster/config.json")
CACHE_PATH = os.path.expanduser("~/.cache/plaster/plaster.json")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets')

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}
