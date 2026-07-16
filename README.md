# Plaster

Plaster is a Python-based desktop utility designed to automate wallpaper rotation, theme generation, and hardware lighting control via OpenRGB. It follows Linux XDG standards for configuration and is built to integrate seamlessly with your desktop environment.

## Features

*   **Automated Wallpaper Management:** Keep your Gnome desktop fresh with automated rotations based on your directory structure.
*   **Theme Integration:** Automatically matches your system theme and generates color palettes.
*   **OpenRGB Sync:** Sync your hardware lighting to complement your current wallpaper and environment.
*   **XDG Compliant:** Clean configuration management using standard `~/.config` and `~/.cache` locations.

## Preview

| Light Mode | Dark Mode |
| :---: | :---: |
| ![Plaster Light Mode](assets/plaster-image.png) | ![Plaster Dark Mode](assets/plaster-image.png) |

*(Note: The interface dynamically adapts to your system theme.)*

## Requirements & Installation

### Prerequisites
* Python 3.10 or higher
* GTK 4 / GNOME desktop environment (for runtime configuration)

### Dependencies
This project relies on the modules listed in `requirements.txt`. Key components include:
* `requests` - For handling core API interactions.
* `pygobject` - For native GNOME interface hooks.

### Installation

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone [https://github.com/sanoguel/plaster.git](https://github.com/sanoguel/plaster.git)
   cd plaster
   ```

2. Create and activate an isolated virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install all required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. (Optional) Register the application menu shortcut for your user profile:
   ```bash
   cp plaster.desktop ~/.local/share/applications/
   update-desktop-database ~/.local/share/applications
   ```

