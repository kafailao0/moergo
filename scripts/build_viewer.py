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
        secondary = f"L{layer_idx}"
        target_layer = layer_idx
        badge = 'LAYER'
        badge_type = 'layer'
        tooltip = f"Layer: {layer_name} (Click to switch or hold to activate)"

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
            secondary = ''
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
            secondary = 'L4'
            target_layer = 4
            badge = 'LAYER'
            badge_type = 'layer'
            tooltip = 'Tap: Toggle Keypad • Hold: Momentary Keypad (Layer 4)'
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

def generate_standalone_html(data):
    json_data = json.dumps(data)

    src_dir = os.path.join(BASE_DIR, 'viewer', 'src')
    with open(os.path.join(src_dir, 'index.html'), 'r', encoding='utf-8') as f:
        html = f.read()
    with open(os.path.join(src_dir, 'style.css'), 'r', encoding='utf-8') as f:
        css = f.read()
    with open(os.path.join(src_dir, 'app.js'), 'r', encoding='utf-8') as f:
        js = f.read()

    # Inline CSS
    style_tag = f"<style>\n{css}\n</style>"
    html = html.replace('<link rel="stylesheet" href="style.css">', style_tag)

    # Inline Data
    data_tag = f'<script id="embedded-data" type="application/json">\n{json_data}\n</script>'
    html = html.replace('<!-- EMBEDDED_DATA_PLACEHOLDER -->', data_tag)

    # Inline JS
    js_tag = f"<script>\n{js}\n</script>"
    html = html.replace('<script src="app.js"></script>', js_tag)

    return html

def main():
    print("Building MoErgo Layout Viewer...")
    data = build_data()

    # Save standalone data.json
    data_path = os.path.join(BASE_DIR, 'viewer', 'data.json')
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Generated data file: {data_path}")

    html_content = generate_standalone_html(data)

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
