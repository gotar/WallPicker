#!/bin/bash

# Installation script for WallPicker

set -e

INSTALL_DIR="$HOME/.local/share/wallpicker"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing WallPicker..."

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3."
    exit 1
fi

# Install system dependencies
echo "Installing system dependencies..."
if command -v apt-get &> /dev/null; then
    # Ubuntu/Debian
    sudo apt-get update
    sudo apt-get install -y python3-pip python3-gi libgirepository1.0-dev \
        gir1.2-gtk-4.0 gir1.2-adw-1
elif command -v dnf &> /dev/null; then
    # Fedora
    sudo dnf install -y python3-pip python3-gobject gtk4 libadwaita-devel
elif command -v pacman &> /dev/null; then
    # Arch
    sudo pacman -S --needed python python-pip python-gobject gtk4 \
        libadwaita
else
    echo "Warning: Could not detect package manager. Please install manually."
    echo "Required: python3, python3-gobject, gtk4, libadwaita"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --user -r "$SCRIPT_DIR/requirements.txt"

# Create installation directory
echo "Creating installation directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p ~/.config/wallpicker
mkdir -p ~/.cache/wallpicker/thumbnails

# Copy source files
echo "Copying source files..."
cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/data" "$INSTALL_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/wallpicker" "$INSTALL_DIR/"

# Make entry point executable
chmod +x "$INSTALL_DIR/wallpicker"

# Create symlink in bin directory
echo "Creating executable symlink..."
ln -sf "$INSTALL_DIR/wallpicker" "$BIN_DIR/wallpicker"

# Install icon
echo "Installing icon..."
mkdir -p "$ICON_DIR"
if [ -f "$SCRIPT_DIR/data/wallpaper-icon.svg" ]; then
    cp "$SCRIPT_DIR/data/wallpaper-icon.svg" "$ICON_DIR/wallpicker.svg"
fi

# Install desktop entry
echo "Creating desktop entry..."
mkdir -p "$DESKTOP_DIR"

if [ -f "$SCRIPT_DIR/wallpicker.desktop" ]; then
    # Use existing desktop file and update paths
    sed "s|Exec=/home/gotar/Programowanie/wallpicker/launcher.sh|Exec=$BIN_DIR/wallpicker|g" \
        "$SCRIPT_DIR/wallpicker.desktop" > "$DESKTOP_DIR/wallpicker.desktop"
    sed -i "s|Icon=/home/gotar/Programowanie/wallpicker/data/wallpaper-icon.svg|Icon=$ICON_DIR/wallpicker.svg|g" \
        "$DESKTOP_DIR/wallpicker.desktop"
else
    # Fallback: create desktop entry from scratch
    cat > "$DESKTOP_DIR/wallpicker.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=WallPicker
Comment=Browse and set wallpapers from Wallhaven and local collection
Exec=$BIN_DIR/wallpicker
Icon=$ICON_DIR/wallpicker.svg
Terminal=false
StartupNotify=true
Categories=Utility;Graphics;
Keywords=wallpaper;background;desktop;wallhaven;
X-GNOME-UsesNotifications=true
EOF
fi

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

echo ""
echo "Installation complete!"
echo ""
echo "To run WallPicker:"
echo "  - From terminal: wallpicker"
echo "  - From menu: WallPicker"
echo ""
echo "Note: Make sure ~/.local/bin is in your PATH. Add this to your ~/.bashrc or ~/.zshrc:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo ""
