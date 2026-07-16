import pystray
from PIL import Image
import socket

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

def run_tray():
    #image = Image.new('RGB', (64, 64), color=(73, 109, 137))
    image = get_thumbnail("/home/lgp/.local/share/icons/hicolor/128x128/apps/plaster.png")
    
    
    def on_show(icon, item):
        send_command('SHOW_WINDOW')

    def on_quit(icon, item):
        send_command('QUIT_APP')
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Show", on_show),
        pystray.MenuItem("Quit", on_quit)
    )
    
    icon = pystray.Icon("Plaster", image, "Plaster", menu)
    icon.run()

if __name__ == "__main__":
    run_tray()
