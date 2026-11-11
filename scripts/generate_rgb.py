#!/usr/bin/env python3
"""
scripts/generate_rgb.py

Automates the generation, validation, and updating of per-key RGB underglow layers
(`underglow-layer` blocks) in `go60/config/go60.keymap` and `glove80/config/glove80.keymap`.

Rules follow docs/RGB_PALETTE.md (v45):
- BLU: Modifiers (Home Row Mods hml/hmr, Shift, Ctrl, Alt, GUI), BT profiles, USB out.
- GRN: Navigation (Vim arrows HJKL, Home, End, PgUp, PgDn, Mouse move, Mouse clicks, Back/Forward).
- YLW: Numbers (0-9) & Function keys (F1-F12).
- CYN: Volume, media, and screen brightness controls in Magic layer.
- WHT: Regular symbols, math operators, Double Quote ("), PC Copy/Paste, Keypad operators.
- GLD: Enclosure pairs [ ] ( ) { }, Base macOS tap dances, Mouse scroll, RGB controls.
- RED: Layer activators & toggles, system locks, bootloader, reset, deletes, layer exits, Sniper move.
- MAG: Magic key & system indicator.
- CPL: CapsLock / CapsWord dynamic indicator.
- NML: NumLock dynamic indicator.
- ___: Unlit / pass-through.

Usage:
    python3 scripts/generate_rgb.py [--check] [--diff] [--apply] [--dry-run] [go60] [glove80]
"""

import os
import sys
import re
import argparse
from typing import Dict, List, Tuple, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

KEYBOARD_CONFIGS = {
    'go60': {
        'name': 'Go60',
        'keyCount': 60,
        'keymapPath': os.path.join(BASE_DIR, 'go60', 'config', 'go60.keymap'),
        'layers': ['Base', 'PC', 'Gaming', 'SymbolNav', 'Keypad', 'NumRow', 'Magic', 'Mouse'],
    },
    'glove80': {
        'name': 'Glove80',
        'keyCount': 80,
        'keymapPath': os.path.join(BASE_DIR, 'glove80', 'config', 'glove80.keymap'),
        'layers': ['Base', 'PC', 'Gaming', 'SymbolNav', 'Keypad', 'NumRow', 'Magic', 'Mouse', 'Sniper'],
    }
}

# --- ANSI Colors for CLI output ---
USE_COLOR = sys.stdout.isatty() and 'NO_COLOR' not in os.environ

def color_text(text: str, color_code: str) -> str:
    if not USE_COLOR:
        return text
    return f"\033[{color_code}m{text}\033[0m"

def c_green(text: str) -> str: return color_text(text, '32')
def c_red(text: str) -> str: return color_text(text, '31')
def c_yellow(text: str) -> str: return color_text(text, '33')
def c_cyan(text: str) -> str: return color_text(text, '36')
def c_bold(text: str) -> str: return color_text(text, '1')

# --- Keymap Parser ---

def parse_keymap_bindings(keymap_content: str) -> Dict[str, List[str]]:
    """
    Parses ZMK bindings from keymap { ... } section.
    Returns mapping from layer name (e.g. 'Base') to list of binding strings (e.g. '&kp N1', '&hml LGUI A').
    """
    km_start = keymap_content.find('keymap {')
    if km_start == -1:
        raise ValueError("Could not find 'keymap {' in keymap file.")
    ug_start = keymap_content.find('underglow-layer {', km_start)
    km_section = keymap_content[km_start:ug_start] if ug_start != -1 else keymap_content[km_start:]

    layer_pattern = r'layer_([a-zA-Z0-9_]+)\s*\{[^}]*bindings\s*=\s*<([^>]+)>;'
    layers = {}

    for name, raw_bindings in re.findall(layer_pattern, km_section, re.DOTALL):
        tokens = raw_bindings.split()
        bindings = []
        current = []
        for tok in tokens:
            if tok.startswith('&'):
                if current:
                    bindings.append(' '.join(current))
                current = [tok]
            else:
                current.append(tok)
        if current:
            bindings.append(' '.join(current))
        layers[name] = bindings

    return layers

