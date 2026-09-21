#!/usr/bin/env bash
set -euo pipefail

# Helper script to flash Glove80 firmware to both keyboard halves

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find firmware file
UF2="${1:-}"
if [[ -z "$UF2" ]]; then
    if [[ -f "$SCRIPT_DIR/glove80.uf2/glove80.uf2" ]]; then
        UF2="$SCRIPT_DIR/glove80.uf2/glove80.uf2"
    elif [[ -f "$SCRIPT_DIR/glove80.uf2" ]]; then
        UF2="$SCRIPT_DIR/glove80.uf2"
    elif [[ -f "$HOME/Downloads/glove80.uf2" ]]; then
        UF2="$HOME/Downloads/glove80.uf2"
    fi
fi

if [[ -z "$UF2" || ! -f "$UF2" ]]; then
    echo "Error: Firmware file not found."
    echo "Download the latest firmware from GitHub Actions using:"
    echo "  gh run download -n glove80.uf2"
    echo "Or specify the path: ./flash.sh /path/to/glove80.uf2"
    exit 1
fi

echo "==> Using firmware: $UF2"

flash_half() {
    local label="$1"
    local side="$2"
    local dev="/dev/disk/by-label/$label"

    if [[ ! -e "$dev" ]]; then
        echo "[-] $side half ($label) not detected."
        echo "    Put the $side half into bootloader mode (Magic + Bootloader, or double-click reset button)."
        return 1
    fi

    echo "[+] Found $side half ($label)."

    # Mount via udisksctl if not already mounted
    local mount_point
    mount_point=$(findmnt -n -o TARGET "$dev" 2>/dev/null || true)
    if [[ -z "$mount_point" ]]; then
        echo "    Mounting $label..."
        mount_point=$(udisksctl mount -b "$dev" --no-user-interaction 2>/dev/null | awk '{print $4}' | tr -d '.' || true)
    fi

    if [[ -z "$mount_point" || ! -d "$mount_point" ]]; then
        # Fallback to standard path
        mount_point="/run/media/$USER/$label"
    fi

    if [[ ! -d "$mount_point" ]]; then
        echo "[-] Error: Could not mount $label."
        return 1
    fi

    echo "    Flashing $UF2 to $mount_point..."
    cp "$UF2" "$mount_point/" || true
    sync || true
    echo "[✓] Successfully flashed $side half ($label)!"
}

flashed_any=false

if flash_half "GLV80LHBOOT" "Left"; then
    flashed_any=true
fi

if flash_half "GLV80RHBOOT" "Right"; then
    flashed_any=true
fi

if [[ "$flashed_any" == false ]]; then
    echo ""
    echo "No bootloader drives detected."
    echo "Connect the keyboard via USB and enter bootloader mode on each half:"
    echo "  - Via keymap: Hold 'Magic' key and tap 'Bootloader'"
    echo "  - Via hardware: Double-click the reset button on the thumb cluster"
    exit 1
fi

echo ""
echo "[✓] Flashing complete!"
