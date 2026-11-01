#!/usr/bin/env python3
"""
Build standalone interactive layout viewer for MoErgo Glove80 and Go60.
Extracts data from config/*.json and config/*.keymap and generates:
- viewer/index.html (for local VPS/Tailscale serving)
- docs/index.html (for GitHub Pages publishing)
"""

import json
import re
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def parse_rgb_from_keymap(keymap_path):
    with open(keymap_path, 'r', encoding='utf-8') as f:
        content = f.read()

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

def format_param_recursive(p):
    """Recursively formats ZMK parameter objects including shifted symbols and modifier wrappers."""
    if isinstance(p, dict):
        val = str(p.get('value', ''))
        sub_params = p.get('params', [])
    else:
        val = str(p)
        sub_params = []

    shift_symbols = {
        'N1': '!', 'N2': '@', 'N3': '#', 'N4': '$', 'N5': '%',
        'N6': '^', 'N7': '&', 'N8': '*', 'N9': '(', 'N0': ')',
        'NUMBER_1': '!', 'NUMBER_2': '@', 'NUMBER_3': '#', 'NUMBER_4': '$', 'NUMBER_5': '%',
        'NUMBER_6': '^', 'NUMBER_7': '&', 'NUMBER_8': '*', 'NUMBER_9': '(', 'NUMBER_0': ')',
        'MINUS': '_', 'EQUAL': '+', 'LBKT': '{', 'RBKT': '}',
        'LEFT_BRACKET': '{', 'RIGHT_BRACKET': '}',
        'BSLH': '|', 'BACKSLASH': '|', 'GRAVE': '~', 'COMMA': '<', 'DOT': '>', 'PERIOD': '>',
        'SLASH': '?', 'FSLH': '?', 'SQT': '"', 'SINGLE_QUOTE': '"',
        'SEMI': ':', 'SEMICOLON': ':'
    }

    if val == 'LS' and sub_params:
        sub_val = str(sub_params[0].get('value', '')) if isinstance(sub_params[0], dict) else str(sub_params[0])
        if sub_val in shift_symbols:
            return shift_symbols[sub_val]
        return '⇧' + format_param_recursive(sub_params[0])

    mod_prefixes = {
        'LG': '⌘', 'RG': '⌘',
        'LC': '⌃', 'RC': '⌃',
        'LA': '⌥', 'RA': '⌥',
        'LS': '⇧', 'RS': '⇧',
        'MEH': '⌃⌥⇧', 'HYPER': '⌘⌃⌥⇧'
    }

    if val in mod_prefixes and sub_params:
        sub_formatted = ''.join(format_param_recursive(sp) for sp in sub_params)
        if len(sub_formatted) > 1 and sub_formatted[0].isalnum():
            return f"{mod_prefixes[val]} {sub_formatted}"
        return f"{mod_prefixes[val]}{sub_formatted}"

    base_aliases = {
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
        'LGUI': '⌘', 'RGUI': '⌘', 'LCMD': '⌘', 'RCMD': '⌘',
        'LALT': '⌥', 'RALT': '⌥', 'LOPT': '⌥', 'ROPT': '⌥',
        'LCTRL': '⌃', 'RCTRL': '⌃',
        'LSHFT': '⇧', 'RSHFT': '⇧',
        'CAPS': 'Caps', 'CAPSLOCK': 'Caps',
        'C_VOL_UP': 'Vol +', 'C_VOL_DN': 'Vol -', 'C_MUTE': 'Mute',
        'C_BRI_UP': 'Bri +', 'C_BRI_DN': 'Bri -',
        'C_PLAY_PAUSE': '⏯', 'C_PP': '⏯',
        'C_NEXT': '⏭', 'C_PREV': '⏮',
        'PSCRN': 'PrtSc', 'SLCK': 'ScrLk', 'PAUSE_BREAK': 'Pause', 'INS': 'Ins',
        'KP_N1': '1', 'KP_N2': '2', 'KP_N3': '3', 'KP_N4': '4',
        'KP_N5': '5', 'KP_N6': '6', 'KP_N7': '7', 'KP_N8': '8',
        'KP_N9': '9', 'KP_N0': '0', 'KP_DOT': '.', 'KP_PLUS': '+',
        'KP_MINUS': '-', 'KP_MULTIPLY': '*', 'KP_DIVIDE': '/',
        'KP_ENTER': '↵', 'KP_NUM': 'NumLk', 'KP_EQUAL': '=', 'KP_SLASH': '/',
        'GLOBE': '🌐'
    }

    if val.startswith('NUMBER_') and len(val) == 8 and val[7].isdigit():
        return val[7]
    if val.startswith('N') and len(val) == 2 and val[1].isdigit():
        return val[1]

    return base_aliases.get(val, val)