def parse_existing_underglow(keymap_content: str) -> Dict[str, List[str]]:
    """
    Parses current RGB tokens from underglow-layer { ... } section.
    Returns mapping from layer name to list of tokens (e.g. ['GRN', '___', ...]).
    """
    ug_start = keymap_content.find('underglow-layer {')
    if ug_start == -1:
        return {}

    layer_pattern = r'layer_([a-zA-Z0-9_]+)\s*\{([^}]+bindings\s*=\s*<([^>]+)>[^}]*)\};'
    layers = {}

    for m in re.finditer(layer_pattern, keymap_content[ug_start:], re.DOTALL):
        name = m.group(1)
        raw = m.group(3)
        tokens = [t for t in raw.split() if t and not t.startswith('/*')]
        layers[name] = tokens

    return layers

# --- RGB Classification Engine ---

MODIFIER_KEYS = {
    '&kp LSHFT', '&kp RSHFT',
    '&kp LCTRL', '&kp RCTRL',
    '&kp LALT',  '&kp RALT',
    '&kp LGUI',  '&kp RGUI',
}

FUNCTION_KEYS = {f'&kp F{i}' for i in range(1, 13)}

NAVIGATION_KEYS = {
    '&kp LEFT', '&kp DOWN', '&kp UP', '&kp RIGHT',
    '&kp HOME', '&kp END',  '&kp PG_UP', '&kp PG_DN',
}

ENCLOSURE_KEYS = {
    '&kp LBKT',     '&kp RBKT',
    '&kp LS(N9)',   '&kp LS(N0)',
    '&kp LS(LBKT)', '&kp LS(RBKT)',
}

KEYPAD_DIGITS = {f'&kp KP_N{i}' for i in range(10)}

KEYPAD_OPERATORS = {
    '&kp KP_MINUS', '&kp KP_SLASH', '&kp KP_PLUS',
    '&kp KP_MULTIPLY', '&kp KP_EQUAL', '&kp KP_DOT', '&kp KP_ENTER',
}

NUMROW_DIGITS = {f'&kp N{i}' for i in range(10)} | {f'&kp NUMBER_{i}' for i in range(10)}

MAGIC_RED_KEYS = {
    '&bt BT_CLR', '&bt BT_CLR_ALL',
    '&bootloader', '&sys_reset',
    '&to LAYER_Factory',
    '&kp INS', '&kp SLCK', '&kp PSCRN',
}

MAGIC_CYAN_KEYS = {
    '&kp C_VOL_DN', '&kp C_VOL_UP', '&kp C_MUTE',
    '&kp C_PREV',   '&kp C_NEXT',   '&kp C_PP',
    '&kp C_BRI_DN', '&kp C_BRI_UP',
}

