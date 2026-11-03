#!/usr/bin/env python3
"""
Generate PNG previews for all 30 layer icon designs and a full visual contact sheet.
Uses headless Chromium to rasterize crisp high-DPI images for the Kitty Graphic Protocol
and web visualizer.
"""

import os
import sys
import subprocess
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEWS_DIR = os.path.join(BASE_DIR, 'viewer', 'icons_preview')
os.makedirs(PREVIEWS_DIR, exist_ok=True)

# 30 Vector icons categorized by layer
LAYERS_DATA = [
    {
        'id': 'Base',
        'idx': 0,
        'title': 'Layer 0: Base',
        'desc': 'Primary Mac typing layer with home row mods',
        'options': [
            {'id': 'base_keyboard', 'name': 'Keyboard', 'svg': '<rect x="2" y="4" width="20" height="16" rx="2"/><line x1="6" y1="8" x2="6.01" y2="8"/><line x1="10" y1="8" x2="10.01" y2="8"/><line x1="14" y1="8" x2="14.01" y2="8"/><line x1="18" y1="8" x2="18.01" y2="8"/><line x1="6" y1="12" x2="6.01" y2="12"/><line x1="10" y1="12" x2="10.01" y2="12"/><line x1="14" y1="12" x2="14.01" y2="12"/><line x1="18" y1="12" x2="18.01" y2="12"/><line x1="8" y1="16" x2="16" y2="16"/>'},
            {'id': 'base_home', 'name': 'Home Key', 'svg': '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>'},
            {'id': 'base_split', 'name': 'Split Ergo', 'svg': '<path d="M4 5h5a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z"/><path d="M14 5h5a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z"/><line x1="6.5" y1="9" x2="7.5" y2="9"/><line x1="16.5" y1="9" x2="17.5" y2="9"/><line x1="6.5" y1="13" x2="7.5" y2="13"/><line x1="16.5" y1="13" x2="17.5" y2="13"/>'}
        ]
    },
    {
        'id': 'PC',
        'idx': 1,
        'title': 'Layer 1: PC',
        'desc': 'Windows overlay layer (swapped Ctrl & Alt)',
        'options': [
            {'id': 'pc_grid', 'name': 'Windows 4-Grid', 'svg': '<rect x="3" y="3" width="8" height="8" rx="1"/><rect x="13" y="3" width="8" height="8" rx="1"/><rect x="3" y="13" width="8" height="8" rx="1"/><rect x="13" y="13" width="8" height="8" rx="1"/>'},
            {'id': 'pc_monitor', 'name': 'PC Workstation', 'svg': '<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'},
            {'id': 'pc_terminal', 'name': 'Command Terminal', 'svg': '<rect x="3" y="4" width="18" height="16" rx="2"/><polyline points="7 10 10 12 7 14"/><line x1="12" y1="14" x2="16" y2="14"/>'}
        ]
    },
    {
        'id': 'Gaming',
        'idx': 2,
        'title': 'Layer 2: Gaming',
        'desc': 'WASD cluster with thumb GUI disabled',
        'options': [
            {'id': 'gaming_gamepad', 'name': 'Gamepad', 'svg': '<line x1="6" y1="12" x2="10" y2="12"/><line x1="8" y1="10" x2="8" y2="14"/><line x1="15" y1="13" x2="15.01" y2="13"/><line x1="18" y1="11" x2="18.01" y2="11"/><rect x="2" y="6" width="20" height="12" rx="6"/>'},
            {'id': 'gaming_dpad', 'name': 'Arcade D-Pad', 'svg': '<path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6V3z"/>'},
            {'id': 'gaming_trophy', 'name': 'Trophy', 'svg': '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.45 1-1 1H7"/><path d="M14 14.66V17c0 .55.45 1 1 1h2"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2z"/>'}
        ]
    },
    {
        'id': 'SymbolNav',
        'idx': 3,
        'title': 'Layer 3: SymbolNav',
        'desc': 'Symbols, code brackets, arrow navigation, PgUp/PgDn',
        'options': [
            {'id': 'sym_compass', 'name': 'Nav Compass', 'svg': '<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>'},
            {'id': 'sym_brackets', 'name': 'Code Brackets </ >', 'svg': '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/><line x1="14" y1="4" x2="10" y2="20"/>'},
            {'id': 'sym_arrows', 'name': '4-Way Arrows', 'svg': '<polyline points="12 2 12 22"/><polyline points="17 7 12 2 7 7"/><polyline points="2 12 22 12"/><polyline points="7 17 12 22 17 17"/>'}
        ]
    },
    {
        'id': 'Keypad',
        'idx': 4,
        'title': 'Layer 4: Keypad',
        'desc': '10-key numeric keypad and arithmetic math operators',
        'options': [
            {'id': 'kp_calc', 'name': 'Calculator', 'svg': '<rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="16" y1="14" x2="16" y2="18"/><path d="M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M8 18h.01M12 18h.01"/>'},
            {'id': 'kp_matrix', 'name': '3x3 Matrix', 'svg': '<rect x="3" y="3" width="4" height="4" rx="1"/><rect x="10" y="3" width="4" height="4" rx="1"/><rect x="17" y="3" width="4" height="4" rx="1"/><rect x="3" y="10" width="4" height="4" rx="1"/><rect x="10" y="10" width="4" height="4" rx="1"/><rect x="17" y="10" width="4" height="4" rx="1"/><rect x="3" y="17" width="4" height="4" rx="1"/><rect x="10" y="17" width="4" height="4" rx="1"/><rect x="17" y="17" width="4" height="4" rx="1"/>'},
            {'id': 'kp_math', 'name': 'Math Signs + - =', 'svg': '<line x1="5" y1="7" x2="11" y2="7"/><line x1="8" y1="4" x2="8" y2="10"/><line x1="14" y1="7" x2="19" y2="7"/><line x1="5" y1="16" x2="11" y2="16"/><line x1="14" y1="14" x2="19" y2="14"/><line x1="14" y1="18" x2="19" y2="18"/>'}
        ]
    },
    {
        'id': 'NumRow',
        'idx': 5,
        'title': 'Layer 5: NumRow',
        'desc': 'Dedicated number row and function key layer',
        'options': [
            {'id': 'num_hash', 'name': 'Hash Sign #', 'svg': '<line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/>'},
            {'id': 'num_digits', 'name': 'Digits 1-2-3', 'svg': '<path d="M3 17V7l-2 2"/><path d="M8 11a2.5 2.5 0 0 1 5 0c0 2-3 4-3 6h4"/><path d="M17 7h4l-2.5 4a2.5 2.5 0 0 1 2.5 4c0 1.5-1.5 2-3 2h-1.5"/>'},
            {'id': 'num_strip', 'name': 'Number Strip', 'svg': '<rect x="2" y="7" width="20" height="10" rx="2"/><line x1="7" y1="7" x2="7" y2="17"/><line x1="12" y1="7" x2="12" y2="17"/><line x1="17" y1="7" x2="17" y2="17"/><circle cx="4.5" cy="12" r="1" fill="currentColor"/><circle cx="9.5" cy="12" r="1" fill="currentColor"/><circle cx="14.5" cy="12" r="1" fill="currentColor"/><circle cx="19.5" cy="12" r="1" fill="currentColor"/>'}
        ]
    },
    {
        'id': 'Magic',
        'idx': 6,
        'title': 'Layer 6: Magic',
        'desc': 'Bluetooth pairing (BT 0-4), RGB effects, battery, reset',
        'options': [
            {'id': 'magic_wand', 'name': 'Magic Wand ✨', 'svg': '<path d="m15 4-1 1 3 3 1-1a2 2 0 0 0 0-2.83l-.17-.17a2 2 0 0 0-2.83 0z"/><path d="M14 8 3 19l2 2 11-11"/><line x1="9" y1="2" x2="9" y2="5"/><line x1="2" y1="9" x2="5" y2="9"/><line x1="20" y1="14" x2="20" y2="17"/><line x1="17" y1="20" x2="20" y2="20"/>'},
            {'id': 'magic_sparkles', 'name': 'Sparkle Burst', 'svg': '<path d="m12 3 1.9 5.6L19.5 10.5l-5.6 1.9L12 18l-1.9-5.6L4.5 10.5l5.6-1.9z"/><path d="m18 15 .8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z"/><path d="m5 4 .5 1.5 1.5.5-1.5.5L5 8l-.5-1.5L3 6l1.5-.5z"/>'},
            {'id': 'magic_gear_sparkle', 'name': 'System Dial Burst', 'svg': '<path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.93 4.93l2.12 2.12M16.95 16.95l2.12 2.12M4.93 19.07l2.12-2.12M16.95 7.05l2.12-2.12"/><circle cx="12" cy="12" r="4"/>'}
        ]
    },
    {
        'id': 'Factory',
        'idx': 7,
        'title': 'Layer 7: Factory',
        'desc': 'Hardware diagnostic testing and switch calibration',
        'options': [
            {'id': 'fac_building', 'name': 'Factory Building', 'svg': '<path d="M2 20h20"/><path d="M20 20V8l-6 4V8l-6 4V4H2v16h18z"/><line x1="6" y1="8" x2="6.01" y2="8"/><line x1="6" y1="12" x2="6.01" y2="12"/><line x1="6" y1="16" x2="6.01" y2="16"/>'},
            {'id': 'fac_tools', 'name': 'Tuning Tools', 'svg': '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>'},
            {'id': 'fac_chip', 'name': 'Microcontroller Chip', 'svg': '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="8" y="8" width="8" height="8" rx="1"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="15" x2="4" y2="15"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="15" x2="23" y2="15"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/>'}
        ]
    },
    {
        'id': 'Mouse',
        'idx': 8,
        'title': 'Layer 8: Mouse (Glove80)',
        'desc': 'Cursor movement, left/middle/right click, vertical scroll',
        'options': [
            {'id': 'mouse_body', 'name': 'Ergo Mouse', 'svg': '<rect x="5" y="2" width="14" height="20" rx="7"/><line x1="12" y1="6" x2="12" y2="10"/>'},
            {'id': 'mouse_pointer', 'name': 'Cursor Pointer', 'svg': '<path d="m3 3 7.07 16.97 2.51-7.39 7.39-2.51L3 3z"/><line x1="13" y1="13" x2="19" y2="19"/>'},
            {'id': 'mouse_split', 'name': 'Trackball Mouse', 'svg': '<rect x="5" y="2" width="14" height="20" rx="7"/><line x1="5" y1="9" x2="19" y2="9"/><line x1="12" y1="2" x2="12" y2="9"/><circle cx="12" cy="14" r="2"/>'}
        ]
    },
    {
        'id': 'Sniper',
        'idx': 9,
        'title': 'Layer 9: Sniper (Glove80)',
        'desc': 'Slow-speed mouse precision targeting for fine control',
        'options': [
            {'id': 'sniper_crosshair', 'name': 'Target Reticle', 'svg': '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><line x1="12" y1="1" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="1" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="23" y2="12"/>'},
            {'id': 'sniper_target', 'name': 'Concentric Bullseye', 'svg': '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2" fill="currentColor"/>'},
            {'id': 'sniper_scope', 'name': 'Precision Optic Scope', 'svg': '<circle cx="12" cy="12" r="9"/><line x1="12" y1="3" x2="12" y2="21"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="10" y1="7" x2="14" y2="7"/><line x1="10" y1="17" x2="14" y2="17"/><line x1="7" y1="10" x2="7" y2="14"/><line x1="17" y1="10" x2="17" y2="14"/>'}
        ]
    }
]

