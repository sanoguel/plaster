import urllib.request
import json
from datetime import datetime
from plaster.config import load_config

def get_day_night_status():
    config = load_config()
    loc = config.get("location", {})
    lat = loc.get("latitude")
    lon = loc.get("longitude")

    if lat is None or lon is None:
        return "Day" # Default if config is missing

    url = f"https://api.sunrisesunset.io/json?lat={lat}&lng={lon}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        results = data['results']
        
        def to_hhmm(time_str):
            t = datetime.strptime(time_str, "%I:%M:%S %p")
            return t.hour * 100 + t.minute

        sunrise = to_hhmm(results['sunrise'])
        sunset = to_hhmm(results['sunset'])
        now = datetime.now().hour * 100 + datetime.now().minute

    return "Day" if sunrise <= now < sunset else "Night"