def classify_key(
    binding: str,
    layer_name: str,
    key_idx: int,
    base_bindings: List[str],
    base_tokens: List[str],
    kb_type: str
) -> str:
    """
    Classifies a single key binding into its corresponding underglow RGB color token
    based on layer rules from docs/RGB_PALETTE.md.
    """
    # 1. Base Layer
    if layer_name == 'Base':
        if binding == '&td_caps':
            return 'CPL'
        if binding.startswith('&magic'):
            return 'MAG'
        if (binding == '&td_LAYER_Keypad' or
            binding.startswith('&tog ') or
            binding.startswith('&to ') or
            binding.startswith('&lt ') or
            binding.startswith('&hold_tap_layer ')):
            return 'RED'
        if (binding.startswith('&hml ') or
            binding.startswith('&hmr ') or
            binding in MODIFIER_KEYS):
            return 'BLU'
        if binding.startswith('&td_'):
            return 'GLD'
        return '___'

    # 2. PC Layer (Overlay on Base)
    if layer_name == 'PC':
        if binding == '&td_copy_paste_pc':
            return 'WHT'
        if binding == '&trans':
            return base_tokens[key_idx] if key_idx < len(base_tokens) else '___'
        return '___'

    # 3. Gaming Layer
    if layer_name == 'Gaming':
        if binding.startswith('&magic'):
            return 'MAG'
        if binding in MODIFIER_KEYS or binding.startswith('&mt '):
            return 'BLU'
        # Thumb Shift inherited from Base (key 54 on Go60, key 69 on Glove80)
        if binding == '&trans' and key_idx < len(base_bindings):
            if base_bindings[key_idx] in ('&kp LSHFT', '&kp RSHFT'):
                return 'BLU'
        return '___'

    # 4. SymbolNav Layer
    if layer_name == 'SymbolNav':
        if binding in FUNCTION_KEYS:
            return 'YLW'
        if binding in NAVIGATION_KEYS:
            return 'GRN'
        if binding in ENCLOSURE_KEYS:
            return 'GLD'
        if binding in ('&trans', '&none'):
            return '___'
        # All regular punctuation, symbols, math operators, double quote (")
        return 'WHT'

    # 5. Keypad Layer
    if layer_name == 'Keypad':
        if binding == '&tog LAYER_Keypad':
            return 'RED'
        if binding in KEYPAD_DIGITS:
            return 'YLW'
        if binding in KEYPAD_OPERATORS:
            return 'WHT'
        return '___'

    # 6. NumRow Layer
    if layer_name == 'NumRow':
        if binding in NUMROW_DIGITS:
            return 'YLW'
        # CapsLock indicator pass-through from Base
        if binding == '&trans' and key_idx < len(base_bindings):
            if base_bindings[key_idx] == '&td_caps':
                return 'CPL'
        return '___'

    # 7. Magic Layer
    if layer_name == 'Magic':
        if binding in MAGIC_RED_KEYS:
            return 'RED'
        if binding.startswith('&rgb_ug'):
            return 'GLD'
        if binding in MAGIC_CYAN_KEYS:
            return 'CYN'
        if (binding.startswith('&bt_') or
            binding == '&out OUT_USB' or
            (binding.startswith('&bt ') and 'SEL' in binding)):
            return 'BLU'
        if binding.startswith('&tog LAYER_'):
            return 'RED'
        return '___'

    # 8. Mouse Layer
    if layer_name == 'Mouse':
        if binding in ('&kp ESC', '&tog LAYER_Mouse'):
            return 'RED'
        if binding == '&mo LAYER_Sniper':
            return 'RED'
        if binding.startswith('&msc '):
            return 'GLD'
        if binding in ('&mkp MB4', '&mkp MB5'):
            return 'GRN'
        if binding.startswith('&mmv ') or binding.startswith('&mkp '):
            return 'GRN'
        return '___'

    # 9. Sniper Layer
    if layer_name == 'Sniper':
        if binding.startswith('&msc '):
            return 'GLD'
        if binding.startswith('&mmv '):
            return 'RED'
        return '___'

    return '___'

def generate_layer_tokens(
    layer_name: str,
    bindings: List[str],
    base_bindings: List[str],
    base_tokens: List[str],
    kb_type: str
) -> List[str]:
    """Generates RGB tokens for all keys in a given layer."""
    tokens = []
    for idx, binding in enumerate(bindings):
        token = classify_key(binding, layer_name, idx, base_bindings, base_tokens, kb_type)
        tokens.append(token)
    return tokens

# --- Formatting Engine ---

def format_go60_layer(tokens: List[str]) -> str:
    """Formats 60 RGB tokens into Go60 ASCII matrix."""
    assert len(tokens) == 60, f"Expected 60 tokens, got {len(tokens)}"
    r0 = ' ' + '  '.join(tokens[0:6]) + ' ' * 50 + '  '.join(tokens[6:12])
    r1 = ' ' + '  '.join(tokens[12:18]) + ' ' * 50 + '  '.join(tokens[18:24])
    r2 = ' ' + '  '.join(tokens[24:30]) + ' ' * 50 + '  '.join(tokens[30:36])
    r3 = ' ' + '  '.join(tokens[36:42]) + ' ' * 50 + '  '.join(tokens[42:48])
    r4 = ' ' * 11 + '  '.join(tokens[48:51]) + ' ' * 60 + '  '.join(tokens[51:54])
    r5 = ' ' * 47 + '  '.join(tokens[54:57]) + '  ' + '  '.join(tokens[57:60])
    return '\n'.join([r0, r1, r2, r3, r4, r5])

