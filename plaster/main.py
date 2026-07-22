import gi
import json
import os
import sys
import signal
import shutil
import subprocess
import threading
import socket
import logging
from datetime import datetime
import getpass

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, Gio, GLib

# Import your custom modules
from plaster.daynight import get_day_night_status
from plaster.seasons import get_astronomical_season
from plaster.config import CONFIG_PATH, ASSETS_DIR, PROJECT_ROOT
from plaster.resolver import get_wallpaper_directory, resolve_and_update_cache
from plaster.utils import log_event
from plaster.log_management import LogManager

CACHE_PATH = os.path.expanduser("~/.cache/plaster/plaster.json")
LOG_DIR = os.path.expanduser("~/.local/state/plaster")
LOG_FILE = os.path.join(LOG_DIR, "plaster.log")

class WallpaperApp(Adw.Application):
   
    def rotate_wallpaper_callback(self):
        config = self.load_config()
        current_mode = config.get("mode", "auto")
        resolve_and_update_cache(mode=current_mode)
        log_manager.evaluate_and_rotate()
        return True
    
    def is_wal_installed(self):
        return shutil.which("wal") is not None
        
    def is_openrgb_installed(self):
        return shutil.which("openrgb") is not None
    
    def __init__(self):
        super().__init__(application_id='com.github.sanoguel.plaster')
        self.main_box = None
        self.win = None
        self.tray_process = None # Track the child tray process
        self.rotation_timer_id = None
        
    def start_rotation_timer(self, minutes):
        # Remove existing timer if it exists
        if self.rotation_timer_id:
            GLib.source_remove(self.rotation_timer_id)
            
        # Convert minutes to seconds
        seconds = int(minutes) * 60
        self.rotation_timer_id = GLib.timeout_add_seconds(seconds, self.rotate_wallpaper_callback)
        log_event(f"Rotation timer started: {minutes} minutes")
        
    def load_config(self):
        """Helper to load config.json or return defaults."""
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                try:
                    return json.load(f)
                except:
                    pass
        return {"change_interval_minutes": 5} # Default value
    
    def rotate_wallpaper_callback(self):
        config = self.load_config()
        current_mode = config.get("mode", "auto")
        resolve_and_update_cache(mode=current_mode)
        log_event("Rotating wallpaper...")
        return True # Return True to keep the timer running
    
    def refresh_wallpaper_path(self):
        config = self.load_config()
        current_mode = config.get("mode", "auto")
        # This calls the resolver logic based on your active mode
        path, modal_icon = get_wallpaper_directory(mode=current_mode)
        print(f"Current wallpaper directory: {path}")
        indicator = Gtk.Image.new_from_icon_name(modal_icon)
        return path

    def update_cache_status(self):
        """Updates the status and wallpaper path in the cache file."""
        data = {}
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    pass
        
        # 1. Load configuration from the source of truth (config.json)
        config = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                try:
                    config = json.load(f)
                except:
                    pass
        mode = config.get("mode", "auto")
        #if os.path.exists(CONFIG_PATH):
        #    with open(CONFIG_PATH, 'r') as f:
        #        try:
        #            config = json.load(f)
        #            mode = config.get("mode", "auto")
        #        except:
        #            pass
        
        # 2. Update status info
        data["day_or_night"] = get_day_night_status()
        data["season"] = get_astronomical_season()
        data["mode"] = mode  # Keep the mode in cache for UI reference
        
        # 3. Use the dynamic mode in the resolver
        active_path, modal_icon = get_wallpaper_directory(mode=mode)
        data["current_wallpaper_dir"] = active_path
        data["modal"] = modal_icon  # Save the icon name to cache
        
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, 'w') as f:
            json.dump(data, f, indent=4)

    def get_wal_colors(self):
        colors_file = os.path.expanduser("~/.cache/wal/colors.sh")
        colors = []
        if os.path.exists(colors_file):
            with open(colors_file, 'r') as f:
                for line in f:
                    if "color" in line and "=" in line:
                        colors.append(line.split('=')[1].strip().strip('"').strip("'"))
        return colors[:8]

    def on_gear_clicked(self, button):
        settings_win = SettingsWindow(transient_for=self.win)
        settings_win.present()
        
    def monitor_config(self):
        cache_file = Gio.File.new_for_path(CACHE_PATH)
        self.monitor = cache_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.monitor.connect("changed", self.on_config_changed)

    def on_config_changed(self, monitor, file, other_file, event_type):
        if event_type in [Gio.FileMonitorEvent.CHANGED, Gio.FileMonitorEvent.CHANGES_DONE_HINT]:
            GLib.idle_add(self.build_ui_content)
            
    
    def log_startup(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user = getpass.getuser()
    
        with open(LOG_FILE, "a") as f:
            f.write(f"{timestamp},{user},Plaster started\n")

    def do_activate(self):
        # Log the startup
        log_event("Plaster started")
        config = self.load_config()
        current_mode = config.get("mode", "auto")
        # Update cache status on startup
        resolve_and_update_cache(mode=current_mode)
        self.update_cache_status()
        
        self.win = Adw.ApplicationWindow(application=self)
        self.win.set_default_size(600, 400)
        self.win.set_title("Wallpaper Config")
        
        icon_path = os.path.join(ASSETS_DIR, 'plaster.png')
        self.win.set_icon_name(icon_path)
        
        # Connect the new close handler
        self.win.connect("close-request", self.on_close_request)
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self.main_box.set_margin_start(20); self.main_box.set_margin_end(20)
        self.main_box.set_margin_top(20); self.main_box.set_margin_bottom(20)

        content = Adw.ToolbarView()
        content.add_top_bar(Adw.HeaderBar())
        content.set_content(self.main_box)
        self.win.set_content(content)
        
        self.build_ui_content()
        self.win.present()
        self.monitor_config()
        
        # Launch the satellite
        #subprocess.Popen(["python3", "tray_satellite.py"])
        
        # Track the tray process for proper cleanup
        venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "python")
        self.tray_process = subprocess.Popen([sys.executable, "-m", "plaster.tray_satellite"])
    
        # Start a simple thread to listen for the tray's signal
        threading.Thread(target=self.listen_for_tray, daemon=True).start()
        
        # Start Rotation
        config = self.load_config()
        interval_min = config.get("change_interval_minutes", 5)
        
        self.start_rotation_timer(interval_min)
        
        # Refresh every 300 seconds (5 minutes)
        GLib.timeout_add_seconds(interval_min * 60, self.update_cache_status)
        
        # Initialize the Log Management system
        log_manager = LogManager(log_path=LOG_FILE)
        
    def listen_for_tray(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allows quick restarts
            s.bind(('localhost', 65432))
            s.listen()
            while True:
                conn, addr = s.accept()
                with conn:
                    data = conn.recv(1024)
                    if data == b'SHOW_WINDOW':
                        GLib.idle_add(self.win.present)
                    elif data == b'ROTATE_NOW':
                        # Load current mode from config to pass into the resolver
                        config = self.load_config()
                        current_mode = config.get("mode", "auto")
                        
                        # Re-run resolution calculations and push changes to cache
                        GLib.idle_add(resolve_and_update_cache, current_mode)
                        GLib.idle_add(self.update_cache_status)
                        GLib.idle_add(self.refresh_ui)
                    elif data == b'QUIT_APP':
                        GLib.idle_add(self.cleanup_and_quit)

    def cleanup_and_quit(self):
        # 1. Terminate the tray satellite process
        if self.tray_process:
            self.tray_process.terminate()
        self.quit()
        
    def build_ui_content(self):
        # Clear existing content
        while self.main_box.get_first_child():
            self.main_box.remove(self.main_box.get_first_child())

        try:
            with open(CACHE_PATH, 'r') as f:
                data = json.load(f)
        except:
            data = {"error": "Cache file not found"}

        # Define mode from the cache data so the conditional checks work safely
        mode = data.get("mode", "auto")

        # Left Column
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        left_box.set_size_request(250, -1)
        
        overlay = Gtk.Overlay()
        img_path = data.get("current_wallpaper", "")
        picture = Gtk.Picture.new_for_filename(img_path) if os.path.exists(img_path) else Gtk.Picture()
        picture.set_size_request(250, 150)
        picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        overlay.set_child(picture)
        
        lbl_tod = Gtk.Label(label=f"{data.get('time_of_day', 'N/A')}")
        lbl_tod.set_halign(Gtk.Align.START); lbl_tod.set_valign(Gtk.Align.START)
        lbl_tod.set_margin_start(10); lbl_tod.set_margin_top(10)
        overlay.add_overlay(lbl_tod)
        
        lbl_modal = Gtk.Label(label=f"{data.get('modal', 'N/A')}")
        lbl_modal.set_halign(Gtk.Align.END); lbl_modal.set_valign(Gtk.Align.START)
        lbl_modal.set_margin_end(10); lbl_modal.set_margin_top(10)
        overlay.add_overlay(lbl_modal)
        left_box.append(overlay)

        if self.is_wal_installed():
            palette_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            palette_box.set_halign(Gtk.Align.START)
            
            lbl_icon = Gtk.Label(label="🎨")
            palette_box.append(lbl_icon)
            
            for hex_color in self.get_wal_colors():
                swatch = Gtk.Box()
                swatch.set_size_request(24, 24)
                css = Gtk.CssProvider()
                css.load_from_data(f"box {{ background-color: {hex_color}; border-radius: 5px; }}")
                swatch.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_USER)
                palette_box.append(swatch)
            left_box.append(palette_box)
            
        if self.is_openrgb_installed():
            rgb_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            rgb_box.set_halign(Gtk.Align.START)
            rgb_box.set_margin_top(5)
            
            lbl_rgb_icon = Gtk.Label(label="💡")
            rgb_profile = data.get("openrgb_profile", "Enabled")
            lbl_rgb_status = Gtk.Label(label=f"OpenRGB: {rgb_profile}")
            lbl_rgb_status.add_css_class("dim-label")
            
            rgb_box.append(lbl_rgb_icon)
            rgb_box.append(lbl_rgb_status)
            left_box.append(rgb_box)
        
        # Right Column
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        group = Adw.PreferencesGroup(title="Current Parameters")
        
        # Add Version row at the top of parameters
        version_row = Adw.ActionRow(title="Plaster Version", subtitle="v0.1.0-alpha.1")
        group.add(version_row)
        
        # Mode-based parameter filtering
        if mode == "auto":
            for key, value in data.items():
                if key not in ["time_of_day", "day_or_night", "modal", "static_wallpaper_dir"]:
                    group.add(Adw.ActionRow(title=key.replace('_', ' ').title(), subtitle=str(value)))
        elif mode == "static":
            for key, value in data.items():
                if key not in ["time_of_day", "day_or_night", "modal", "season", "root_wallpaper_dir", "mapping"]:
                    group.add(Adw.ActionRow(title=key.replace('_', ' ').title(), subtitle=str(value)))
               
        right_box.append(group)

        spacer = Gtk.Box(); spacer.set_vexpand(True); right_box.append(spacer)
        
        # Bottom button box for settings and logs
        bottom_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_btn_box.set_halign(Gtk.Align.END)
        bottom_btn_box.set_margin_bottom(10); bottom_btn_box.set_margin_end(10)
        
        logs_button = Gtk.Button(icon_name="text-x-generic-symbolic")
        logs_button.set_tooltip_text("View Logs")
        logs_button.connect("clicked", self.on_show_logs_clicked)
        
        gear_button = Gtk.Button(icon_name="preferences-system-symbolic")
        gear_button.set_tooltip_text("Settings")
        gear_button.connect("clicked", self.on_gear_clicked)
        
        bottom_btn_box.append(logs_button)
        bottom_btn_box.append(gear_button)
        right_box.append(bottom_btn_box)

        self.main_box.append(left_box)
        self.main_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        self.main_box.append(right_box)
    
    def refresh_ui(self):
        self.build_ui_content()
        
    def on_close_request(self, window):
        # Hide the window instead of destroying it
        window.hide()
        # Return True to prevent the window from being destroyed
        return True

    def restore_window(self):
        if self.win:
            self.win.show()
            self.win.present()
            
    def on_show_logs_clicked(self, button):
        if os.path.exists(LOG_FILE):
            try:
                subprocess.Popen(["xdg-open", LOG_FILE])
                log_event("Opened log file in system editor.")
            except Exception as e:
                log_event(f"Failed to open log file: {e}")
        else:
            log_event("Log file does not exist yet.")

