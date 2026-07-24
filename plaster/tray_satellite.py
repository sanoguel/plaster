import pystray
from PIL import Image
import socket
import os
import dbus
import time
from plaster.config import CONFIG_PATH, ASSETS_DIR
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
from plaster.utils import log_event

def get_thumbnail(file_path):
    try:
        # Open the actual image
        img = Image.open(file_path)
        
        # Resize it to your 64x64 display size (using LANCZOS for high quality)
        img = img.resize((64, 64), Image.Resampling.LANCZOS)
        
        return img
    except Exception as e:
        log_event(f"Error loading thumbnail for {file_path}: {e}")
        # Fallback to the blueish block if the image fails to load
        return Image.new('RGB', (64, 64), color=(73, 109, 137))

def send_command(command):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', 65432))
            s.sendall(command.encode())
    except:
        pass

def handle_sleep_signal(active):
    if not active:
        # active is False when the system is *resuming* from sleep
        log_event(f"System resumed from sleep! Triggering wallpaper/RGB rotation...")
        # allow 5 seconds for system to wake and then call the rotation and sync functions here:
        time.sleep(5)
        send_command('ROTATE_NOW')

def setup_sleep_listener():
    # Integrate D-Bus with the GLib main loop (which GTK uses)
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    
    bus.add_signal_receiver(
        handle_sleep_signal,
        signal_name='PrepareForSleep',
        dbus_interface='org.freedesktop.login1.Manager',
        bus_name='org.freedesktop.login1'
    )

def run_tray():
    #image = Image.new('RGB', (64, 64), color=(73, 109, 137))
    image = get_thumbnail(os.path.join(ASSETS_DIR, 'plaster.png'))
    
    
    def on_show(icon, item):
        send_command('SHOW_WINDOW')

    # New handler for rotating via tray menu
    def on_rotate(icon, item):
        send_command('ROTATE_NOW')
    
    def on_quit(icon, item):
        send_command('QUIT_APP')
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Show Plaster", on_show),
        pystray.MenuItem("Rotate Wallpaper", on_rotate), # Added option
        pystray.MenuItem("Quit", on_quit)
    )
    
    # Initialize the systemd sleep listener over D-Bus
    try:
        setup_sleep_listener()
    except Exception as e:
        # Fallback if system bus is unavailable (e.g., running in certain containerized tests)
        log_event(f"Warning: Could not setup sleep listener: {e}")
    
    icon = pystray.Icon("Plaster", image, "Plaster", menu)
    icon.run()

if __name__ == "__main__":
    run_tray()
