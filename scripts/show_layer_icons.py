#!/usr/bin/env python3
"""
Render MoErgo Layer Icons in the terminal using Kitty Graphic Protocol.
Also provides links to the interactive web selector at http://localhost:8088/layer-icons.html.
"""

import os
import sys
import base64
import argparse
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEWS_DIR = os.path.join(BASE_DIR, 'viewer', 'icons_preview')
CONTACT_SHEET_PNG = os.path.join(PREVIEWS_DIR, 'contact_sheet.png')
STRIPS_PNG = os.path.join(PREVIEWS_DIR, 'strips.png')

def get_tailscale_ip():
    try:
        res = subprocess.run(['tailscale', 'ip', '-4'], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return None

def print_kitty_png(png_path, max_width_cols=None):
    """Outputs an image to the terminal using Kitty Graphic Protocol."""
    if not os.path.exists(png_path):
        print(f"Error: Preview image {png_path} not found.", file=sys.stderr)
        return False

    with open(png_path, 'rb') as f:
        data = f.read()

    b64 = base64.b64encode(data).decode('ascii')
    chunk_size = 4096
    total_len = len(b64)

    ctrl_parts = ["a=T", "f=100"]
    if max_width_cols:
        ctrl_parts.append(f"c={max_width_cols}")
    ctrl_str = ",".join(ctrl_parts)

    for i in range(0, total_len, chunk_size):
        chunk = b64[i:i + chunk_size]
        is_last = (i + chunk_size >= total_len)
        m = 0 if is_last else 1
        if i == 0:
            sys.stdout.write(f"\033_G{ctrl_str},m={m};{chunk}\033\\")
        else:
            sys.stdout.write(f"\033_Gm={m};{chunk}\033\\")
    sys.stdout.write("\n")
    sys.stdout.flush()
    return True

def main():
    parser = argparse.ArgumentParser(description="View MoErgo Layer Icons via Kitty Graphic Protocol or Web")
    parser.add_argument('--sheet', action='store_true', help="Render full 2-column contact sheet (default)")
    parser.add_argument('--strips', action='store_true', help="Render single-column vertical layer strips")
    parser.add_argument('--cols', type=int, default=None, help="Terminal column width for Kitty image scaling")
    args = parser.parse_args()

    ts_ip = get_tailscale_ip()

    print("\033[1;36m" + "=" * 70 + "\033[0m")
    print("\033[1;37m  ⌨️  MoErgo Layer Icons Design Lab — Terminal Preview\033[0m")
    print("\033[1;36m" + "=" * 70 + "\033[0m\n")

    print("  \033[1;33m🌐 Interactive Web Selector & Live Simulator:\033[0m")
    print("     • Local:     \033[1;34mhttp://localhost:8088/layer-icons.html\033[0m")
    if ts_ip:
        print(f"     • Tailscale: \033[1;34mhttp://{ts_ip}:8088/layer-icons.html\033[0m")
    print("     • Layout:    \033[1;34mhttp://localhost:8088/\033[0m (Current Layout Visualizer)\n")

    print("  \033[1;32m🖼️  Rendering via Kitty Graphic Protocol below...\033[0m\n")

    target_png = STRIPS_PNG if args.strips else CONTACT_SHEET_PNG
    print_kitty_png(target_png, max_width_cols=args.cols)

    print("\n\033[1;36m" + "-" * 70 + "\033[0m")
    print("\033[1;37m  Layer Design Options Summary:\033[0m")
    print("\033[1;36m" + "-" * 70 + "\033[0m")

    summary_layers = [
        ("Layer 0: Base [CHOSEN]", "Option 1: Keyboard (rect + keys) ✓"),
        ("Layer 1: PC (Linux)", "Option 1: Linux Tux Penguin | Option 2: Shell Prompt >_ | Option 3: Linux Workstation"),
        ("Layer 2: Gaming [CHOSEN]", "Option 1: Gamepad Controller ✓"),
        ("Layer 3: SymbolNav [CHOSEN]", "Option 2: Code Brackets </> ✓"),
        ("Layer 4: Keypad [CHOSEN]", "Option 1: Pocket Calculator ✓"),
        ("Layer 5: NumRow", "Option 1: Normal Font 123 | Option 2: Keycap Pill 123 | Option 3: Hash Sign #"),
        ("Layer 6: Magic", "Option 1: Lucide Magic Wand | Option 2: Star-Tipped Wand | Option 3: Radiance Wand Burst"),
        ("Layer 7: Factory [CHOSEN]", "Option 1: Factory Building ✓"),
        ("Layer 8: Mouse [CHOSEN]", "Option 1: Ergo Mouse Body ✓"),
        ("Layer 9: Sniper [CHOSEN]", "Option 1: Target Reticle ✓"),
    ]

    for title, opts in summary_layers:
        print(f"  \033[1;35m• {title:<20}\033[0m \033[0;37m{opts}\033[0m")

    print("\n\033[1;36m" + "=" * 70 + "\033[0m\n")

if __name__ == '__main__':
    main()
