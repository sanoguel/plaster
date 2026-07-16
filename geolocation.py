import gi
gi.require_version('GWeather', '4.0')
from gi.repository import GWeather

# Use GWeather.Info to automatically grab the system-configured location
info = GWeather.Info.new()
location = info.get_location()

if location:
    print(f"Detected Location: {location.get_name()}")
    sunrise, sunset = location.get_sun_times()
    print(f"Sunrise: {sunrise.format('%H:%M:%S')}")
    print(f"Sunset: {sunset.format('%H:%M:%S')}")
else:
    print("No location configured in GNOME settings.")
