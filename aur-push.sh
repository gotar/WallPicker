#!/usr/bin/env bash
set -euo pipefail

# AUR Push Script - Reliable method using direct clone
# This avoids git subtree merge conflicts that plague the subtree approach

AUR_REPO="aur@aur.archlinux.org:wallpicker.git"
TMP_DIR="/tmp/aur-wallpicker-$$"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/aur"

echo "🚀 Pushing WallPicker to AUR..."

# Clone AUR repo
echo "📥 Cloning AUR repository..."
git clone "$AUR_REPO" "$TMP_DIR"

# Copy updated files
echo "📋 Copying PKGBUILD and .SRCINFO..."
cp "$SOURCE_DIR/PKGBUILD" "$TMP_DIR/"
cp "$SOURCE_DIR/.SRCINFO" "$TMP_DIR/"

# Check for changes
cd "$TMP_DIR"
if git diff --quiet; then
  echo "✅ No changes to push - AUR is already up to date"
  rm -rf "$TMP_DIR"
  exit 0
fi

# Show diff
echo "📝 Changes to be pushed:"
git diff

# Commit and push
VERSION=$(grep '^pkgver=' PKGBUILD | cut -d= -f2)
echo "📦 Committing version $VERSION..."
git add .
git commit -m "Update to v$VERSION"

echo "⬆️  Pushing to AUR..."
git push

# Cleanup
cd -
rm -rf "$TMP_DIR"

echo "✅ Successfully pushed v$VERSION to AUR!"
