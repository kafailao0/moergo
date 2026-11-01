#!/usr/bin/env python3
"""
Build standalone interactive layout viewer for MoErgo Glove80 and Go60.
Extracts data from config/*.json and config/*.keymap and generates viewer/index.html.
"""

import json
import re
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def parse_rgb_from_keymap(keymap_path):
    with open(keymap_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse color hex defines
    colors = {
        '___': '#000000',
        'GRN': '#00FF00',
        'MAG': '#FF00FF',
        'GLD': '#FFBF00',
        'ORG': '#FF5500',
        'CYN': '#00FFFF',
        'RED': '#FF0000',
        'BLU': '#0066FF',
        'NML': '#00FF00',
        'CPL': '#FF0000',
    }
    for line in content.splitlines():
        m = re.match(r'#define\s+([A-Z0-9_]+)\s+&ug(?:_nl|_cl)?\s+0x([0-9a-fA-F]{6})', line)
        if m:
            colors[m.group(1)] = '#' + m.group(2).upper()

    # Parse layers inside underglow-layer { ... }
    start = content.find('underglow-layer {')
    layers = {}
    if start != -1:
        pattern = r'layer_([a-zA-Z0-9_]+)\s*\{([^}]+bindings\s*=\s*<([^>]+)>[^}]*)\};'
        for m in re.finditer(pattern, content[start:], re.DOTALL):
            layer_name = m.group(1)
            raw = m.group(3)
            tokens = [t for t in raw.split() if t and not t.startswith('/*')]
            layers[layer_name] = tokens

    return colors, layers

def format_zmk_param(val):
    if not val:
        return ''
    aliases = {
        'EXCLAMATION': '!', 'EXCL': '!',
        'AT_SIGN': '@', 'AT': '@',
        'HASH': '#', 'POUND': '#',
        'DOLLAR': '$', 'DLLR': '$',
        'PERCENT': '%', 'PRCNT': '%',
        'CARET': '^',
        'AMPERSAND': '&', 'AMPS': '&',
        'ASTERISK': '*', 'ASTRK': '*',
        'LEFT_PARENTHESIS': '(', 'LPAR': '(',
        'RIGHT_PARENTHESIS': ')', 'RPAR': ')',
        'MINUS': '-',
        'EQUAL': '=',
        'PLUS': '+',
        'UNDERSCORE': '_', 'UNDER': '_',
        'LEFT_BRACE': '{', 'LBRC': '{',
        'RIGHT_BRACE': '}', 'RBRC': '}',
        'LEFT_BRACKET': '[', 'LBKT': '[',
        'RIGHT_BRACKET': ']', 'RBKT': ']',
        'BACKSLASH': '\\', 'BSLH': '\\',
        'PIPE': '|',
        'SEMICOLON': ';', 'SEMI': ';',
        'COLON': ':',
        'SINGLE_QUOTE': "'", 'SQT': "'",
        'DOUBLE_QUOTES': '"', 'DQT': '"',
        'GRAVE': '`',
        'TILDE': '~',
        'COMMA': ',',
        'PERIOD': '.', 'DOT': '.',
        'SLASH': '/', 'FSLH': '/',
        'QUESTION': '?', 'QMARK': '?',
        'SPACE': 'Space',
        'TAB': 'Tab',
        'ENTER': 'Enter', 'RET': 'Enter',
        'BACKSPACE': 'Bksp', 'BSPC': 'Bksp',
        'DELETE': 'Del', 'DEL': 'Del',
        'ESCAPE': 'Esc', 'ESC': 'Esc',
        'PAGE_UP': 'PgUp', 'PG_UP': 'PgUp',
        'PAGE_DOWN': 'PgDn', 'PG_DN': 'PgDn',
        'HOME': 'Home',
        'END': 'End',
        'UP': '↑', 'UP_ARROW': '↑',
        'DOWN': '↓', 'DOWN_ARROW': '↓',
        'LEFT': '←', 'LEFT_ARROW': '←',
        'RIGHT': '→', 'RIGHT_ARROW': '→',
        'LGUI': '⌘ Cmd', 'RGUI': '⌘ Cmd', 'LCMD': '⌘ Cmd', 'RCMD': '⌘ Cmd',
        'LALT': '⌥ Alt', 'RALT': '⌥ Alt', 'LOPT': '⌥ Alt', 'ROPT': '⌥ Alt',
        'LCTRL': '⌃ Ctrl', 'RCTRL': '⌃ Ctrl',
        'LSHFT': '⇧ Shift', 'RSHFT': '⇧ Shift',
        'CAPS': 'Caps', 'CAPSLOCK': 'Caps',
        'C_VOL_UP': 'Vol +', 'C_VOL_DN': 'Vol -', 'C_MUTE': 'Mute',
        'C_BRI_UP': 'Bri +', 'C_BRI_DN': 'Bri -',
        'C_PLAY_PAUSE': '⏯', 'C_PP': '⏯',
        'C_NEXT': '⏭ Next', 'C_PREV': '⏮ Prev',
        'PSCRN': 'PrtSc', 'SLCK': 'ScrLk', 'PAUSE_BREAK': 'Pause', 'INS': 'Ins',
        'KP_N1': 'Pad 1', 'KP_N2': 'Pad 2', 'KP_N3': 'Pad 3', 'KP_N4': 'Pad 4',
        'KP_N5': 'Pad 5', 'KP_N6': 'Pad 6', 'KP_N7': 'Pad 7', 'KP_N8': 'Pad 8',
        'KP_N9': 'Pad 9', 'KP_N0': 'Pad 0', 'KP_DOT': 'Pad .', 'KP_PLUS': 'Pad +',
        'KP_MINUS': 'Pad -', 'KP_MULTIPLY': 'Pad *', 'KP_DIVIDE': 'Pad /',
        'KP_ENTER': 'Pad ↵', 'KP_NUM': 'NumLk', 'KP_EQUAL': 'Pad ='
    }
    if val.startswith('N') and len(val) == 2 and val[1].isdigit():
        return val[1]
    return aliases.get(val, val)

def parse_key_data(key_obj, layer_names):
    beh = str(key_obj.get('value', ''))
    raw_params = [str(p.get('value', '')) for p in key_obj.get('params', [])]

    primary = ''
    secondary = ''
    badge = ''
    badge_type = ''
    tooltip = ''
    raw_binding = beh + (' ' + ' '.join(raw_params) if raw_params else '')

    if beh == '&kp':
        primary = format_zmk_param(raw_params[0]) if raw_params else ''
        tooltip = f"Key: {raw_params[0]}"
    elif beh in ['&hml', '&hmr']:
        mod = format_zmk_param(raw_params[0])
        tap = format_zmk_param(raw_params[1])
        primary = tap
        secondary = mod.split()[0]
        badge = 'HML' if beh == '&hml' else 'HMR'
        badge_type = 'mod'
        hand = "Left (Home Row Mod)" if beh == '&hml' else "Right (Home Row Mod)"
        tooltip = f"Tap: {tap} • Hold: {mod} [{hand}]"
    elif beh == '&hold_tap_layer':
        layer_idx = int(raw_params[0]) if raw_params[0].isdigit() else raw_params[0]
        layer_name = layer_names[layer_idx] if isinstance(layer_idx, int) and layer_idx < len(layer_names) else f"Layer {layer_idx}"
        tap = format_zmk_param(raw_params[1])
        primary = tap
        secondary = f"L{layer_idx}"
        badge = 'HT'
        badge_type = 'layer'
        tooltip = f"Tap: {tap} • Hold: {layer_name}"
    elif beh == '&layer' or beh == '&mo':
        layer_idx = int(raw_params[0]) if raw_params[0].isdigit() else raw_params[0]
        layer_name = layer_names[layer_idx] if isinstance(layer_idx, int) and layer_idx < len(layer_names) else f"Layer {layer_idx}"
        primary = layer_name
        badge = 'MO'
        badge_type = 'layer'
        tooltip = f"Momentary Layer: {layer_name}"
    elif beh == '&to':
        layer_idx = int(raw_params[0]) if raw_params[0].isdigit() else raw_params[0]
        layer_name = layer_names[layer_idx] if isinstance(layer_idx, int) and layer_idx < len(layer_names) else f"Layer {layer_idx}"
        primary = f"To {layer_name}"
        badge = 'TO'
        badge_type = 'layer'
        tooltip = f"Switch to {layer_name}"
    elif beh == '&tog':
        layer_idx = int(raw_params[0]) if raw_params[0].isdigit() else raw_params[0]
        layer_name = layer_names[layer_idx] if isinstance(layer_idx, int) and layer_idx < len(layer_names) else f"Layer {layer_idx}"
        primary = f"Tog {layer_name}"
        badge = 'TOG'
        badge_type = 'layer'
        tooltip = f"Toggle {layer_name}"
    elif beh == '&magic':
        primary = 'Magic'
        badge = 'SYS'
        badge_type = 'sys'
        tooltip = 'Magic Layer'
    elif beh == 'Custom':
        custom_str = raw_params[0] if raw_params else ''
        raw_binding = custom_str
        if 'td_caps' in custom_str:
            primary = 'Caps'
            badge = 'TD'
            badge_type = 'td'
            tooltip = 'Tap Dance: 1x Caps Word • 2x Caps Lock'
        elif 'td_mouse' in custom_str:
            primary = 'Mouse'
            badge = 'TD'
            badge_type = 'td'
            tooltip = 'Tap Dance: 1x Spotlight • 2x Toggle Mouse Layer'
        elif 'td_copy_paste_pc' in custom_str:
            primary = 'Copy/Paste'
            badge = 'TD'
            badge_type = 'td'
            tooltip = 'Tap Dance (PC): 1x Ctrl+C • 2x Ctrl+V'
        elif 'td_copy_paste' in custom_str:
            primary = 'Copy/Paste'
            badge = 'TD'
            badge_type = 'td'
            tooltip = 'Tap Dance: 1x ⌘C • 2x ⌘V'
        elif 'td_media' in custom_str:
            primary = 'Media'
            badge = 'TD'
            badge_type = 'td'
            tooltip = 'Tap Dance: 1x Play/Pause • 2x Next • 3x Prev'
        elif 'SNIPER_SCRL' in custom_str:
            direction = custom_str.split('_')[-1]
            arrows = {'UP': '↑', 'DOWN': '↓', 'LEFT': '←', 'RIGHT': '→'}
            primary = f"Scrl {arrows.get(direction, direction)}"
            badge = 'SNP'
            badge_type = 'mouse'
            tooltip = f"Sniper Scroll {direction}"
        elif 'SNIPER_MOVE' in custom_str:
            direction = custom_str.split('_')[-1]
            arrows = {'UP': '↑', 'DOWN': '↓', 'LEFT': '←', 'RIGHT': '→'}
            primary = f"Move {arrows.get(direction, direction)}"
            badge = 'SNP'
            badge_type = 'mouse'
            tooltip = f"Sniper Move {direction}"
        else:
            primary = custom_str
    elif beh == '&trans':
        primary = '▽'
        tooltip = 'Transparent (Pass through to lower layer)'
        badge_type = 'trans'
    elif beh == '&none':
        primary = '—'
        tooltip = 'None (Inactive)'
        badge_type = 'none'
    elif beh.startswith('&bt'):
        if beh == '&bt':
            sub = raw_params[0] if raw_params else ''
            primary = f"BT {sub}"
        else:
            primary = beh.replace('&bt_', 'BT ')
        badge = 'BT'
        badge_type = 'bt'
        tooltip = f"Bluetooth: {primary}"
    elif beh == '&out':
        primary = raw_params[0].replace('OUT_', '') if raw_params else 'OUT'
        badge = 'OUT'
        badge_type = 'sys'
        tooltip = f"Output: {primary}"
    elif beh in ['&bootloader', '&reset']:
        primary = beh.replace('&', '').capitalize()
        badge = 'SYS'
        badge_type = 'sys'
        tooltip = primary
    elif beh == '&rgb_ug':
        primary = raw_params[0].replace('RGB_', '') if raw_params else 'RGB'
        badge = 'RGB'
        badge_type = 'rgb'
        tooltip = f"RGB Underglow: {primary}"
    elif beh == '&mmv':
        direction = raw_params[0].replace('MOVE_', '') if raw_params else ''
        arrows = {'UP': '↑', 'DOWN': '↓', 'LEFT': '←', 'RIGHT': '→'}
        primary = f"Mouse {arrows.get(direction, direction)}"
        badge = 'MS'
        badge_type = 'mouse'
        tooltip = f"Mouse Move {direction}"
    elif beh == '&msc':
        direction = raw_params[0].replace('SCRL_', '') if raw_params else ''
        arrows = {'UP': '↑', 'DOWN': '↓', 'LEFT': '←', 'RIGHT': '→'}
        primary = f"Scrl {arrows.get(direction, direction)}"
        badge = 'MSC'
        badge_type = 'mouse'
        tooltip = f"Mouse Scroll {direction}"
    elif beh == '&mkp':
        btn = raw_params[0].replace('CLK', '') if raw_params else ''
        labels = {'L': 'Left Click', 'R': 'Right Click', 'M': 'Middle Click'}
        primary = labels.get(btn, f"Click {btn}")
        badge = 'MKP'
        badge_type = 'mouse'
        tooltip = primary
    else:
        primary = beh
        tooltip = raw_binding

    return {
        'primary': primary,
        'secondary': secondary,
        'badge': badge,
        'badgeType': badge_type,
        'tooltip': tooltip,
        'rawBinding': raw_binding
    }

def build_data():
    with open(os.path.join(BASE_DIR, 'viewer', 'coords_glove80.json')) as f:
        g80_coords = json.load(f)
    with open(os.path.join(BASE_DIR, 'viewer', 'coords_go60.json')) as f:
        go60_coords = json.load(f)

    with open(os.path.join(BASE_DIR, 'glove80', 'config', 'glove80.json')) as f:
        g80_json = json.load(f)
    with open(os.path.join(BASE_DIR, 'go60', 'config', 'go60.json')) as f:
        go60_json = json.load(f)

    g80_colors, g80_rgb = parse_rgb_from_keymap(os.path.join(BASE_DIR, 'glove80', 'config', 'glove80.keymap'))
    go60_colors, go60_rgb = parse_rgb_from_keymap(os.path.join(BASE_DIR, 'go60', 'config', 'go60.keymap'))

    keyboards = {
        'glove80': {
            'name': 'Glove80',
            'title': g80_json.get('title', 'Kelvin\'s Glove80 Layout'),
            'notes': g80_json.get('notes', ''),
            'keyCount': 80,
            'coords': g80_coords,
            'layerNames': g80_json.get('layer_names', []),
            'rgbColors': g80_colors,
            'rgbLayers': g80_rgb,
            'layers': []
        },
        'go60': {
            'name': 'Go60',
            'title': go60_json.get('title', 'Kelvin\'s Go60 Layout'),
            'notes': go60_json.get('notes', ''),
            'keyCount': 60,
            'coords': go60_coords,
            'layerNames': go60_json.get('layer_names', []),
            'rgbColors': go60_colors,
            'rgbLayers': go60_rgb,
            'layers': []
        }
    }

    # Process Glove80 layers
    for layer_idx, layer_name in enumerate(keyboards['glove80']['layerNames']):
        raw_layer = g80_json['layers'][layer_idx]
        rgb_tokens = g80_rgb.get(layer_name, ['___'] * 80)
        parsed_keys = []
        for key_idx, key_obj in enumerate(raw_layer):
            kdata = parse_key_data(key_obj, keyboards['glove80']['layerNames'])
            rgb_token = rgb_tokens[key_idx] if key_idx < len(rgb_tokens) else '___'
            rgb_hex = g80_colors.get(rgb_token, '#000000')
            kdata['rgbToken'] = rgb_token
            kdata['rgbHex'] = rgb_hex
            parsed_keys.append(kdata)
        keyboards['glove80']['layers'].append({
            'name': layer_name,
            'keys': parsed_keys
        })

    # Process Go60 layers
    for layer_idx, layer_name in enumerate(keyboards['go60']['layerNames']):
        raw_layer = go60_json['layers'][layer_idx]
        rgb_tokens = go60_rgb.get(layer_name, ['___'] * 60)
        parsed_keys = []
        for key_idx, key_obj in enumerate(raw_layer):
            kdata = parse_key_data(key_obj, keyboards['go60']['layerNames'])
            rgb_token = rgb_tokens[key_idx] if key_idx < len(rgb_tokens) else '___'
            rgb_hex = go60_colors.get(rgb_token, '#000000')
            kdata['rgbToken'] = rgb_token
            kdata['rgbHex'] = rgb_hex
            parsed_keys.append(kdata)
        keyboards['go60']['layers'].append({
            'name': layer_name,
            'keys': parsed_keys
        })

    return keyboards

def generate_html(data):
    json_data = json.dumps(data)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=2.0">
  <title>MoErgo Layout Visualizer</title>
  <style>
    :root {{
      --bg: #0d1117;
      --surface: #161b22;
      --surface-border: #30363d;
      --text: #c9d1d9;
      --text-bright: #ffffff;
      --text-muted: #8b949e;
      --accent: #58a6ff;
      --key-bg: #1c2128;
      --key-border: #3b434e;
      --key-hover: #262c36;
      --key-active: #313947;
      --homing: #f0883e;
      --badge-mod: #d2a8ff;
      --badge-layer: #7ee787;
      --badge-td: #ffa657;
      --badge-sys: #ff7b72;
      --badge-mouse: #79c0ff;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
      user-select: none;
      -webkit-user-select: none;
    }}

    /* Top Navigation Bar */
    header {{
      background: var(--surface);
      border-bottom: 1px solid var(--surface-border);
      padding: 10px 18px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      position: sticky;
      top: 0;
      z-index: 100;
    }}

    .brand {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .brand-icon {{
      width: 26px;
      height: 26px;
      fill: var(--accent);
    }}
    .brand-title {{
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--text-bright);
      letter-spacing: -0.3px;
    }}
    .brand-sub {{
      font-size: 0.78rem;
      color: var(--accent);
      background: rgba(88, 166, 255, 0.12);
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 600;
    }}

    .controls {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}

    /* Toggle Switches & Buttons */
    .btn-group {{
      display: inline-flex;
      background: #090d12;
      border-radius: 8px;
      padding: 2px;
      border: 1px solid var(--surface-border);
    }}
    .btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 6px 14px;
      font-size: 0.82rem;
      font-weight: 600;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .btn:hover {{
      color: var(--text-bright);
    }}
    .btn.active {{
      background: var(--accent);
      color: #0d1117;
      font-weight: 700;
      box-shadow: 0 1px 3px rgba(0,0,0,0.3);
    }}

    .search-box {{
      position: relative;
      display: flex;
      align-items: center;
    }}
    .search-box input {{
      background: #090d12;
      border: 1px solid var(--surface-border);
      color: var(--text-bright);
      padding: 6px 12px 6px 30px;
      border-radius: 8px;
      font-size: 0.82rem;
      outline: none;
      width: 140px;
      transition: width 0.2s, border-color 0.2s;
    }}
    .search-box input:focus {{
      width: 180px;
      border-color: var(--accent);
    }}
    .search-icon {{
      position: absolute;
      left: 9px;
      width: 14px;
      height: 14px;
      fill: var(--text-muted);
      pointer-events: none;
    }}

    /* Layer Bar */
    .layer-bar {{
      background: #11151c;
      border-bottom: 1px solid var(--surface-border);
      padding: 8px 16px;
      display: flex;
      gap: 6px;
      overflow-x: auto;
      scrollbar-width: thin;
      scrollbar-color: var(--surface-border) transparent;
    }}
    .layer-btn {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      color: var(--text);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.12s ease;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .layer-btn .idx {{
      font-size: 0.7rem;
      color: var(--text-muted);
      background: rgba(255,255,255,0.06);
      padding: 1px 5px;
      border-radius: 4px;
    }}
    .layer-btn:hover {{
      background: #21262d;
      color: var(--text-bright);
    }}
    .layer-btn.active {{
      background: #1f6feb;
      border-color: #58a6ff;
      color: #ffffff;
    }}
    .layer-btn.active .idx {{
      background: rgba(0,0,0,0.25);
      color: #ffffff;
    }}

    /* Main Container & SVG Viewport */
    main {{
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 16px 10px;
      position: relative;
      overflow: hidden;
    }}

    .viewport-container {{
      width: 100%;
      max-width: 1200px;
      display: flex;
      justify-content: center;
      align-items: center;
      position: relative;
    }}

    svg#keyboard-svg {{
      width: 100%;
      height: auto;
      max-height: 72vh;
      display: block;
      overflow: visible;
    }}

    /* SVG Key Styling */
    .key-group {{
      cursor: pointer;
      transition: transform 0.1s ease;
    }}
    .key-group:hover {{
      filter: brightness(1.15);
    }}
    .key-cap {{
      fill: var(--key-bg);
      stroke: var(--key-border);
      stroke-width: 1.2;
      rx: 7;
      ry: 7;
      transition: all 0.12s ease;
    }}
    .key-cap.trans {{
      opacity: 0.45;
      stroke-dasharray: 2, 2;
    }}
    .key-cap.none {{
      opacity: 0.2;
    }}
    .key-group:hover .key-cap {{
      stroke: var(--accent);
      stroke-width: 1.8;
    }}
    .key-group.selected .key-cap {{
      fill: #243245;
      stroke: #58a6ff;
      stroke-width: 2.2;
      filter: drop-shadow(0 0 6px rgba(88,166,255,0.6));
    }}
    .key-group.matched .key-cap {{
      stroke: #f0883e !important;
      stroke-width: 2.5 !important;
      fill: #3b281c !important;
      filter: drop-shadow(0 0 8px #f0883e);
    }}

    .key-glow {{
      rx: 8;
      ry: 8;
      fill: none;
      stroke-width: 2.8;
      opacity: 0;
      transition: opacity 0.2s ease;
    }}
    .rgb-mode .key-glow {{
      opacity: 0.95;
    }}

    .key-text-primary {{
      fill: var(--text-bright);
      font-size: 13px;
      font-weight: 700;
      text-anchor: middle;
      dominant-baseline: central;
      pointer-events: none;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}
    .key-text-sec {{
      fill: var(--badge-mod);
      font-size: 10px;
      font-weight: 700;
      text-anchor: end;
      dominant-baseline: text-before-edge;
      pointer-events: none;
    }}
    .key-badge {{
      font-size: 8px;
      font-weight: 800;
      letter-spacing: 0.3px;
      text-anchor: start;
      dominant-baseline: text-before-edge;
      pointer-events: none;
    }}
    .badge-mod {{ fill: var(--badge-mod); }}
    .badge-layer {{ fill: var(--badge-layer); }}
    .badge-td {{ fill: var(--badge-td); }}
    .badge-sys {{ fill: var(--badge-sys); }}
    .badge-mouse {{ fill: var(--badge-mouse); }}

    .homing-dot {{
      fill: var(--homing);
      pointer-events: none;
    }}

    /* Legend & Info Drawer */
    .drawer {{
      background: var(--surface);
      border-top: 1px solid var(--surface-border);
      padding: 12px 20px;
      width: 100%;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      box-shadow: 0 -4px 12px rgba(0,0,0,0.25);
    }}

    .inspector {{
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .key-pill {{
      background: #21262d;
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      padding: 4px 10px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .key-pill-label {{
      font-size: 1.05rem;
      font-weight: 800;
      color: var(--text-bright);
      font-family: ui-monospace, SFMono-Regular, monospace;
    }}
    .key-meta {{
      font-size: 0.8rem;
      color: var(--text-muted);
      line-height: 1.3;
    }}
    .key-meta strong {{
      color: var(--text-bright);
    }}

    .rgb-legend {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      font-size: 0.75rem;
      color: var(--text-muted);
    }}
    .rgb-dot {{
      width: 9px;
      height: 9px;
      border-radius: 50%;
      display: inline-block;
      margin-right: 3px;
      vertical-align: middle;
    }}

    /* Zoom Controls Floating */
    .zoom-widget {{
      position: absolute;
      right: 16px;
      bottom: 70px;
      background: rgba(22, 27, 34, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      padding: 3px;
      gap: 3px;
      z-index: 50;
    }}
    .zoom-btn {{
      background: transparent;
      border: none;
      color: var(--text);
      width: 30px;
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
      font-weight: 700;
      cursor: pointer;
      border-radius: 6px;
    }}
    .zoom-btn:hover {{
      background: #30363d;
      color: #fff;
    }}

    /* Mobile Adaptations */
    @media (max-width: 768px) {{
      header {{ padding: 8px 12px; }}
      .brand-title {{ font-size: 1rem; }}
      .btn {{ padding: 5px 10px; font-size: 0.75rem; }}
      .search-box input {{ width: 100px; }}
      .drawer {{ padding: 8px 12px; }}
      .key-pill-label {{ font-size: 0.95rem; }}
      .rgb-legend {{ display: none; }}
      .zoom-widget {{ bottom: 90px; right: 10px; }}
    }}
  </style>
</head>
<body>

  <!-- Top Header Navigation -->
  <header>
    <div class="brand">
      <svg class="brand-icon" viewBox="0 0 24 24">
        <path d="M20 5H4c-1.1 0-1.99.9-1.99 2L2 17c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm-9 3h2v2h-2V8zm0 3h2v2h-2v-2zM8 8h2v2H8V8zm0 3h2v2H8v-2zm-1 2H5v-2h2v2zm0-3H5V8h2v2zm9 7H8v-2h8v2zm0-4h-2v-2h2v2zm0-3h-2V8h2v2zm3 3h-2v-2h2v2zm0-3h-2V8h2v2z"/>
      </svg>
      <div>
        <span class="brand-title">MoErgo Layout</span>
        <span class="brand-sub" id="kb-version">v24</span>
      </div>
    </div>

    <div class="controls">
      <!-- Keyboard Switcher -->
      <div class="btn-group">
        <button class="btn active" id="btn-glove80" onclick="switchKeyboard('glove80')">Glove80</button>
        <button class="btn" id="btn-go60" onclick="switchKeyboard('go60')">Go60</button>
      </div>

      <!-- Underglow View Toggle -->
      <div class="btn-group">
        <button class="btn active" id="btn-rgb" onclick="toggleRgb()">RGB Underglow: ON</button>
      </div>

      <!-- Quick Search -->
      <div class="search-box">
        <svg class="search-icon" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
        <input type="text" id="search-input" placeholder="Search keys... (/)" oninput="handleSearch(this.value)">
      </div>
    </div>
  </header>

  <!-- Layer Tabs Bar -->
  <div class="layer-bar" id="layer-tabs">
    <!-- Generated by JS -->
  </div>

  <!-- Keyboard Visualization SVG -->
  <main>
    <div class="viewport-container">
      <svg id="keyboard-svg" viewBox="-20 -20 1080 430" class="rgb-mode">
        <!-- SVG content rendered by JS -->
      </svg>
    </div>

    <!-- Floating Zoom Controls -->
    <div class="zoom-widget">
      <button class="zoom-btn" title="Zoom In" onclick="zoom(1.15)">+</button>
      <button class="zoom-btn" title="Zoom Out" onclick="zoom(0.85)">−</button>
      <button class="zoom-btn" title="Reset Fit" onclick="resetZoom()">⟲</button>
    </div>
  </main>

  <!-- Bottom Key Inspector Drawer & RGB Legend -->
  <div class="drawer">
    <div class="inspector" id="key-inspector">
      <div class="key-pill">
        <span class="key-pill-label" id="insp-label">—</span>
      </div>
      <div class="key-meta">
        <div id="insp-title">Click or tap any key to inspect full details</div>
        <div id="insp-detail" style="color: var(--text-muted); font-size: 0.75rem;">Shortcuts: [0-9] Layer • [G] Glove80 • [O] Go60 • [R] Toggle RGB</div>
      </div>
    </div>

    <div class="rgb-legend">
      <span><span class="rgb-dot" style="background:#FF00FF"></span>Nav/Arrows</span>
      <span><span class="rgb-dot" style="background:#00FFFF"></span>Function/Fn</span>
      <span><span class="rgb-dot" style="background:#FF5500"></span>Symbols</span>
      <span><span class="rgb-dot" style="background:#FFBF00"></span>Brackets/RGB</span>
      <span><span class="rgb-dot" style="background:#00FF00"></span>Keypad/Numpad</span>
      <span><span class="rgb-dot" style="background:#FF0000"></span>System/Lock</span>
      <span><span class="rgb-dot" style="background:#0066FF"></span>PC/Bluetooth</span>
    </div>
  </div>

  <script id="embedded-data" type="application/json">
{json_data}
  </script>

  <script>
    const KEYBOARDS = JSON.parse(document.getElementById('embedded-data').textContent);
    let currentKb = 'glove80';
    let currentLayer = 0;
    let rgbEnabled = true;
    let selectedKeyIdx = null;
    let currentScale = 1.0;
    let searchQuery = '';

    const UNIT = 54;
    const KEY_SIZE = 48;

    function init() {{
      renderLayerTabs();
      renderSvg();
      updateHeader();

      // Keyboard shortcuts
      window.addEventListener('keydown', (e) => {{
        if (e.target.tagName === 'INPUT') {{
          if (e.key === 'Escape') {{
            e.target.blur();
            e.target.value = '';
            handleSearch('');
          }}
          return;
        }}
        if (e.key >= '0' && e.key <= '9') {{
          const idx = parseInt(e.key);
          const kb = KEYBOARDS[currentKb];
          if (idx < kb.layers.length) {{
            setLayer(idx);
          }}
        }} else if (e.key === 'g' || e.key === 'G') {{
          switchKeyboard('glove80');
        }} else if (e.key === 'o' || e.key === 'O') {{
          switchKeyboard('go60');
        }} else if (e.key === 'r' || e.key === 'R') {{
          toggleRgb();
        }} else if (e.key === '/') {{
          e.preventDefault();
          document.getElementById('search-input').focus();
        }} else if (e.key === 'Escape') {{
          selectedKeyIdx = null;
          handleSearch('');
          renderSvg();
          resetInspector();
        }}
      }});
    }}

    function switchKeyboard(kb) {{
      if (currentKb === kb) return;
      currentKb = kb;
      currentLayer = 0;
      selectedKeyIdx = null;
      document.getElementById('btn-glove80').classList.toggle('active', kb === 'glove80');
      document.getElementById('btn-go60').classList.toggle('active', kb === 'go60');
      updateHeader();
      renderLayerTabs();
      renderSvg();
      resetInspector();
    }}

    function updateHeader() {{
      const kb = KEYBOARDS[currentKb];
      const match = kb.title.match(/v[0-9]+/);
      document.getElementById('kb-version').textContent = match ? match[0] : 'v24';
    }}

    function toggleRgb() {{
      rgbEnabled = !rgbEnabled;
      const btn = document.getElementById('btn-rgb');
      const svg = document.getElementById('keyboard-svg');
      btn.textContent = `RGB Underglow: ${{rgbEnabled ? 'ON' : 'OFF'}}`;
      btn.classList.toggle('active', rgbEnabled);
      svg.classList.toggle('rgb-mode', rgbEnabled);
    }}

    function renderLayerTabs() {{
      const kb = KEYBOARDS[currentKb];
      const bar = document.getElementById('layer-tabs');
      bar.innerHTML = '';
      kb.layers.forEach((layer, idx) => {{
        const btn = document.createElement('button');
        btn.className = `layer-btn ${{idx === currentLayer ? 'active' : ''}}`;
        btn.innerHTML = `<span class="idx">${{idx}}</span> ${{layer.name}}`;
        btn.onclick = () => setLayer(idx);
        bar.appendChild(btn);
      }});
    }}

    function setLayer(idx) {{
      currentLayer = idx;
      renderLayerTabs();
      renderSvg();
      if (selectedKeyIdx !== null) {{
        inspectKey(selectedKeyIdx);
      }}
    }}

    function renderSvg() {{
      const kb = KEYBOARDS[currentKb];
      const coords = kb.coords;
      const layer = kb.layers[currentLayer];
      const svg = document.getElementById('keyboard-svg');

      // Adjust viewBox based on keyboard
      if (currentKb === 'glove80') {{
        svg.setAttribute('viewBox', '-15 -15 1025 385');
      }} else {{
        svg.setAttribute('viewBox', '-15 -15 975 365');
      }}

      let html = '';

      coords.forEach((c, idx) => {{
        const key = layer.keys[idx] || {{ primary: '', secondary: '', badge: '', rgbHex: '#000000' }};
        const x = c.x * UNIT;
        const y = c.y * UNIT;
        const r = c.r || 0;
        const cx = x + KEY_SIZE / 2;
        const cy = y + KEY_SIZE / 2;

        const isSelected = selectedKeyIdx === idx;
        const isMatched = searchQuery && (
          key.primary.toLowerCase().includes(searchQuery) ||
          key.secondary.toLowerCase().includes(searchQuery) ||
          key.rawBinding.toLowerCase().includes(searchQuery) ||
          key.tooltip.toLowerCase().includes(searchQuery)
        );

        let transClass = '';
        if (key.primary === '▽') transClass = 'trans';
        if (key.primary === '—') transClass = 'none';

        // Check for homing keycaps (F and J on Base layer: keys 26 and 31 for Glove80)
        let isHoming = false;
        if (currentKb === 'glove80' && (idx === 26 || idx === 31)) isHoming = true;
        if (currentKb === 'go60' && (idx === 16 || idx === 21)) isHoming = true;

        const rotAttr = r ? `transform="rotate(${{r}} ${{cx}} ${{cy}})"` : '';
        const groupClass = `key-group ${{isSelected ? 'selected' : ''}} ${{isMatched ? 'matched' : ''}}`;

        html += `
          <g class="${{groupClass}}" ${{rotAttr}} onclick="onKeyClick(${{idx}})" data-idx="${{idx}}">
            <!-- RGB Glow -->
            <rect class="key-glow" x="${{x-2}}" y="${{y-2}}" width="${{KEY_SIZE+4}}" height="${{KEY_SIZE+4}}" stroke="${{key.rgbHex}}" />
            
            <!-- Keycap -->
            <rect class="key-cap ${{transClass}}" x="${{x}}" y="${{y}}" width="${{KEY_SIZE}}" height="${{KEY_SIZE}}" />

            <!-- Mod / Secondary (Top-Right) -->
            ${{key.secondary ? `<text class="key-text-sec" x="${{x + KEY_SIZE - 5}}" y="${{y + 5}}">${{escapeHtml(key.secondary)}}</text>` : ''}}

            <!-- Badge (Top-Left) -->
            ${{key.badge ? `<text class="key-badge badge-${{key.badgeType}}" x="${{x + 5}}" y="${{y + 5}}">${{escapeHtml(key.badge)}}</text>` : ''}}

            <!-- Primary Label (Center) -->
            <text class="key-text-primary" x="${{cx}}" y="${{cy + (key.secondary || key.badge ? 3 : 0)}}">${{escapeHtml(key.primary)}}</text>

            <!-- Homing dot -->
            ${{isHoming ? `<circle class="homing-dot" cx="${{cx}}" cy="${{y + KEY_SIZE - 6}}" r="1.8"/>` : ''}}
          </g>
        `;
      }});

      svg.innerHTML = html;
    }}

    function onKeyClick(idx) {{
      selectedKeyIdx = idx;
      renderSvg();
      inspectKey(idx);
    }}

    function inspectKey(idx) {{
      const kb = KEYBOARDS[currentKb];
      const coord = kb.coords[idx];
      const layer = kb.layers[currentLayer];
      const key = layer.keys[idx];

      document.getElementById('insp-label').textContent = key.primary || '—';
      
      const titleEl = document.getElementById('insp-title');
      const detailEl = document.getElementById('insp-detail');

      let rgbDesc = key.rgbToken !== '___' ? `RGB: <span style="color:${{key.rgbHex}}; font-weight:700;">${{key.rgbToken}}</span>` : 'RGB: Unlit';

      titleEl.innerHTML = `<strong>${{coord.label}}</strong> (Key #${{idx}}) • Layer ${{currentLayer}}: <strong>${{layer.name}}</strong> • ${{rgbDesc}}`;
      detailEl.innerHTML = `ZMK: <code style="color:var(--accent); background:#090d12; padding:2px 6px; border-radius:4px;">${{escapeHtml(key.rawBinding)}}</code> • ${{escapeHtml(key.tooltip)}}`;
    }}

    function resetInspector() {{
      document.getElementById('insp-label').textContent = '—';
      document.getElementById('insp-title').textContent = 'Click or tap any key to inspect full details';
      document.getElementById('insp-detail').textContent = 'Shortcuts: [0-9] Layer • [G] Glove80 • [O] Go60 • [R] Toggle RGB • [/] Search';
    }}

    function handleSearch(val) {{
      searchQuery = val.trim().toLowerCase();
      renderSvg();
    }}

    function zoom(factor) {{
      currentScale *= factor;
      const svg = document.getElementById('keyboard-svg');
      svg.style.transform = `scale(${{currentScale}})`;
    }}

    function resetZoom() {{
      currentScale = 1.0;
      const svg = document.getElementById('keyboard-svg');
      svg.style.transform = 'scale(1)';
    }}

    function escapeHtml(text) {{
      if (!text) return '';
      return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }}

    window.onload = init;
  </script>
</body>
</html>
"""
    return html

def main():
    print("Building MoErgo Layout Viewer...")
    data = build_data()
    html_content = generate_html(data)
    
    out_path = os.path.join(BASE_DIR, 'viewer', 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    size_kb = len(html_content.encode('utf-8')) / 1024
    print(f"Generated standalone viewer: {out_path} ({size_kb:.1f} KB)")

if __name__ == '__main__':
    main()
