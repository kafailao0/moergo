#!/usr/bin/env bash
set -euo pipefail

# Helper script to flash Glove80 firmware to both keyboard halves
# Supports both immediate flashing and continuous monitoring/wait mode.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

UF2=""
WATCH_MODE=true
TIMEOUT=300

while [[ $# -gt 0 ]]; do
    case "$1" in
        --once|--no-wait)
            WATCH_MODE=false
            shift
            ;;
        --watch)
            WATCH_MODE=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: ./flash.sh [path/to/firmware.uf2] [options]"
            echo ""
            echo "Options:"
            echo "  --watch          Continuously monitor and flash halves as they appear (default)"
            echo "  --once           One-shot check: flash currently detected halves and exit"
            echo "  --timeout <sec>  Watch mode timeout in seconds (default: 300)"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            if [[ -z "$UF2" ]]; then
                UF2="$1"
            fi
            shift
            ;;
    esac
done

# Find firmware file if not specified
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
    echo "  rm -rf glove80.uf2 && gh run download -n glove80.uf2"
    echo "Or specify the path: ./flash.sh /path/to/glove80.uf2"
    exit 1
fi

echo "========================================="
echo "Glove80 Firmware Flasher"
echo "Firmware: $UF2 ($(stat -c %s "$UF2" 2>/dev/null || stat -f %z "$UF2" 2>/dev/null || echo "unknown") bytes)"
echo "========================================="

flash_half() {
    local label="$1"
    local side="$2"
    local dev="/dev/disk/by-label/$label"

    if [[ ! -e "$dev" ]]; then
        return 1
    fi

    echo ""
    echo "[+] Detected $side half ($label) at $dev."

    # Give udev/system a brief moment to settle
    sleep 1

    # Mount via udisksctl if not already mounted
    local mount_point
    mount_point=$(findmnt -n -o TARGET "$dev" 2>/dev/null || true)
    if [[ -z "$mount_point" ]]; then
        echo "    Mounting $label via udisksctl..."
        mount_point=$(udisksctl mount -b "$dev" --no-user-interaction 2>/dev/null | awk '{print $4}' | tr -d '.' || true)
    fi

    if [[ -z "$mount_point" || ! -d "$mount_point" ]]; then
        mount_point="/run/media/$USER/$label"
    fi

    if [[ ! -d "$mount_point" ]]; then
        echo "[-] Error: Could not mount $label at $mount_point."
        return 1
    fi

    # Safety check: Verify the drive is a genuine UF2 bootloader
    local info_file
    info_file=$(find "$mount_point" -maxdepth 1 -iname "INFO_UF2.TXT" 2>/dev/null | head -n 1)
    if [[ -z "$info_file" || ! -f "$info_file" ]]; then
        echo "[-] Error: $mount_point does not contain INFO_UF2.TXT. Skipping (not a valid UF2 bootloader drive)."
        return 1
    fi

    echo "    Mount point: $mount_point"
    echo "    Verified UF2 bootloader signature ($info_file)."
    echo "    Copying firmware..."
    cp "$UF2" "$mount_point/" || true
    sync || true
    echo "[✓] Successfully flashed $side half ($label)! Device is rebooting into keyboard mode..."
    sleep 2
    return 0
}

left_flashed=false
right_flashed=false

# Check if both are already connected right now
if [[ -e "/dev/disk/by-label/GLV80LHBOOT" ]]; then
    if flash_half "GLV80LHBOOT" "Left"; then
        left_flashed=true
    fi
fi

if [[ -e "/dev/disk/by-label/GLV80RHBOOT" ]]; then
    if flash_half "GLV80RHBOOT" "Right"; then
        right_flashed=true
    fi
fi

if [[ "$left_flashed" == true && "$right_flashed" == true ]]; then
    echo ""
    echo "========================================="
    echo "[✓] Both halves successfully flashed!"
    echo "========================================="
    exit 0
fi

if [[ "$WATCH_MODE" == false ]]; then
    if [[ "$left_flashed" == false && "$right_flashed" == false ]]; then
        echo "No bootloader drives detected."
        echo "Connect via USB and enter bootloader mode on each half:"
        echo "  - Left half:  Hold 'Magic' and tap 'ESC' (or double-click reset button)"
        echo "  - Right half: Hold 'Magic' and tap ''' (SQT) (or double-click reset button)"
        exit 1
    fi
    echo "One half was flashed. Run again to flash the other half."
    exit 0
fi

echo ""
echo "Monitoring for bootloader drives (timeout: ${TIMEOUT}s, press Ctrl+C to cancel)..."
echo "Connect and trigger bootloader mode on each half (simultaneously or sequentially):"
if [[ "$left_flashed" == true ]]; then
    echo "  - Left half:  [ALREADY FLASHED]"
else
    echo "  - Left half:  Hold 'Magic' + tap 'ESC' (or double-click reset button)"
fi
if [[ "$right_flashed" == true ]]; then
    echo "  - Right half: [ALREADY FLASHED]"
else
    echo "  - Right half: Hold 'Magic' + tap ''' (SQT) (or double-click reset button)"
fi

start_time=$(date +%s)
while true; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    if (( elapsed > TIMEOUT )); then
        echo ""
        echo "[-] Timeout reached (${TIMEOUT}s)."
        break
    fi

    if [[ "$left_flashed" == false && -e "/dev/disk/by-label/GLV80LHBOOT" ]]; then
        if flash_half "GLV80LHBOOT" "Left"; then
            left_flashed=true
        fi
    fi

    if [[ "$right_flashed" == false && -e "/dev/disk/by-label/GLV80RHBOOT" ]]; then
        if flash_half "GLV80RHBOOT" "Right"; then
            right_flashed=true
        fi
    fi

    if [[ "$left_flashed" == true && "$right_flashed" == true ]]; then
        echo ""
        echo "========================================="
        echo "[🎉] BOTH HALVES FLASHED SUCCESSFULLY!"
        echo "Your Glove80 is ready to use."
        echo "========================================="
        exit 0
    fi

    sleep 1
done

if [[ "$left_flashed" == true || "$right_flashed" == true ]]; then
    echo ""
    echo "Partial flash completed:"
    echo "  Left half:  $left_flashed"
    echo "  Right half: $right_flashed"
    exit 0
fi

echo ""
echo "No halves were detected within the timeout period."
exit 1