def format_glove80_layer(tokens: List[str]) -> str:
    """Formats 80 RGB tokens into Glove80 ASCII matrix."""
    assert len(tokens) == 80, f"Expected 80 tokens, got {len(tokens)}"
    r0 = ' ' + '  '.join(tokens[0:5]) + ' ' * 86 + '  '.join(tokens[5:10])
    r1 = ' ' + '  '.join(tokens[10:16]) + ' ' * 76 + '  '.join(tokens[16:22])
    r2 = ' ' + '  '.join(tokens[22:28]) + ' ' * 76 + '  '.join(tokens[28:34])
    r3 = ' ' + '  '.join(tokens[34:40]) + ' ' * 76 + '  '.join(tokens[40:46])
    r4 = ' ' + '  '.join(tokens[46:52]) + '  ' + '  '.join(tokens[52:55]) + ' ' * 6 + '  '.join(tokens[55:58]) + ' ' * 6 + '  '.join(tokens[58:64])
    r5 = ' ' + '  '.join(tokens[64:69]) + ' ' * 7 + '  '.join(tokens[69:72]) + ' ' * 6 + '  '.join(tokens[72:75]) + ' ' * 11 + '  '.join(tokens[75:80])
    return '\n'.join([r0, r1, r2, r3, r4, r5])

def format_underglow_matrix(kb_type: str, tokens: List[str]) -> str:
    if kb_type == 'go60':
        return format_go60_layer(tokens)
    elif kb_type == 'glove80':
        return format_glove80_layer(tokens)
    else:
        raise ValueError(f"Unknown keyboard type: {kb_type}")

# --- Core Processor ---

