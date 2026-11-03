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
import shutil
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Unified key metadata mapping: keycode -> (display_symbol, friendly_name, icon_id)
KEY_METADATA = {
    'BSPC': ('⌫', 'Backspace', 'backspace'),
    'BACKSPACE': ('⌫', 'Backspace', 'backspace'),
    'DEL': ('⌦', 'Delete', 'delete'),
    'DELETE': ('⌦', 'Delete', 'delete'),
    'ESC': ('⎋', 'Escape', 'escape'),
    'ESCAPE': ('⎋', 'Escape', 'escape'),
    'TAB': ('⇥', 'Tab', 'tab'),
    'RET': ('↵', 'Enter', 'enter'),
    'ENTER': ('↵', 'Enter', 'enter'),
    'KP_ENTER': ('↵', 'Enter', 'enter'),
    'SPACE': ('␣', 'Space', 'space'),
    'CAPS': ('⇪', 'Caps Lock', 'caps'),
    'CAPSLOCK': ('⇪', 'Caps Lock', 'caps'),
    'C_VOL_UP': ('🔊', 'Volume Up', 'vol_up'),
    'C_VOL_DN': ('🔉', 'Volume Down', 'vol_down'),
    'C_MUTE': ('🔇', 'Mute', 'mute'),
    'C_BRI_UP': ('🔆', 'Brightness Up', 'bri_up'),
    'C_BRI_DN': ('🔅', 'Brightness Down', 'bri_down'),
    'PSCRN': ('📷', 'Print Screen', 'prtsc'),
    'INS': ('Ins', 'Insert', 'ins'),
}

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
        'SPACE': '␣',
        'TAB': '⇥',
        'ENTER': '↵', 'RET': '↵',
        'BACKSPACE': '⌫', 'BSPC': '⌫',
        'DELETE': '⌦', 'DEL': '⌦',
        'ESCAPE': '⎋', 'ESC': '⎋',
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
        'CAPS': '⇪', 'CAPSLOCK': '⇪',
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
        'Keypad': 'Keypad'
    }
    if name in abbrevs:
        return abbrevs[name]
    return name[:6] if len(name) > 6 else name

def parse_custom_behavior_annotations(dts_text, layer_names=None):
    """
    Parses doc-comment annotations from custom_defined_behaviors or keymap behaviors.
    Format example:
      /* @viewer: Copy | Paste | @badge: TD | @tooltip: Tap Dance: 1x Ctrl+C • 2x Ctrl+V */
      td_copy_paste_pc: td_copy_paste_pc { ... };

    If no annotation comment exists, attempts auto-derivation for tap-dance behaviors
    based on their bindings.
    """
    meta = {}
    if not dts_text:
        return meta

    # 1. Parse explicit /* @viewer: ... */ comments
    pattern = re.compile(r'/\*\s*@(?:viewer|label)\b(.*?)\*/\s*([a-zA-Z0-9_]+)\s*:', re.DOTALL)
    for m in pattern.finditer(dts_text):
        comment_body = m.group(1).strip()
        beh_name = m.group(2).strip()
        info = {'name': beh_name}
        parts = re.split(r'\|\s*@', comment_body)
        for idx, part in enumerate(parts):
            part = part.strip()
            if idx == 0:
                val = re.sub(r'^(?:label|viewer)?\s*:\s*', '', part).strip()
                labels = [l.strip() for l in re.split(r'[|/]', val)]
                info['line1'] = labels[0] if len(labels) > 0 else ''
                info['line2'] = labels[1] if len(labels) > 1 else ''
            else:
                if ':' in part:
                    k, v = part.split(':', 1)
                    k = k.strip()
                    v = v.strip()
                    if k == 'target_layer' and v.isdigit():
                        info[k] = int(v)
                    else:
                        info[k] = v
        meta[beh_name] = info

    # 2. Auto-derive tap-dance behaviors without explicit annotations
    beh_block_pattern = re.compile(r'([a-zA-Z0-9_]+)\s*:\s*([a-zA-Z0-9_]+)\s*\{([^}]+)\};', re.DOTALL)
    for m in beh_block_pattern.finditer(dts_text):
        beh_name = m.group(1).strip()
        body = m.group(3)
        if beh_name not in meta and 'zmk,behavior-tap-dance' in body:
            bm = re.search(r'bindings\s*=\s*([^;]+);', body)
            if bm:
                raw_bindings = re.findall(r'<([^>]+)>', bm.group(1))
                formatted_steps = []
                target_l = None
                for rb in raw_bindings:
                    parts = rb.split(None, 1)
                    param = parts[1] if len(parts) > 1 else parts[0]
                    formatted_steps.append(format_param_recursive(param))
                    if layer_names and target_l is None:
                        for l_idx, l_name in enumerate(layer_names):
                            if l_name.lower() in rb.lower() or f"layer_{l_name.lower()}" in rb.lower():
                                target_l = l_idx
                                break

                info = {
                    'name': beh_name,
                    'line1': formatted_steps[0] if len(formatted_steps) > 0 else beh_name,
                    'line2': formatted_steps[1] if len(formatted_steps) > 1 else '',
                    'badge': 'TD',
                    'badge_type': 'td',
                    'tooltip': f"Tap Dance: {' • '.join(f'{i+1}x {s}' for i, s in enumerate(formatted_steps))}"
                }
                if target_l is not None:
                    info['target_layer'] = target_l
                    if layer_names and target_l < len(layer_names):
                        info['icon'] = f"layer_{layer_names[target_l].lower()}"
                meta[beh_name] = info

    return meta