def stringify_param(p):
    """Stringifies nested parameters for raw binding display."""
    if isinstance(p, dict):
        val = str(p.get('value', ''))
        sub = p.get('params', [])
        if sub:
            return f"{val}({', '.join(stringify_param(sp) for sp in sub)})"
        return val
    return str(p)

def format_layer_badge(name):
    """Format layer name for keycap corner badge."""
    abbrevs = {
        'SymbolNav': 'SymNav',
        'NumRow': 'NumRow',
        'Keypad': 'Keypad',
        'Magic': 'Magic',
        'Mouse': 'Mouse',
        'Sniper': 'Sniper',
        'Gaming': 'Gaming',
        'Factory': 'Factory',
        'Base': 'Base',
        'PC': 'PC'
    }
    return abbrevs.get(name, name)

def parse_key_data(key_obj, layer_names):
    beh = str(key_obj.get('value', ''))
    raw_params = key_obj.get('params', [])
    formatted_params = [format_param_recursive(p) for p in raw_params]

    line1 = ''
    line2 = ''
    secondary = ''
    badge = ''
    badge_type = ''
    tooltip = ''
    target_layer = None
    raw_binding = beh + (' ' + ' '.join(stringify_param(p) for p in raw_params) if raw_params else '')

    if beh == '&kp':
        primary_text = formatted_params[0] if formatted_params else ''
        if ' ' in primary_text and len(primary_text) > 4:
            parts = primary_text.split(None, 1)
            line1, line2 = parts[0], parts[1]
        else:
            line1 = primary_text
        tooltip = f"Key: {primary_text}"

    elif beh in ['&hml', '&hmr']:
        mod = formatted_params[0]
        tap = formatted_params[1]
        line1 = tap
        secondary = mod.split()[0]
        badge = ''
        badge_type = 'mod'
        hand = "Left" if beh == '&hml' else "Right"
        tooltip = f"Home Row Mod ({hand}): Tap for {tap} • Hold for {mod}"

    elif beh == '&hold_tap_layer':
        layer_idx = int(raw_params[0].get('value', 0)) if str(raw_params[0].get('value', '')).isdigit() else 0
        layer_name = layer_names[layer_idx] if layer_idx < len(layer_names) else f"Layer {layer_idx}"
        tap = formatted_params[1]
        line1 = tap
        # User requested: Show layer name instead of L1/L2
        secondary = format_layer_badge(layer_name)
        target_layer = layer_idx
        badge_type = 'layer'
        tooltip = f"Tap for {tap} • Hold for {layer_name} (Click or hover to view layer)"

    elif beh in ['&layer', '&mo']:
        layer_idx = int(raw_params[0].get('value', 0)) if str(raw_params[0].get('value', '')).isdigit() else 0
        layer_name = layer_names[layer_idx] if layer_idx < len(layer_names) else f"Layer {layer_idx}"
        line1 = layer_name
        # If primary already displays layer_name, don't repeat in corner
        secondary = ''
        target_layer = layer_idx
        badge = ''
        badge_type = 'layer'
        tooltip = f"Layer: {layer_name} (Click or hover to view layer)"

    elif beh == '&to':
        layer_idx = int(raw_params[0].get('value', 0)) if str(raw_params[0].get('value', '')).isdigit() else 0
        layer_name = layer_names[layer_idx] if layer_idx < len(layer_names) else f"Layer {layer_idx}"
        line1 = "To"
        line2 = layer_name
        target_layer = layer_idx
        secondary = format_layer_badge(layer_name)
        badge = ''
        badge_type = 'layer'
        tooltip = f"Switch to {layer_name} (Click or hover to view layer)"

    elif beh == '&tog':
        layer_idx = int(raw_params[0].get('value', 0)) if str(raw_params[0].get('value', '')).isdigit() else 0
        layer_name = layer_names[layer_idx] if layer_idx < len(layer_names) else f"Layer {layer_idx}"
        line1 = "Tog"
        line2 = layer_name
        target_layer = layer_idx
        secondary = format_layer_badge(layer_name)
        badge = ''
        badge_type = 'layer'
        tooltip = f"Toggle {layer_name} (Click or hover to view layer)"

    elif beh == '&lt':
        layer_idx = int(raw_params[0].get('value', 0)) if str(raw_params[0].get('value', '')).isdigit() else 0
        layer_name = layer_names[layer_idx] if layer_idx < len(layer_names) else f"Layer {layer_idx}"
        tap = formatted_params[1] if len(formatted_params) > 1 else 'LT'
        line1 = tap
        secondary = format_layer_badge(layer_name)
        target_layer = layer_idx
        badge_type = 'layer'
        tooltip = f"Tap for {tap} • Hold for {layer_name} (Click or hover to view layer)"

    elif beh == '&magic':
        line1 = 'Magic'
        target_layer = 6
        secondary = 'Magic'
        badge_type = 'sys'
        tooltip = 'Magic Configuration Layer (Click or hover to view layer)'

    elif beh == 'Custom':
        custom_str = str(raw_params[0].get('value', '')) if raw_params else ''
        raw_binding = custom_str
        if 'td_caps' in custom_str:
            line1 = 'Caps'
            secondary = '1x/2x'
            badge = 'TD'
            badge_type = 'td'
            tooltip = 'Tap Dance: 1x Caps Word • 2x Caps Lock'
        elif 'td_mouse' in custom_str:
            line1 = 'Spotlight'
            line2 = 'Mouse'
            secondary = 'Mouse'
            target_layer = 8
            badge = 'TD'
            badge_type = 'td'
            tooltip = 'Tap Dance: 1x Spotlight (⌘ Space) • 2x Toggle Mouse Layer'
        elif 'td_copy_paste_pc' in custom_str:
            line1 = 'Copy'
            line2 = 'Paste (PC)'
            badge = 'TD'
            badge_type = 'td'
            tooltip = 'Tap Dance: 1x Ctrl+C (Copy) • 2x Ctrl+V (Paste)'
        elif 'td_copy_paste' in custom_str:
            line1 = 'Copy'
            line2 = 'Paste'
            badge = 'TD'
            badge_type = 'td'
            tooltip = 'Tap Dance: 1x ⌘C (Copy) • 2x ⌘V (Paste)'
        elif 'td_media' in custom_str:
            line1 = '⏯'
            line2 = 'Media'
            badge = 'TD'
            badge_type = 'td'
            tooltip = 'Tap Dance: 1x Play/Pause • 2x Next Track • 3x Prev Track'
        elif 'SNIPER_SCRL' in custom_str:
            direction = custom_str.split('_')[-1]
            arrows = {'UP': '↑', 'DOWN': '↓', 'LEFT': '←', 'RIGHT': '→'}
            line1 = '🎯 Scrl'
            line2 = arrows.get(direction, direction)
            badge_type = 'mouse'
            tooltip = f"Sniper Precision Scroll {direction}"
        elif 'SNIPER_MOVE' in custom_str:
            direction = custom_str.split('_')[-1]
            arrows = {'UP': '↑', 'DOWN': '↓', 'LEFT': '←', 'RIGHT': '→'}
            line1 = '🎯 Move'
            line2 = arrows.get(direction, direction)
            badge_type = 'mouse'
            tooltip = f"Sniper Precision Move {direction}"
        elif 'td_LAYER_Keypad' in custom_str:
            line1 = 'Keypad'
            secondary = 'Keypad'
            target_layer = 4
            tooltip = 'Tap: Toggle Keypad • Hold: Momentary Keypad'
        else:
            line1 = custom_str

    elif beh == '&trans':
        line1 = '▽'
        tooltip = 'Pass through (inherits key from Base layer)'
        badge_type = 'trans'
    elif beh == '&none':
        line1 = '—'
        tooltip = 'None (Inactive / Blocked)'
        badge_type = 'none'
    elif beh.startswith('&bt'):
        sub = formatted_params[0] if formatted_params else ''
        line1 = f"BT {sub}" if sub else beh.replace('&bt_', 'BT ')
        badge = 'BT'
        badge_type = 'bt'
        tooltip = f"Bluetooth: {line1}"
    elif beh == '&out':
        sub = str(raw_params[0].get('value', '')).replace('OUT_', '') if raw_params else 'OUT'
        line1 = f"OUT {sub}"
        badge_type = 'sys'
        tooltip = f"Output Selection: {sub}"
    elif beh in ['&bootloader', '&reset']:
        line1 = beh.replace('&', '').capitalize()
        badge_type = 'sys'
        tooltip = line1
    elif beh == '&rgb_ug':
        sub = str(raw_params[0].get('value', '')).replace('RGB_', '') if raw_params else 'RGB'
        line1 = 'RGB'
        line2 = sub
        badge_type = 'rgb'
        tooltip = f"RGB Control: {sub}"
    elif beh == '&mmv':
        sub = str(raw_params[0].get('value', '')).replace('MOVE_', '') if raw_params else ''
        arrows = {'UP': '↑', 'DOWN': '↓', 'LEFT': '←', 'RIGHT': '→'}
        line1 = 'Mouse'
        line2 = arrows.get(sub, sub)
        badge_type = 'mouse'
        tooltip = f"Mouse Move {sub}"
    elif beh == '&msc':
        sub = str(raw_params[0].get('value', '')).replace('SCRL_', '') if raw_params else ''
        arrows = {'UP': '↑', 'DOWN': '↓', 'LEFT': '←', 'RIGHT': '→'}
        line1 = 'Scrl'
        line2 = arrows.get(sub, sub)
        badge_type = 'mouse'
        tooltip = f"Mouse Scroll {sub}"
    elif beh == '&mkp':
        sub = str(raw_params[0].get('value', '')).replace('CLK', '') if raw_params else ''
        labels = {'L': 'L-Click', 'R': 'R-Click', 'M': 'M-Click'}
        line1 = labels.get(sub, f"Click {sub}")
        badge_type = 'mouse'
        tooltip = f"Mouse {line1}"
    else:
        line1 = beh
        tooltip = raw_binding

    return {
        'line1': line1,
        'line2': line2,
        'secondary': secondary,
        'badge': badge,
        'badgeType': badge_type,
        'tooltip': tooltip,
        'targetLayer': target_layer,
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
      --key-border: #38424d;
      --key-hover: #262e38;
      --key-active: #313d4c;
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

    .back-layer-btn {{
      background: #238636;
      border: 1px solid #2ea043;
      color: #ffffff;
      padding: 5px 12px;
      font-size: 0.8rem;
      font-weight: 700;
      border-radius: 6px;
      cursor: pointer;
      display: none;
      align-items: center;
      gap: 5px;
      animation: fadeIn 0.15s ease-in;
    }}
    .back-layer-btn:hover {{
      background: #2ea043;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(-3px); }}
      to {{ opacity: 1; transform: translateY(0); }}
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
    .layer-btn.preview-active {{
      background: #238636 !important;
      border-color: #7ee787 !important;
      color: #ffffff !important;
      box-shadow: 0 0 10px rgba(126, 231, 135, 0.6);
    }}
    .layer-btn.target-pulse {{
      border-color: #7ee787 !important;
      box-shadow: 0 0 8px rgba(126, 231, 135, 0.5);
    }}

    .preview-banner {{
      position: absolute;
      top: 10px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(35, 134, 54, 0.9);
      backdrop-filter: blur(6px);
      border: 1px solid #7ee787;
      color: #ffffff;
      padding: 4px 14px;
      border-radius: 20px;
      font-size: 0.78rem;
      font-weight: 700;
      display: none;
      align-items: center;
      gap: 6px;
      z-index: 60;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
      pointer-events: none;
    }}

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
      max-height: 74vh;
      display: block;
      overflow: visible;
    }}

    .key-group {{
      cursor: pointer;
      transition: filter 0.1s ease;
    }}
    .key-group:hover {{
      filter: brightness(1.25);
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
    .key-cap.pass-through {{
      opacity: 0.7;
      stroke-dasharray: 2.5, 2.5;
      fill: #141920;
    }}
    .key-cap.none {{
      opacity: 0.2;
    }}
    .key-group:hover .key-cap {{
      stroke: var(--accent);
      stroke-width: 1.8;
    }}
    .key-group.selected .key-cap {{
      fill: #223247;
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
    .key-group.has-layer-link:hover .key-cap {{
      stroke: var(--badge-layer) !important;
      stroke-width: 2px !important;
    }}

    .key-group.is-pass-through .key-text-primary {{
      fill: #8b949e !important;
      font-style: italic;
    }}
    .key-group.is-pass-through .key-text-sec {{
      fill: #8b949e !important;
      opacity: 0.7;
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
      text-anchor: middle;
      dominant-baseline: central;
      pointer-events: none;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}
    .key-text-sec {{
      fill: var(--badge-mod);
      font-size: 10.5px;
      font-weight: 700;
      text-anchor: end;
      dominant-baseline: text-before-edge;
      pointer-events: none;
    }}
    .key-text-layer-link {{
      fill: var(--badge-layer);
      font-weight: 800;
      text-anchor: end;
      dominant-baseline: text-before-edge;
      pointer-events: none;
      letter-spacing: -0.2px;
    }}
    .key-badge {{
      font-size: 8px;
      font-weight: 800;
      letter-spacing: 0.3px;
      text-anchor: start;
      dominant-baseline: text-before-edge;
      pointer-events: none;
    }}
    .badge-td {{ fill: var(--badge-td); }}
    .badge-sys {{ fill: var(--badge-sys); }}
    .badge-mouse {{ fill: var(--badge-mouse); }}

    .trans-watermark {{
      fill: #6e7681;
      font-size: 8px;
      font-weight: 700;
      pointer-events: none;
      text-anchor: start;
      dominant-baseline: text-before-edge;
    }}

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
      line-height: 1.35;
    }}
    .key-meta strong {{
      color: var(--text-bright);
    }}
    .jump-layer-btn {{
      background: #1f6feb;
      border: 1px solid #388bfd;
      color: #fff;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.72rem;
      font-weight: 700;
      cursor: pointer;
      margin-left: 8px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}
    .jump-layer-btn:hover {{
      background: #388bfd;
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
      <button class="back-layer-btn" id="btn-back-layer" onclick="returnToPreviousLayer()">
        ↩ Back to Base (Esc)
      </button>

      <div class="btn-group">
        <button class="btn active" id="btn-glove80" onclick="switchKeyboard('glove80')">Glove80</button>
        <button class="btn" id="btn-go60" onclick="switchKeyboard('go60')">Go60</button>
      </div>

      <div class="btn-group">
        <button class="btn active" id="btn-rgb" onclick="toggleRgb()">RGB Underglow: ON</button>
      </div>

      <div class="search-box">
        <svg class="search-icon" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
        <input type="text" id="search-input" placeholder="Search keys... (/)" oninput="handleSearch(this.value)">
      </div>
    </div>
  </header>

  <div class="layer-bar" id="layer-tabs"></div>

  <main>
    <div class="preview-banner" id="preview-banner">
      <span>👁️ Previewing Layer:</span>
      <span id="preview-layer-name" style="text-decoration: underline;">—</span>
      <span style="opacity: 0.8; font-weight: normal; font-size: 0.72rem;">(Move away or release to return)</span>
    </div>

    <div class="viewport-container">
      <svg id="keyboard-svg" viewBox="-20 -20 1010 475" class="rgb-mode"></svg>
    </div>

    <div class="zoom-widget">
      <button class="zoom-btn" title="Zoom In" onclick="zoom(1.15)">+</button>
      <button class="zoom-btn" title="Zoom Out" onclick="zoom(0.85)">−</button>
      <button class="zoom-btn" title="Reset Fit" onclick="resetZoom()">⟲</button>
    </div>
  </main>

  <div class="drawer">
    <div class="inspector" id="key-inspector">
      <div class="key-pill">
        <span class="key-pill-label" id="insp-label">—</span>
      </div>
      <div class="key-meta">
        <div id="insp-title">Hover or click any key to inspect details and preview layers</div>
        <div id="insp-detail" style="color: var(--text-muted); font-size: 0.75rem;">Shortcuts: [0-9] Layer • [G] Glove80 • [O] Go60 • [R] Toggle RGB • Hover layer keys to preview</div>
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
    let previewLayer = null;
    let previewTriggerKeyIdx = null;
    let layerHistory = [];
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
          if (previewLayer !== null || previewTriggerKeyIdx !== null) {{
            stopPreview();
          }} else if (layerHistory.length > 0) {{
            returnToPreviousLayer();
          }} else {{
            selectedKeyIdx = null;
            handleSearch('');
            renderSvg();
            resetInspector();
          }}
        }}
      }});

      // Bulletproof move-away detection for layer preview:
      // Instantly disables preview the moment mouse moves off the trigger key
      document.addEventListener('pointermove', (e) => {{
        if (previewTriggerKeyIdx === null) return;
        const targetKey = e.target.closest('[data-idx]');
        const hoveredIdx = targetKey ? parseInt(targetKey.getAttribute('data-idx'), 10) : null;
        if (hoveredIdx !== previewTriggerKeyIdx) {{
          stopPreview();
        }}
      }});

      document.addEventListener('mouseleave', () => {{
        if (previewTriggerKeyIdx !== null) {{
          stopPreview();
        }}
      }});
    }}

    function switchKeyboard(kb) {{
      if (currentKb === kb) return;
      currentKb = kb;
      currentLayer = 0;
      previewLayer = null;
      layerHistory = [];
      selectedKeyIdx = null;
      document.getElementById('btn-glove80').classList.toggle('active', kb === 'glove80');
      document.getElementById('btn-go60').classList.toggle('active', kb === 'go60');
      updateHeader();
      updateBackButton();
      updatePreviewBanner();
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
        btn.id = `layer-tab-${{idx}}`;
        const isActive = (idx === currentLayer && previewLayer === null);
        const isPreview = (idx === previewLayer);
        btn.className = `layer-btn ${{isActive ? 'active' : ''}} ${{isPreview ? 'preview-active' : ''}}`;
        btn.innerHTML = `<span class="idx">${{idx}}</span> ${{layer.name}}`;
        btn.onclick = () => setLayer(idx);
        btn.onmouseenter = () => {{
          if (idx !== currentLayer) {{
            previewLayer = idx;
            updateLayerTabStates();
            renderSvg();
            updatePreviewBanner();
          }}
        }};
        btn.onmouseleave = () => {{
          if (previewLayer === idx && previewTriggerKeyIdx === null) {{
            previewLayer = null;
            updateLayerTabStates();
            renderSvg();
            updatePreviewBanner();
          }}
        }};
        bar.appendChild(btn);
      }});
    }}

    function updateLayerTabStates() {{
      const kb = KEYBOARDS[currentKb];
      kb.layers.forEach((layer, idx) => {{
        const btn = document.getElementById(`layer-tab-${{idx}}`);
        if (btn) {{
          const isActive = (idx === currentLayer && previewLayer === null);
          const isPreview = (idx === previewLayer);
          btn.className = `layer-btn ${{isActive ? 'active' : ''}} ${{isPreview ? 'preview-active' : ''}}`;
        }}
      }});
    }}

    function setLayer(idx, fromKeyLink = false) {{
      if (fromKeyLink && idx !== currentLayer) {{
        layerHistory.push(currentLayer);
      }}
      currentLayer = idx;
      previewLayer = null;
      previewTriggerKeyIdx = null;
      updateBackButton();
      updatePreviewBanner();
      updateLayerTabStates();
      renderSvg();
      if (selectedKeyIdx !== null) {{
        inspectKey(selectedKeyIdx);
      }}
    }}

    function returnToPreviousLayer() {{
      if (layerHistory.length > 0) {{
        const prev = layerHistory.pop();
        currentLayer = prev;
        previewLayer = null;
        previewTriggerKeyIdx = null;
        updateBackButton();
        updatePreviewBanner();
        updateLayerTabStates();
        renderSvg();
        if (selectedKeyIdx !== null) inspectKey(selectedKeyIdx);
      }} else {{
        setLayer(0);
      }}
    }}

    function updateBackButton() {{
      const btn = document.getElementById('btn-back-layer');
      if (layerHistory.length > 0) {{
        const kb = KEYBOARDS[currentKb];
        const prevIdx = layerHistory[layerHistory.length - 1];
        const prevName = kb.layers[prevIdx] ? kb.layers[prevIdx].name : 'Base';
        btn.innerHTML = `↩ Back to ${{prevName}} (Esc)`;
        btn.style.display = 'inline-flex';
      }} else {{
        btn.style.display = 'none';
      }}
    }}

    function updatePreviewBanner() {{
      const banner = document.getElementById('preview-banner');
      const nameEl = document.getElementById('preview-layer-name');
      if (previewLayer !== null) {{
        const kb = KEYBOARDS[currentKb];
        const layerName = kb.layers[previewLayer] ? kb.layers[previewLayer].name : `L${{previewLayer}}`;
        nameEl.textContent = `${{previewLayer}}: ${{layerName}}`;
        banner.style.display = 'inline-flex';
      }} else {{
        banner.style.display = 'none';
      }}
    }}

    function renderSvg() {{
      const kb = KEYBOARDS[currentKb];
      const coords = kb.coords;
      const displayLayer = (previewLayer !== null) ? previewLayer : currentLayer;
      const layer = kb.layers[displayLayer];
      const baseLayer = kb.layers[0];
      const svg = document.getElementById('keyboard-svg');

      if (currentKb === 'glove80') {{
        svg.setAttribute('viewBox', '-15 -10 1000 460');
      }} else {{
        svg.setAttribute('viewBox', '-15 -10 970 365');
      }}

      let html = '';

      coords.forEach((c, idx) => {{
        const rawKey = layer.keys[idx] || {{ line1: '', line2: '', secondary: '', badge: '', rgbHex: '#000000', rawBinding: '' }};
        const x = c.x * UNIT;
        const y = c.y * UNIT;
        const r = c.r || 0;
        const cx = x + KEY_SIZE / 2;
        const cy = y + KEY_SIZE / 2;

        let pivotX = (c.rx !== undefined) ? c.rx * UNIT : x;
        let pivotY = (c.ry !== undefined) ? c.ry * UNIT : y;

        // Pass-through (&trans) key resolution to Base layer
        const isTrans = (rawKey.line1 === '▽' || rawKey.rawBinding === '&trans');
        let key = rawKey;
        let isPassThrough = false;

        if (isTrans && displayLayer !== 0 && baseLayer && baseLayer.keys[idx]) {{
          const baseK = baseLayer.keys[idx];
          if (baseK && baseK.line1 !== '▽' && baseK.rawBinding !== '&trans') {{
            isPassThrough = true;
            key = {{
              ...rawKey,
              line1: baseK.line1,
              line2: baseK.line2,
              secondary: baseK.secondary,
              badge: '',
              tooltip: `Pass-through (Inherited from Base: ${{baseK.tooltip || baseK.line1}})`,
              rawBinding: `&trans (Inherits Base: ${{baseK.rawBinding}})`
            }};
          }}
        }}

        const isSelected = selectedKeyIdx === idx;
        const isMatched = searchQuery && (
          (key.line1 && key.line1.toLowerCase().includes(searchQuery)) ||
          (key.line2 && key.line2.toLowerCase().includes(searchQuery)) ||
          (key.secondary && key.secondary.toLowerCase().includes(searchQuery)) ||
          (key.rawBinding && key.rawBinding.toLowerCase().includes(searchQuery)) ||
          (key.tooltip && key.tooltip.toLowerCase().includes(searchQuery))
        );

        let capClass = 'key-cap';
        if (isPassThrough) {{
          capClass += ' pass-through';
        }} else if (key.line1 === '▽') {{
          capClass += ' trans';
        }} else if (key.line1 === '—') {{
          capClass += ' none';
        }}

        const hasLayerLink = key.targetLayer !== null && key.targetLayer !== undefined;
        const rotAttr = r ? `transform="rotate(${{r}} ${{pivotX}} ${{pivotY}})"` : '';
        const groupClass = `key-group ${{isSelected ? 'selected' : ''}} ${{isMatched ? 'matched' : ''}} ${{hasLayerLink ? 'has-layer-link' : ''}} ${{isPassThrough ? 'is-pass-through' : ''}}`;

        let primaryFontSize = 13.5;
        let primaryFontWeight = 700;
        if (key.line2) {{
          primaryFontSize = key.line1.length > 5 ? 8.5 : 9.5;
        }} else if (key.line1.length > 6) {{
          primaryFontSize = 9;
          primaryFontWeight = 600;
        }} else if (key.line1.length > 3) {{
          primaryFontSize = 11;
        }}

        const secFontSize = (key.secondary && key.secondary.length > 5) ? '7.8px' : '9px';

        html += `
          <g class="${{groupClass}}" ${{rotAttr}}
             onclick="onKeyClick(${{idx}})"
             onmouseenter="onKeyHover(${{idx}})"
             data-idx="${{idx}}">

            <!-- RGB Glow border -->
            <rect class="key-glow" x="${{x-2}}" y="${{y-2}}" width="${{KEY_SIZE+4}}" height="${{KEY_SIZE+4}}" stroke="${{key.rgbHex}}" />

            <!-- Tactile Keycap -->
            <rect class="${{capClass}}" x="${{x}}" y="${{y}}" width="${{KEY_SIZE}}" height="${{KEY_SIZE}}" />

            <!-- Pass-through watermark icon -->
            ${{isPassThrough ? `<text class="trans-watermark" x="${{x + 4}}" y="${{y + 10}}">▽</text>` : ''}}

            <!-- Corner Secondary / Mod / Layer Name -->
            ${{key.secondary ? `
              <text class="${{hasLayerLink ? 'key-text-layer-link' : 'key-text-sec'}}"
                    x="${{x + KEY_SIZE - 4}}" y="${{y + 4.5}}"
                    font-size="${{secFontSize}}">${{escapeHtml(key.secondary)}}</text>
            ` : ''}}

            <!-- Badge (Top-Left) -->
            ${{key.badge ? `
              <text class="key-badge badge-${{key.badgeType}}" x="${{x + 5}}" y="${{y + 4.5}}">${{escapeHtml(key.badge)}}</text>
            ` : ''}}

            <!-- Primary Label (Centered, 1 or 2 lines) -->
            ${{key.line2 ? `
              <text class="key-text-primary" x="${{cx}}" y="${{cy - 5.5}}" font-size="${{primaryFontSize}}" font-weight="${{primaryFontWeight}}">${{escapeHtml(key.line1)}}</text>
              <text class="key-text-primary" x="${{cx}}" y="${{cy + 7.5}}" font-size="${{primaryFontSize}}" font-weight="${{primaryFontWeight}}">${{escapeHtml(key.line2)}}</text>
            ` : `
              <text class="key-text-primary" x="${{cx}}" y="${{cy + (key.secondary ? 2.5 : 0)}}" font-size="${{primaryFontSize}}" font-weight="${{primaryFontWeight}}">${{escapeHtml(key.line1)}}</text>
            `}}
          </g>
        `;
      }});

      svg.innerHTML = html;
    }}

    function startPreview(idx, targetLayer) {{
      if (previewTriggerKeyIdx === idx && previewLayer === targetLayer) return;
      previewTriggerKeyIdx = idx;
      previewLayer = targetLayer;
      updateLayerTabStates();
      renderSvg();
      updatePreviewBanner();
    }}

    function stopPreview() {{
      if (previewTriggerKeyIdx === null && previewLayer === null) return;
      previewTriggerKeyIdx = null;
      previewLayer = null;
      updateLayerTabStates();
      renderSvg();
      updatePreviewBanner();
    }}

    function onKeyClick(idx) {{
      const kb = KEYBOARDS[currentKb];
      const origKey = kb.layers[currentLayer].keys[idx];

      // If clicked key links to another layer, switch permanently
      if (origKey && origKey.targetLayer !== null && origKey.targetLayer !== undefined && origKey.targetLayer !== currentLayer) {{
        stopPreview();
        setLayer(origKey.targetLayer, true);
        return;
      }}

      stopPreview();
      selectedKeyIdx = idx;
      renderSvg();
      inspectKey(idx);
    }}

    function onKeyHover(idx) {{
      if (previewTriggerKeyIdx !== null) return;
      const kb = KEYBOARDS[currentKb];
      const key = kb.layers[currentLayer].keys[idx];
      if (key && key.targetLayer !== null && key.targetLayer !== undefined && key.targetLayer !== currentLayer) {{
        startPreview(idx, key.targetLayer);
      }}
    }}

    function inspectKey(idx) {{
      const kb = KEYBOARDS[currentKb];
      const coord = kb.coords[idx];
      const displayLayer = (previewLayer !== null) ? previewLayer : currentLayer;
      const layer = kb.layers[displayLayer];
      const key = layer.keys[idx];

      const fullLabel = key.line2 ? `${{key.line1}} ${{key.line2}}` : (key.line1 || '—');
      document.getElementById('insp-label').textContent = fullLabel;

      const titleEl = document.getElementById('insp-title');
      const detailEl = document.getElementById('insp-detail');

      let rgbDesc = key.rgbToken !== '___' ? `RGB: <span style="color:${{key.rgbHex}}; font-weight:700;">${{key.rgbToken}}</span>` : 'RGB: Unlit';

      let layerJumpHtml = '';
      if (key.targetLayer !== null && key.targetLayer !== undefined) {{
        const targetName = kb.layers[key.targetLayer] ? kb.layers[key.targetLayer].name : `Layer ${{key.targetLayer}}`;
        layerJumpHtml = `<button class="jump-layer-btn" onclick="setLayer(${{key.targetLayer}}, true)">Go to ${{targetName}} →</button>`;
      }}

      titleEl.innerHTML = `<strong>${{coord.label}}</strong> (Key #${{idx}}) • Layer ${{displayLayer}}: <strong>${{layer.name}}</strong> • ${{rgbDesc}} ${{layerJumpHtml}}`;
      detailEl.innerHTML = `ZMK: <code style="color:var(--accent); background:#090d12; padding:2px 6px; border-radius:4px;">${{escapeHtml(key.rawBinding)}}</code> • ${{escapeHtml(key.tooltip)}}`;
    }}

    function resetInspector() {{
      document.getElementById('insp-label').textContent = '—';
      document.getElementById('insp-title').textContent = 'Hover or click any key to inspect details and preview layers';
      document.getElementById('insp-detail').textContent = 'Shortcuts: [0-9] Layer • [G] Glove80 • [O] Go60 • [R] Toggle RGB • Hover layer keys to preview';
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

    docs_dir = os.path.join(BASE_DIR, 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    docs_path = os.path.join(docs_dir, 'index.html')
    with open(docs_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    size_kb = len(html_content.encode('utf-8')) / 1024
    print(f"Generated standalone viewer: {out_path} and {docs_path} ({size_kb:.1f} KB)")

if __name__ == '__main__':
    main()