def process_keyboard(
    kb_type: str,
    action: str = 'apply',
    dry_run: bool = False,
    verbose: bool = False
) -> Tuple[bool, int, str]:
    """
    Processes a keyboard layout:
    - Parses bindings and existing RGB tokens
    - Generates expected tokens
    - In '--check' mode: checks for differences (returns True if in sync)
    - In '--diff' mode: formats and displays diffs
    - In '--apply' mode: rewrites underglow-layer blocks in keymap
    Returns (is_sync, diff_count, summary_report).
    """
    config = KEYBOARD_CONFIGS[kb_type]
    keymap_path = config['keymapPath']
    layers_to_process = config['layers']

    with open(keymap_path, 'r', encoding='utf-8') as f:
        content = f.read()

    km_layers = parse_keymap_bindings(content)
    ug_layers = parse_existing_underglow(content)

    if 'Base' not in km_layers:
        raise ValueError(f"{kb_type}: 'Base' layer not found in keymap.")

    base_bindings = km_layers['Base']
    base_tokens = generate_layer_tokens('Base', base_bindings, base_bindings, [], kb_type)

    generated_layers: Dict[str, List[str]] = {'Base': base_tokens}
    for layer_name in layers_to_process:
        if layer_name == 'Base':
            continue
        bindings = km_layers.get(layer_name, [])
        if not bindings:
            continue
        tokens = generate_layer_tokens(layer_name, bindings, base_bindings, base_tokens, kb_type)
        generated_layers[layer_name] = tokens

    # Compare with existing
    diffs = []
    for layer_name in layers_to_process:
        if layer_name not in generated_layers:
            continue
        gen = generated_layers[layer_name]
        cur = ug_layers.get(layer_name, [])
        if gen != cur:
            for idx, (g_tok, c_tok) in enumerate(zip(gen, cur)):
                if g_tok != c_tok:
                    binding = km_layers[layer_name][idx] if idx < len(km_layers[layer_name]) else '?'
                    diffs.append({
                        'keyboard': kb_type,
                        'layer': layer_name,
                        'index': idx,
                        'binding': binding,
                        'current': c_tok,
                        'generated': g_tok,
                    })

    is_sync = len(diffs) == 0

    # Build report
    report_lines = []
    report_lines.append(c_bold(f"=== {config['name']} ({config['keyCount']} keys) ==="))

    if is_sync:
        report_lines.append(c_green(f"  ✓ All {len(generated_layers)} layers in sync with keymap bindings."))
    else:
        report_lines.append(c_yellow(f"  ⚠ Found {len(diffs)} difference(s) across {len(set(d['layer'] for d in diffs))} layer(s):"))
        for d in diffs:
            report_lines.append(
                f"    - [{d['layer']}:{d['index']:02d}] {d['binding']:<30s} "
                f"current={c_red(d['current'])} -> expected={c_green(d['generated'])}"
            )

    # Apply changes if requested and differences exist
    if action == 'apply' and not is_sync:
        ug_pos = content.find('underglow-layer {')
        if ug_pos == -1:
            raise ValueError(f"Could not find 'underglow-layer {{' in {keymap_path}")
        prefix = content[:ug_pos]
        ug_content = content[ug_pos:]

        new_ug = ug_content
        for layer_name, tokens in generated_layers.items():
            matrix = format_underglow_matrix(kb_type, tokens)
            sub_pat = re.compile(
                rf'(layer_{re.escape(layer_name)}\s*\{{[^}}]*?bindings\s*=\s*<)\n.*?\n(\s*>;)',
                re.DOTALL
            )
            new_ug, count = sub_pat.subn(rf'\g<1>\n{matrix}\n\g<2>', new_ug)
            if count == 0:
                report_lines.append(c_red(f"    Failed to locate layer_{layer_name} inside underglow-layer block!"))

        if not dry_run:
            new_content = prefix + new_ug
            with open(keymap_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            report_lines.append(c_green(f"  ✓ Updated {keymap_path}"))
        else:
            report_lines.append(c_yellow(f"  [DRY RUN] Would update {keymap_path}"))

    return is_sync, len(diffs), '\n'.join(report_lines)

# --- CLI Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Generate, validate, and update per-key RGB layers for Glove80 and Go60 keymaps.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/generate_rgb.py --check          # Validate RGB layers without modifying files
  python3 scripts/generate_rgb.py --diff           # Show token diffs
  python3 scripts/generate_rgb.py                  # Apply RGB generation to both keyboards
  python3 scripts/generate_rgb.py go60             # Apply RGB generation only to Go60
        """
    )
    parser.add_argument('keyboards', nargs='*', choices=['go60', 'glove80'], help="Keyboards to process (default: all)")
    parser.add_argument('--check', action='store_true', help="Check if keymaps match generated RGB tokens and exit")
    parser.add_argument('--diff', action='store_true', help="Show differences without modifying files")
    parser.add_argument('--apply', action='store_true', help="Apply generated RGB matrices to keymap files (default)")
    parser.add_argument('--dry-run', action='store_true', help="Simulate applying changes without writing to disk")
    parser.add_argument('--no-viewer', action='store_true', help="Skip running build_viewer.py after applying changes")
    parser.add_argument('-v', '--verbose', action='store_true', help="Show verbose output")

    args = parser.parse_args()

    keyboards = args.keyboards if args.keyboards else ['go60', 'glove80']

    action = 'check' if args.check else ('diff' if args.diff else 'apply')

    all_sync = True
    total_diffs = 0

    for kb in keyboards:
        is_sync, diff_count, report = process_keyboard(
            kb_type=kb,
            action=action,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        print(report)
        print()
        if not is_sync:
            all_sync = False
            total_diffs += diff_count

    if action in ('check', 'diff'):
        if all_sync:
            print(c_green("All per-key RGB layers are in sync with keymap bindings."))
            sys.exit(0)
        else:
            print(c_red(f"Total differences found: {total_diffs}"))
            sys.exit(1)

    if action == 'apply' and not args.dry_run and not all_sync:
        if not args.no_viewer:
            print(c_cyan("Regenerating viewer data and standalone HTML..."))
            viewer_script = os.path.join(BASE_DIR, 'scripts', 'build_viewer.py')
            ret = os.system(f"python3 {viewer_script}")
            if ret != 0:
                print(c_red("Failed to rebuild viewer!"), file=sys.stderr)
                sys.exit(ret)

    print(c_green("Per-key RGB generation complete."))
    sys.exit(0)

if __name__ == '__main__':
    main()
