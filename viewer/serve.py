#!/usr/bin/env python3
"""
Simple HTTP server for MoErgo Layout Viewer.
Listens on the Tailscale IP (or 0.0.0.0) so you can open it on your laptop and phone.
"""

import http.server
import socketserver
import os
import sys
import subprocess

PORT = 8088
VIEWER_DIR = os.path.dirname(os.path.abspath(__file__))

def get_tailscale_ip():
    try:
        res = subprocess.run(['tailscale', 'ip', '-4'], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return None

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else PORT
    ts_ip = get_tailscale_ip()

    # Change to viewer directory
    os.chdir(VIEWER_DIR)

    # Allow dual-stack / binding
    class Handler(http.server.SimpleHTTPRequestHandler):
        extensions_map = {
            **http.server.SimpleHTTPRequestHandler.extensions_map,
            '.json': 'application/json',
            '.webmanifest': 'application/manifest+json',
        }

        def end_headers(self):
            # Cache control for easy live updates
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Service-Worker-Allowed', '/')
            super().end_headers()

    # Bind to 0.0.0.0 so both Tailscale and localhost work
    class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

        def server_bind(self):
            import socket
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, 'SO_REUSEPORT'):
                try:
                    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except Exception:
                    pass
            super().server_bind()

    server = ThreadedHTTPServer(('0.0.0.0', port), Handler)

    print("\n" + "=" * 60)
    print("  ⌨️  MoErgo Layout Visualizer is running!")
    print("=" * 60)
    print(f"  • Local access:       http://localhost:{port}/")
    if ts_ip:
        print(f"  • Tailscale access:   http://{ts_ip}:{port}/")
        print(f"    (Open this on your laptop or phone connected to Tailscale)")
    print("=" * 60)
    print("  Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        server.server_close()

if __name__ == '__main__':
    main()