class SettingsWindow(Adw.PreferencesWindow):
    def __init__(self, transient_for):
        super().__init__(transient_for=transient_for, modal=True, default_width=500, default_height=400)
        
        # 1. Setup UI Pages
        self.page = Adw.PreferencesPage(title="Settings", icon_name="preferences-system-symbolic")
        self.add(self.page)
        
        # 2. Add Mapping Page first so entries exist
        self.add_mapping_page()
        self.add_special_days_page() # added mapping for special days.
        
        # 3. Setup Settings Page groups...
        group_mode = Adw.PreferencesGroup(title="Mode Settings")
        self.page.add(group_mode)
        
        # Create the switch
        self.mode_switch = Adw.SwitchRow(title="Enable Auto-Mode")
        group_mode.add(self.mode_switch)
        
        row = Adw.ActionRow(title="Root Wallpaper Directory")
        self.root_dir_entry = Adw.EntryRow(title="Path")
        folder_btn = Gtk.Button(icon_name="folder-open-symbolic")
        folder_btn.connect("clicked", self.on_folder_button_clicked)
        row.add_suffix(self.root_dir_entry)
        row.add_suffix(folder_btn)
        group_mode.add(row)
        
        static_row = Adw.ActionRow(title="Static Wallpaper Directory")
        self.static_dir_entry = Adw.EntryRow(title="Path")
        static_folder_btn = Gtk.Button(icon_name="folder-open-symbolic")
        static_folder_btn.connect("clicked", self.on_static_folder_button_clicked)
        static_row.add_suffix(self.static_dir_entry)
        static_row.add_suffix(static_folder_btn)
        group_mode.add(static_row)
        
        adjustment = Gtk.Adjustment(value=5, lower=1, upper=60, step_increment=1, page_increment=5, page_size=0)
        self.interval_spin = Adw.SpinRow(title="Rotation Interval (minutes)", adjustment=adjustment)
        group_mode.add(self.interval_spin)
        
        group_loc = Adw.PreferencesGroup(title="Location Settings")
        self.page.add(group_loc)
        self.lat_entry = Adw.EntryRow(title="Latitude")
        self.lon_entry = Adw.EntryRow(title="Longitude")
        group_loc.add(self.lat_entry)
        group_loc.add(self.lon_entry)
        
        # 4. Load Data
        self.load_current_settings()
        
        save_btn = Gtk.Button(label="Save Settings")
        save_btn.connect("clicked", self.save_settings)
        group_loc.add(save_btn)

    def on_static_folder_button_clicked(self, button):
        dialog = Gtk.FileChooserNative.new(
            "Select Static Wallpaper Directory",
            self,
            Gtk.FileChooserAction.SELECT_FOLDER,
            "_Open",
            "_Cancel"
        )
        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                folder = dialog.get_file().get_path()
                self.static_dir_entry.set_text(folder)
            dialog.destroy()
        dialog.connect("response", on_response)
        dialog.show()
    
    def add_mapping_page(self):
        self.season_entries = {
            "Spring": Adw.EntryRow(title="Spring"),
            "Summer": Adw.EntryRow(title="Summer"),
            "Autumn": Adw.EntryRow(title="Autumn"),
            "Winter": Adw.EntryRow(title="Winter")
        }
        
        self.month_entries = {
            "January": Adw.EntryRow(title="January"),
            "February": Adw.EntryRow(title="February"),
            "March": Adw.EntryRow(title="March"),
            "April": Adw.EntryRow(title="April"),
            "May": Adw.EntryRow(title="May"),
            "June": Adw.EntryRow(title="June"),
            "July": Adw.EntryRow(title="July"),
            "August": Adw.EntryRow(title="August"),
            "September": Adw.EntryRow(title="September"),
            "October": Adw.EntryRow(title="October"),
            "November": Adw.EntryRow(title="November"),
            "December": Adw.EntryRow(title="December")
        }
        
        page = Adw.PreferencesPage(title="Wallpaper Mapping", icon_name="folder-symbolic")
        self.add(page)
        
        group_s = Adw.PreferencesGroup(title="Season Mappings")
        page.add(group_s)
        for entry in self.season_entries.values():
            group_s.add(entry)
            
        group_m = Adw.PreferencesGroup(title="Month Mappings")
        page.add(group_m)
        for entry in self.month_entries.values():
            group_m.add(entry)

    def load_current_settings(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                data = json.load(f)
                self.interval_spin.set_value(data.get("change_interval_minutes", 5))
                self.mode_switch.set_active(data.get("mode", "auto") == "auto")
                self.root_dir_entry.set_text(data.get("root_wallpaper_dir", ""))
                self.static_dir_entry.set_text(data.get("static_wallpaper_dir", ""))
                loc = data.get("location", {})
                self.lat_entry.set_text(str(loc.get("latitude", "")))
                self.lon_entry.set_text(str(loc.get("longitude", "")))
                
                mapping = data.get("mapping", {})
                
                # Load Seasons
                seasons = mapping.get("seasons", {})
                for season, entry in self.season_entries.items():
                    entry.set_text(seasons.get(season, ""))
                    
                # Load Months
                months = mapping.get("months", {})
                for month, entry in self.month_entries.items():
                    entry.set_text(months.get(month, ""))
    
    def save_settings(self, button):
        config_path = os.path.expanduser("~/.config/plaster/config.json")
        
        # Determine the mode string based on the switch state
        mode_val = "auto" if self.mode_switch.get_active() else "static"
        
        updated_mapping = {
            "seasons": {season: entry.get_text() for season, entry in self.season_entries.items()},
            "months": {month: entry.get_text() for month, entry in self.month_entries.items()}
        }

        # 1. Save exclusively to the configuration file (Source of Truth)
        data = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                try: data = json.load(f)
                except: pass

        data.update({
            "mode": mode_val,
            "change_interval_minutes": int(self.interval_spin.get_value()),
            "root_wallpaper_dir": self.root_dir_entry.get_text(),
            "static_wallpaper_dir": self.static_dir_entry.get_text(),
            "location": {
                "latitude": float(self.lat_entry.get_text() or 0),
                "longitude": float(self.lon_entry.get_text() or 0)
            },
            "mapping": updated_mapping
        })
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=4)
            
        # 2. Explicitly trigger the resolver to calculate and update the cache file properly
        resolve_and_update_cache(mode=mode_val)
        
        # 3. Refresh the main application UI immediately
        if self.get_transient_for() and hasattr(self.get_transient_for(), 'refresh_ui'):
            self.get_transient_for().refresh_ui()
            
        self.close()
    
    def on_folder_button_clicked(self, button):
        dialog = Gtk.FileChooserNative.new(
            "Select Wallpaper Directory",
            self,
            Gtk.FileChooserAction.SELECT_FOLDER,
            "_Open",
            "_Cancel"
        )
        
        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                folder = dialog.get_file().get_path()
                self.root_dir_entry.set_text(folder)
            dialog.destroy()
            
        dialog.connect("response", on_response)
        dialog.show()
        
        def add_mapping_page(self):
            page = Adw.PreferencesPage(title="Wallpaper Mapping", icon_name="folder-symbolic")
            self.add(page)
    
            group = Adw.PreferencesGroup(title="Season Mappings")
            page.add(group)
    
            # Create an entry for each season
            self.season_entries = {
                "Spring": Adw.EntryRow(title="Spring Directory Name"),
                "Summer": Adw.EntryRow(title="Summer Directory Name"),
                "Autumn": Adw.EntryRow(title="Autumn Directory Name"),
                "Winter": Adw.EntryRow(title="Winter Directory Name")
            }
    
            for entry in self.season_entries.values():
                group.add(entry)
                
            # Create an entry for each month
            self.month_entries = {
                "January": Adw.EntryRow(title="January Directory Name"),
                "February": Adw.EntryRow(title="February Directory Name"),
                "March": Adw.EntryRow(title="March Directory Name"),
                "April": Adw.EntryRow(title="April Directory Name"),
                "May": Adw.EntryRow(title="May Directory Name"),
                "June": Adw.EntryRow(title="June Directory Name"),
                "July": Adw.EntryRow(title="July Directory Name"),
                "August": Adw.EntryRow(title="August Directory Name"),
                "September": Adw.EntryRow(title="September Directory Name"),
                "October": Adw.EntryRow(title="October Directory Name"),
                "November": Adw.EntryRow(title="November Directory Name"),
                "December": Adw.EntryRow(title="December Directory Name")
            }
    
            for entry in self.month_entries.values():
                group.add(entry)
                
    def add_special_days_page(self):
        page = Adw.PreferencesPage(title="Special Days", icon_name="x-office-calendar-symbolic")
        self.add(page)
        
        # Group for adding a new special day
        group_add = Adw.PreferencesGroup(title="Add New Special Day", description="Define custom wallpapers for specific dates (MM-DD)")
        page.add(group_add)
        
        self.special_name_entry = Adw.EntryRow(title="Event Name (e.g. Anniversary)")
        group_add.add(self.special_name_entry)
        
        self.special_date_entry = Adw.EntryRow(title="Date (MM-DD)")
        group_add.add(self.special_date_entry)
        
        # Path row with file picker button
        path_row = Adw.ActionRow(title="Wallpaper Path")
        self.special_path_entry = Adw.EntryRow(title="Path to image or directory")
        path_btn = Gtk.Button(icon_name="folder-open-symbolic")
        path_btn.connect("clicked", self.on_special_folder_button_clicked)
        path_row.add_suffix(self.special_path_entry)
        path_row.add_suffix(path_btn)
        group_add.add(path_row)
        
        add_btn = Gtk.Button(label="Add Special Day")
        add_btn.set_margin_top(10)
        add_btn.set_margin_bottom(10)
        add_btn.connect("clicked", self.on_add_special_day_clicked)
        group_add.add(add_btn)
        
        # Group for displaying existing special days
        self.group_list = Adw.PreferencesGroup(title="Configured Special Days")
        page.add(self.group_list)
        
        self.populate_special_days_list()

    def populate_special_days_list(self):
        # Clear existing rows if reloading
        # (Optional: keep track of dynamically added rows to clear them cleanly)
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                try:
                    data = json.load(f)
                    special_days = data.get("special_days", [])
                    for event in special_days:
                        row = Adw.ActionRow(
                            title=f"{event.get('name')} ({event.get('date')})",
                            subtitle=event.get('wallpaper_path')
                        )
                        self.group_list.add(row)
                except:
                    pass

    def on_special_folder_button_clicked(self, button):
        dialog = Gtk.FileChooserNative.new(
            "Select Special Day Wallpaper",
            self,
            Gtk.FileChooserAction.OPEN,
            "_Open",
            "_Cancel"
        )
        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                file_path = dialog.get_file().get_path()
                self.special_path_entry.set_text(file_path)
            dialog.destroy()
        dialog.connect("response", on_response)
        dialog.show()

    def on_add_special_day_clicked(self, button):
        name = self.special_name_entry.get_text()
        date_str = self.special_date_entry.get_text()
        path = self.special_path_entry.get_text()
        
        if name and date_str and path:
            # Import your backend helper function
            from plaster.special_days import add_special_day
            add_special_day(name, date_str, path, target="config")
            
            # Clear entries and refresh list view
            self.special_name_entry.set_text("")
            self.special_date_entry.set_text("")
            self.special_path_entry.set_text("")
            
            # Re-populate list group
            # (Alternatively, you can append the new Adw.ActionRow directly here)
            row = Adw.ActionRow(title=f"{name} ({date_str})", subtitle=path)
            self.group_list.add(row)
        
app = WallpaperApp()
app.run(None)