def build_contact_sheet_html():
    cards_html = []
    for layer in LAYERS_DATA:
        opts_html = []
        for idx, opt in enumerate(layer['options'], 1):
            opts_html.append(f'''
            <div class="opt-card">
              <div class="opt-badge">Option {idx}</div>
              <div class="opt-icon-box">
                <svg viewBox="0 0 24 24" class="icon-svg">{opt["svg"]}</svg>
              </div>
              <div class="opt-name">{opt["name"]}</div>
              <div class="opt-key">{opt["id"]}</div>
            </div>
            ''')

        cards_html.append(f'''
        <div class="layer-section">
          <div class="layer-header">
            <span class="layer-title">{layer["title"]}</span>
            <span class="layer-desc">{layer["desc"]}</span>
          </div>
          <div class="options-row">
            {"".join(opts_html)}
          </div>
        </div>
        ''')

    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0b0d13;
    color: #c9d1d9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, sans-serif;
    padding: 24px;
    width: 1080px;
  }}
  .header-box {{
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid #30363d;
  }}
  h1 {{
    font-size: 22px;
    font-weight: 700;
    color: #f0f6fc;
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  p.sub {{
    font-size: 13px;
    color: #8b949e;
    margin-top: 4px;
  }}
  .layers-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }}
  .layer-section {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 14px 16px;
  }}
  .layer-header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 10px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding-bottom: 6px;
  }}
  .layer-title {{
    font-size: 14px;
    font-weight: 700;
    color: #58a6ff;
  }}
  .layer-desc {{
    font-size: 11px;
    color: #8b949e;
  }}
  .options-row {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
  }}
  .opt-card {{
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 8px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  .opt-badge {{
    font-size: 10px;
    font-weight: 600;
    background: rgba(255,255,255,0.06);
    color: #8b949e;
    padding: 2px 6px;
    border-radius: 4px;
    margin-bottom: 8px;
  }}
  .opt-icon-box {{
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0,0,0,0.3);
    border-radius: 6px;
    margin-bottom: 6px;
  }}
  .icon-svg {{
    width: 28px;
    height: 28px;
    stroke: #58a6ff;
    fill: none;
    stroke-width: 2.2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }}
  .opt-name {{
    font-size: 12px;
    font-weight: 600;
    color: #f0f6fc;
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }}
  .opt-key {{
    font-size: 9px;
    color: #8b949e;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }}
</style>
</head>
<body>
  <div class="header-box">
    <h1>⌨️ MoErgo Layer Icons Design Showcase</h1>
    <p class="sub">3 Design Options for all 10 Layers • Interactive web picker available at http://localhost:8088/layer-icons.html</p>
  </div>
  <div class="layers-grid">
    {"".join(cards_html)}
  </div>
</body>
</html>'''

    path = os.path.join(PREVIEWS_DIR, 'contact_sheet.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path

def build_individual_preview_html():
    """Generates an HTML with each layer as a compact horizontal strip for terminal Kitty display."""
    strips_html = []
    for layer in LAYERS_DATA:
        opts_html = []
        for idx, opt in enumerate(layer['options'], 1):
            opts_html.append(f'''
            <div class="opt-card">
              <div class="opt-badge">Option {idx}</div>
              <div class="icon-wrap">
                <svg viewBox="0 0 24 24" class="icon-svg">{opt["svg"]}</svg>
              </div>
              <div class="opt-name">{opt["name"]}</div>
            </div>
            ''')

        strips_html.append(f'''
        <div class="layer-strip" id="strip-{layer['id']}">
          <div class="strip-header">
            <span class="strip-title">{layer['title']}</span>
            <span class="strip-desc">{layer['desc']}</span>
          </div>
          <div class="strip-options">
            {"".join(opts_html)}
          </div>
        </div>
        ''')

    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0b0d13;
    color: #c9d1d9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    padding: 10px;
    width: 620px;
  }}
  .layer-strip {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 12px;
  }}
  .strip-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding-bottom: 4px;
  }}
  .strip-title {{
    font-size: 13px;
    font-weight: 700;
    color: #58a6ff;
  }}
  .strip-desc {{
    font-size: 10px;
    color: #8b949e;
  }}
  .strip-options {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }}
  .opt-card {{
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  .opt-badge {{
    font-size: 9px;
    font-weight: 600;
    color: #8b949e;
    margin-bottom: 4px;
  }}
  .icon-wrap {{
    width: 38px;
    height: 38px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 4px;
  }}
  .icon-svg {{
    width: 26px;
    height: 26px;
    stroke: #58a6ff;
    fill: none;
    stroke-width: 2.2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }}
  .opt-name {{
    font-size: 11px;
    font-weight: 600;
    color: #f0f6fc;
  }}
</style>
</head>
<body>
  {"".join(strips_html)}
</body>
</html>'''

    path = os.path.join(PREVIEWS_DIR, 'strips.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path

def render_with_chromium(html_path, out_png, window_size="1080,1200"):
    cmd = [
        "chromium-browser",
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        f"--window-size={window_size}",
        f"--screenshot={out_png}",
        f"file://{html_path}"
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def main():
    print("Generating HTML preview templates...")
    contact_html = build_contact_sheet_html()
    strips_html = build_individual_preview_html()

    contact_png = os.path.join(PREVIEWS_DIR, 'contact_sheet.png')
    strips_png = os.path.join(PREVIEWS_DIR, 'strips.png')

    print(f"Rendering full contact sheet to {contact_png}...")
    render_with_chromium(contact_html, contact_png, "1080,1100")

    print(f"Rendering layer strips to {strips_png}...")
    render_with_chromium(strips_html, strips_png, "620,1350")

    print(f"Done! Created:\n  • {contact_png} ({os.path.getsize(contact_png):,} bytes)\n  • {strips_png} ({os.path.getsize(strips_png):,} bytes)")

if __name__ == '__main__':
    main()
