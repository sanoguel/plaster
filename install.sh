#!/usr/bin/env bash
set -e

# Define user-local installation directories
INSTALL_DIR="$HOME/.local/share/plaster"
APP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

echo "Installing Plaster to user space..."

# 1. Create target directories if they don't exist
mkdir -p "$INSTALL_DIR"
mkdir -p "$APP_DIR"
mkdir -p "$ICON_DIR"

# 2. Copy project files to the local share directory
# (Assuming install.sh is run from the root of your source repo)
cp -r . "$INSTALL_DIR/"

# 3. Set up the virtual environment inside the install path
echo "Setting up virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip

# (Optional: if you have a requirements.txt)
if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
fi

# 4. Create the launch script dynamically inside the installation directory
cat << EOF > "$INSTALL_DIR/plaster-launch.sh"
#!/usr/bin/env bash
cd "$INSTALL_DIR"
exec python3 -m plaster.main
EOF
chmod +x "$INSTALL_DIR/plaster-launch.sh"

# 5. Install the .desktop shortcut
cat << EOF > "$APP_DIR/plaster.desktop"
[Desktop Entry]
Type=Application
Name=Plaster
Comment=Dynamic Wallpaper Manager
Exec=$INSTALL_DIR/plaster-launch.sh
Icon=plaster
Terminal=false
Categories=Utility;
EOF

# 6. Install the icon (assuming you have plaster.png or plaster.svg in assets)
if [ -f "$INSTALL_DIR/assets/plaster.png" ]; then
    cp "$INSTALL_DIR/assets/plaster.png" "$ICON_DIR/plaster.png"
fi

# 7. Refresh desktop database
update-desktop-database "$APP_DIR"

echo "Installation complete! Plaster is now available in your application menu."