def parse_key_data(key_obj, layer_names, custom_meta=None):
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

    icon = None

    if beh == '&kp':
        p0 = str(raw_params[0].get('value', '')) if (raw_params and isinstance(raw_params[0], dict)) else str(raw_params[0]) if raw_params else ''
        primary_text = formatted_params[0] if formatted_params else ''
        if p0 in KEY_METADATA:
            line1 = KEY_METADATA[p0][0]
            icon = KEY_METADATA[p0][2]
            tooltip = f"Key: {KEY_METADATA[p0][1]}"
        elif ' ' in primary_text and len(primary_text) > 4:
            parts = primary_text.split(None, 1)
            line1, line2 = parts[0], parts[1]
            tooltip = f"Key: {primary_text}"
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

    elif beh in ['&hold_tap_layer', '&lt', '&mt']:
        layer_idx = int(raw_params[0].get('value', 0)) if (raw_params and str(raw_params[0].get('value', '')).isdigit()) else 0
        tap_p = raw_params[1] if len(raw_params) > 1 else ''
        tap_val = str(tap_p.get('value', '')) if isinstance(tap_p, dict) else str(tap_p)
        tap_formatted = formatted_params[1] if len(formatted_params) > 1 else 'TAP'

        line1 = tap_formatted
        if tap_val in KEY_METADATA:
            line1 = KEY_METADATA[tap_val][0]
            icon = KEY_METADATA[tap_val][2]

        if beh == '&hold_tap_layer':
            layer_name = layer_names[layer_idx] if layer_idx < len(layer_names) else f"Layer {layer_idx}"
            secondary = format_layer_badge(layer_name)
            target_layer = layer_idx
            badge_type = 'layer'
            tooltip = f"Tap for {tap_formatted} • Hold for {layer_name} (Click or hover to view layer)"
        elif beh == '&lt':
            layer_name = layer_names[layer_idx] if layer_idx < len(layer_names) else f"Layer {layer_idx}"
            secondary = format_layer_badge(layer_name)
            target_layer = layer_idx
            badge_type = 'layer'
            tooltip = f"Tap for {tap_formatted} • Hold for {layer_name} (Click or hover to view layer)"
        elif beh == '&mt':
            mod = formatted_params[0] if len(formatted_params) > 0 else ''
            secondary = mod.split()[0] if mod else ''
            badge_type = 'mod'
            tooltip = f"Mod-Tap: Tap for {tap_formatted} • Hold for {mod}"

    elif beh in ['&layer', '&mo']:
        layer_idx = int(raw_params[0].get('value', 0)) if str(raw_params[0].get('value', '')).isdigit() else 0
        layer_name = layer_names[layer_idx] if layer_idx < len(layer_names) else f"Layer {layer_idx}"
        line1 = layer_name
        secondary = ''
        target_layer = layer_idx
        badge = 'TD' if beh == '&layer' else ''
        badge_type = 'td' if beh == '&layer' else 'layer'
        icon = f"layer_{layer_name.lower()}"
        tooltip = f"Layer: {layer_name} ({'Tap: Toggle • Hold: Momentary' if beh == '&layer' else 'Hold to activate'})"

    elif beh == '&to':
        layer_idx = int(raw_params[0].get('value', 0)) if str(raw_params[0].get('value', '')).isdigit() else 0
        layer_name = layer_names[layer_idx] if layer_idx < len(layer_names) else f"Layer {layer_idx}"
        line1 = layer_name
        line2 = ''
        target_layer = layer_idx
        secondary = ''
        badge = 'To'
        badge_type = 'to'
        icon = f"layer_{layer_name.lower()}"
        tooltip = f"Switch to {layer_name} (Click or hover to view layer)"

    elif beh == '&tog':
        layer_idx = int(raw_params[0].get('value', 0)) if str(raw_params[0].get('value', '')).isdigit() else 0
        layer_name = layer_names[layer_idx] if layer_idx < len(layer_names) else f"Layer {layer_idx}"
        line1 = layer_name
        line2 = ''
        target_layer = layer_idx
        secondary = ''
        badge = 'Tog'
        badge_type = 'tog'
        icon = f"layer_{layer_name.lower()}"
        tooltip = f"Toggle {layer_name} (Click or hover to view layer)"

    elif beh == '&magic':
        line1 = 'Magic'
        target_layer = layer_names.index('Magic') if 'Magic' in layer_names else None
        secondary = ''
        badge = ''
        badge_type = 'sys'
        icon = 'layer_magic'
        tooltip = 'Magic Configuration Layer (Click or hover to view layer)'

    elif beh == 'Custom':
        custom_str = str(raw_params[0].get('value', '')) if raw_params else ''
        raw_binding = custom_str

        # If custom string wraps a standard command like '&msc SNIPER_SCRL_LEFT' or '&mmv ...'
        if custom_str.startswith('&') and ' ' in custom_str:
            parts = custom_str.split(None, 1)
            sub_key_obj = {'value': parts[0], 'params': [{'value': parts[1], 'params': []}]}
            return parse_key_data(sub_key_obj, layer_names, custom_meta)

        clean_name = custom_str.lstrip('&')
        if custom_meta and clean_name in custom_meta:
            m = custom_meta[clean_name]
            line1 = m.get('line1', clean_name)
            line2 = m.get('line2', '')
            badge = m.get('badge', 'TD')
            badge_type = m.get('badge_type', 'td')
            tooltip = m.get('tooltip', f"Custom Behavior: {clean_name}")
            if 'target_layer' in m:
                target_layer = m['target_layer']
            if 'icon' in m:
                icon = m['icon']
            elif target_layer is not None and layer_names and target_layer < len(layer_names):
                icon = f"layer_{layer_names[target_layer].lower()}"
            else:
                for sym, _, ic in KEY_METADATA.values():
                    if line1 == sym:
                        icon = ic
                        break
        elif 'td_layer_' in custom_str.lower():
            m = re.search(r'td_layer_([a-zA-Z0-9_]+)', custom_str, re.IGNORECASE)
            layer_match = m.group(1) if m else ''
            l_idx = None
            l_name = layer_match
            for idx, ln in enumerate(layer_names):
                if ln.lower() == layer_match.lower():
                    l_idx = idx
                    l_name = ln
                    break
            line1 = l_name
            secondary = ''
            target_layer = l_idx
            badge = 'TD'
            badge_type = 'td'
            icon = f"layer_{l_name.lower()}"
            tooltip = f"Layer: {l_name} (Tap: Toggle • Hold: Momentary)"
        else:
            line1 = clean_name
            tooltip = custom_str

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
        sub = str(raw_params[0].get('value', '')) if raw_params else ''
        direction = sub.split('_')[-1]
        arrows = {'UP': '↑', 'DOWN': '↓', 'LEFT': '←', 'RIGHT': '→'}
        is_sniper = 'SNIPER' in sub
        line1 = '🎯 Move' if is_sniper else 'Mouse'
        line2 = arrows.get(direction, direction)
        badge_type = 'mouse'
        tooltip = f"{'Sniper Precision ' if is_sniper else 'Mouse '}Move {direction}"
    elif beh == '&msc':
        sub = str(raw_params[0].get('value', '')) if raw_params else ''
        direction = sub.split('_')[-1]
        arrows = {'UP': '↑', 'DOWN': '↓', 'LEFT': '←', 'RIGHT': '→'}
        is_sniper = 'SNIPER' in sub
        line1 = '🎯 Scrl' if is_sniper else 'Scrl'
        line2 = arrows.get(direction, direction)
        badge_type = 'mouse'
        tooltip = f"{'Sniper Precision ' if is_sniper else 'Mouse '}Scroll {direction}"
    elif beh == '&mkp':
        sub = str(raw_params[0].get('value', '')).replace('CLK', '') if raw_params else ''
        labels = {'L': 'L-Click', 'R': 'R-Click', 'M': 'M-Click'}
        line1 = labels.get(sub, f"Click {sub}")
        badge_type = 'mouse'
        tooltip = f"Mouse {line1}"
    else:
        line1 = beh
        tooltip = raw_binding

    # Deduplicate secondary label if it repeats line1 or line2
    if secondary and (secondary == line1 or secondary == line2 or (line2 and secondary in line2)):
        secondary = ''

    return {
        'line1': line1,
        'line2': line2,
        'secondary': secondary,
        'badge': badge,
        'badgeType': badge_type,
        'tooltip': tooltip,
        'targetLayer': target_layer,
        'rawBinding': raw_binding,
        'icon': icon
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

    g80_custom_meta = parse_custom_behavior_annotations(g80_json.get('custom_defined_behaviors', ''), keyboards['glove80']['layerNames'])
    go60_custom_meta = parse_custom_behavior_annotations(go60_json.get('custom_defined_behaviors', ''), keyboards['go60']['layerNames'])

    # Process Glove80 layers
    for layer_idx, layer_name in enumerate(keyboards['glove80']['layerNames']):
        raw_layer = g80_json['layers'][layer_idx]
        rgb_tokens = g80_rgb.get(layer_name, ['___'] * 80)
        parsed_keys = []
        for key_idx, key_obj in enumerate(raw_layer):
            kdata = parse_key_data(key_obj, keyboards['glove80']['layerNames'], g80_custom_meta)
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
            kdata = parse_key_data(key_obj, keyboards['go60']['layerNames'], go60_custom_meta)
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

    # Data placeholder (empty script tag for dynamic data.json fetch)
    html = html.replace('<!-- EMBEDDED_DATA_PLACEHOLDER -->', '<script id="embedded-data" type="application/json"></script>')

    # Inline JS
    js_tag = f"<script>\n{js}\n</script>"
    html = html.replace('<script src="app.js"></script>', js_tag)

    return html

def main():
    print("Building MoErgo Layout Viewer...")
    data = build_data()

    # Save standalone viewer/data.json
    data_path = os.path.join(BASE_DIR, 'viewer', 'data.json')
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Generated data file: {data_path}")

    # Save docs/data.json for GitHub Pages
    docs_dir = os.path.join(BASE_DIR, 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    docs_data_path = os.path.join(docs_dir, 'data.json')
    with open(docs_data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Generated docs data file: {docs_data_path}")

    html_content = generate_standalone_html(data)

    out_path = os.path.join(BASE_DIR, 'viewer', 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    docs_path = os.path.join(docs_dir, 'index.html')
    with open(docs_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Auto-version sw.js with data hash so browsers always detect layout updates
    data_hash = hashlib.sha256(json.dumps(data).encode('utf-8')).hexdigest()[:8]
    sw_path = os.path.join(BASE_DIR, 'viewer', 'sw.js')
    if os.path.exists(sw_path):
        with open(sw_path, 'r', encoding='utf-8') as f:
            sw_code = f.read()
        sw_code = re.sub(r"const CACHE_NAME = ['\"][^'\"]+['\"];", f"const CACHE_NAME = 'moergo-layout-{data_hash}';", sw_code)
        with open(sw_path, 'w', encoding='utf-8') as f:
            f.write(sw_code)

    # Sync PWA assets (manifest, service worker, icons) to docs/
    pwa_files = [
        'manifest.json',
        'sw.js',
        'favicon.svg',
        'icon-192.png',
        'icon-512.png',
        'icon-maskable-512.png',
    ]
    viewer_dir = os.path.join(BASE_DIR, 'viewer')
    for fname in pwa_files:
        src = os.path.join(viewer_dir, fname)
        if os.path.exists(src):
            dst = os.path.join(docs_dir, fname)
            shutil.copy2(src, dst)

    size_kb = len(html_content.encode('utf-8')) / 1024
    print(f"Generated viewer: {out_path} and {docs_path} ({size_kb:.1f} KB)")
    print(f"Synced {len(pwa_files)} PWA assets to {docs_dir}")

if __name__ == '__main__':
    main()
