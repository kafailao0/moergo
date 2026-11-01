#!/usr/bin/env python3
"""
Automated screenshot generator for MoErgo Layout Visualizer.
Captures key visualizer features across Glove80 and Go60.
"""

import os
import sys
import time
import socket
import threading
import subprocess
import http.server
import socketserver

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEWER_DIR = os.path.join(BASE_DIR, 'viewer')
OUTPUT_DIR = os.path.join(BASE_DIR, 'docs', 'screenshots')

SCREENSHOTS = [
    {
        "filename": "01_glove80_simulate_base.png",
        "query": "?kb=glove80&mode=simulate",
        "description": "Glove80 base layout in simulation mode with home-row mods and thumb clusters",
        "window_size": "1440,900"
    },
    {
        "filename": "02_glove80_symbol_nav_rgb.png",
        "query": "?kb=glove80&mode=simulate&layer=3&rgb=on",
        "description": "SymbolNav layer active on Glove80 with vibrant per-key RGB underglow",
        "window_size": "1440,900"
    },
    {
        "filename": "03_go60_compact_simulate.png",
        "query": "?kb=go60&mode=simulate",
        "description": "Go60 60-key compact split layout simulation",
        "window_size": "1440,900"
    },
    {
        "filename": "04_inspect_mode_key_details.png",
        "query": "?kb=glove80&mode=inspect&layer=0&inspect=73",
        "description": "Inspect mode showing raw ZMK behaviors, parameters, and layer jump badges",
        "window_size": "1440,900"
    },
    {
        "filename": "05_rgb_color_palette_modal.png",
        "query": "?kb=glove80&mode=simulate&layer=3&rgb=on&modal=colors",
        "description": "Built-in RGB Underglow color reference modal",
        "window_size": "1440,900"
    },
    {
        "filename": "06_search_and_filter.png",
        "query": "?kb=glove80&mode=simulate&search=Media",
        "description": "Keycode search filtering and cross-keyboard highlighting",
        "window_size": "1440,900"
    }
]

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def run_server(port, stop_event):
    os.chdir(VIEWER_DIR)
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass # Suppress logging
    with socketserver.TCPServer(('127.0.0.1', port), QuietHandler) as httpd:
        httpd.timeout = 0.5
        while not stop_event.is_set():
            httpd.handle_request()

def capture_screenshot(url, output_path, window_size="1440,900"):
    cmd = [
        "chromium-browser",
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        f"--window-size={window_size}",
        "--virtual-time-budget=2000",
        f"--screenshot={output_path}",
        url
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"Screenshot failed: {res.stderr}\nCommand: {' '.join(cmd)}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    port = find_free_port()
    stop_event = threading.Event()
    server_thread = threading.Thread(target=run_server, args=(port, stop_event), daemon=True)
    server_thread.start()
    time.sleep(0.5)

    print(f"Server started on port {port}. Capturing {len(SCREENSHOTS)} screenshots...")
    try:
        for idx, shot in enumerate(SCREENSHOTS, start=1):
            out_file = os.path.join(OUTPUT_DIR, shot['filename'])
            target_url = f"http://127.0.0.1:{port}/{shot['query']}"
            print(f"[{idx}/{len(SCREENSHOTS)}] Capturing {shot['filename']}...")
            start_t = time.time()
            capture_screenshot(target_url, out_file, shot['window_size'])
            dur = time.time() - start_t
            size_kb = os.path.getsize(out_file) / 1024
            print(f"    ✓ Saved {shot['filename']} ({size_kb:.1f} KB in {dur:.2f}s)")
    finally:
        stop_event.set()
        server_thread.join(timeout=1.0)

    print(f"\nAll screenshots captured successfully to {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
