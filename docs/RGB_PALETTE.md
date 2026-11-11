# MoErgo ZMK Layout Per-Key RGB Color Palette Reference

This document provides a comprehensive reference for the per-key RGB underglow color coding scheme across the Glove80 and Go60 keyboards.

---

## 1. Color Palette Tokens

| Token | Name | Hex Code | RGB (Dec) | Visual Swatch | Functional Category & Usage |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **`BLU`** | Blue | `#0066FF` | `(0, 102, 255)` | 🟦 | **Modifiers & Connectivity:** Home Row Mods (`hml` / `hmr`), primary thumb Shift, upper thumb mods (Ctrl, Alt, GUI), Gaming active mods, and Bluetooth profile selection in Magic layer. |
| **`GRN`** | Green | `#00FF00` | `(0, 255, 0)` | 🟩 | **Navigation & Mouse:** Vim navigation cluster (HJKL / Left, Down, Up, Right), Home, End, PageUp, PageDown, Mouse cursor movement (`mmv`), mouse clicks (Left, Right, Middle), and browser Back/Forward (`MB4`, `MB5`). |
| **`YLW`** | Yellow | `#FFFF00` | `(255, 255, 0)` | 🟨 | **Numbers & Function Keys:** Number row digits (1–0) in `layer_NumRow`, Keypad digits (0–9) in `layer_Keypad`, and Function keys (F1–F12) in `layer_SymbolNav`. |
| **`CYN`** | Cyan | `#00FFFF` | `(0, 255, 255)` | 🩵 | **Media & Hardware Controls:** Volume controls (`Vol Dn`, `Vol Up`, `Mute`), media keys (`Prev`, `Next`, `Play/Pause`), and screen brightness in `layer_Magic`. |
| **`WHT`** | White | `#FFFFFF` | `(255, 255, 255)` | ⬜ | **Regular Symbols, Math & PC Overrides:** All standard punctuation / math operators (`@`, `#`, `$`, `%`, `^`, `&`, `*`, `+`, `-`, `=`, `/`, `\`, `|`, `<`, `>`, `~`, `` ` ``), Brackets & Braces (`[ ]`, `{ }`), Parentheses (`( )`), Double Quote (`"`), Keypad operators (`+`, `-`, `*`, `/`, `=`, `.`, Enter), and PC layer Copy/Paste Tap Dance (`td_copy_paste_pc`). |
| **`GLD`** | Gold | `#FFBF00` | `(255, 191, 0)` | 🟧 | **Base Tap Dances, Scroll & Underglow:** Base layer tap dances (`td_caps`, `td_copy_paste`, `td_launcher`, `td_screenshot`, `td_browser`, `td_media`, `td_wm_prev`, `td_wm_next`), mouse wheel scrolling (`msc`), and RGB underglow controls in Magic. |
| **`RED`** | Red | `#FF0000` | `(255, 0, 0)` | 🟥 | **Layer Controls, System & Locks:** Layer toggles & momentary thumb activators (NumRow, SymbolNav, Keypad, PC, Gaming, Mouse, Sniper), layer exit keys (`ESC`, `tog`), system locks, Bootloader, Reset, Delete keys, and Sniper precision motion. |
| **`MAG`** | Magenta | `#FF00FF` | `(255, 0, 255)` | 🟪 | **Magic Key & System Indicator:** Dedicated indicator for the Magic layer access key across all permanent layers (Base, PC, Gaming). |
| **`NML`** | NumLock | Dynamic | — | 🟢/🔴 | **NumLock Status Indicator:** Green when NumLock is ON, Red when OFF. |
| **`CPL`** | CapsLock | Dynamic | — | ⚫/🔴 | **CapsLock Status Indicator:** Unlit when OFF, Red when CapsLock or Caps Word is active. |
| **`___`** | Black / Off | `#000000` | `(0, 0, 0)` | ⬛ | **Unlit / Pass-Through:** Normal alphanumeric keys, unmodified gaming keys, transparent pass-through positions, or inactive keys. |

---

## 2. Layer Color Mapping Matrix

### Base Layer (`layer_Base`)
- **Red (`RED`)**: Layer keys (`td_LAYER_Keypad`, NumRow Tab thumb, SymbolNav Del thumb, Mouse toggle on Glove80).
- **Blue (`BLU`)**: Home Row Mods (A, S, D, F and J, K, L, ;) and Left Thumb Shift (`&kp LSHFT`). Glove80 upper thumbs (Ctrl, Alt, GUI).
- **Gold (`GLD`)**: Base tap dances (`td_caps`, `td_copy_paste`, `td_launcher`, `td_screenshot`, `td_browser`, `td_media`, `td_wm_prev`, `td_wm_next`).
- **Magenta (`MAG`)**: Magic key (`&magic LAYER_Magic 0`).

### PC Layer (`layer_PC`)
- Mirrors Base layer RGB highlights.
- **Red (`RED`)**: Layer thumb keys and toggles.
- **White (`WHT`)**: PC Copy/Paste tap dance (`td_copy_paste_pc` — 1x Ctrl+C, 2x Ctrl+V, 3x Win+V), clearly distinguished from Base layer's Gold.
- **Blue (`BLU`)**: Modifiers, Home Row Mods, and thumb Shift.
- **Magenta (`MAG`)**: Magic key.

### Gaming Layer (`layer_Gaming`)
- **Blue (`BLU`)**: Active modifier keys only (Bottom row Cmd/Super, Thumb Shift, Hold-Tap Ctrl/Space, Hold-Tap Alt/Enter).
- **Magenta (`MAG`)**: Magic key.
- **Unlit (`___`)**: All home row keys (ASDF, JKL;), numbers, and overridden non-modifier keys (Grave, Tab, Tilde, Backspace, Delete) remain dark to signify they behave as standard, non-modifier gaming keys.

### SymbolNav Layer (`layer_SymbolNav`)
- **Yellow (`YLW`)**: Function keys (F1–F12).
- **Green (`GRN`)**: Vim navigation cluster (HJKL arrows), Home, End, PageUp, PageDown.
- **White (`WHT`)**: All symbols, punctuation, brackets `[ ]`, braces `{ }`, parentheses `( )`, math operators, and Double Quote (`"`).

### Keypad Layer (`layer_Keypad`)
- **Yellow (`YLW`)**: 3x3 numeric digit block (0–9).
- **White (`WHT`)**: Arithmetic operators (`+`, `-`, `*`, `/`, `=`, `.`) and Keypad Enter.
- **Red (`RED`)**: Keypad exit toggle key (top-left).

### NumRow Layer (`layer_NumRow`)
- **Yellow (`YLW`)**: Home row numbers 1–0 across A–G and H–;.
- **Unlit (`___`)**: All other keys unlit.

### Magic Layer (`layer_Magic`)
- **Red (`RED`)**: Bootloader, Reset, system lock keys, and layer toggles (`PC`, `Gaming`, `Mouse`).
- **Blue (`BLU`)**: Bluetooth profile keys (BT 0, BT 1, BT 2) and USB output.
- **Cyan (`CYN`)**: Volume, media, and screen brightness controls (`Vol Dn`, `Vol Up`, `Mute`, `Prev`, `Next`, `PP`, `Bri Dn`, `Bri Up`).
- **Gold (`GLD`)**: RGB underglow controls.

### Mouse Layer (`layer_Mouse`)
- **Green (`GRN`)**: Mouse cursor movement (`mmv`), mouse click buttons (Left, Right, Middle), and browser Back/Forward navigation (`MB4`, `MB5`).
- **Gold (`GLD`)**: Mouse wheel scrolling (`msc`).
- **Red (`RED`)**: Mouse layer exit keys (`kp ESC` and `tog LAYER_Mouse`), and Sniper mode momentary activator (`mo LAYER_Sniper` on Glove80).

### Sniper Layer (`layer_Sniper`)
- **Red (`RED`)**: Sniper precision mouse movement (`mmv`).
- **Gold (`GLD`)**: Sniper precision scrolling (`msc`).

---

## 3. Automated RGB Generation (`scripts/generate_rgb.py`)

The layout RGB matrices can be verified and generated automatically from keymap bindings using `scripts/generate_rgb.py`:

```bash
# Verify that keymaps match color palette rules (exits with code 0 if synced, 1 if differences):
python3 scripts/generate_rgb.py --check

# Display token diffs without modifying files:
python3 scripts/generate_rgb.py --diff

# Regenerate and apply per-key underglow matrices to both keymap files:
python3 scripts/generate_rgb.py

# Target only a specific keyboard:
python3 scripts/generate_rgb.py go60
python3 scripts/generate_rgb.py glove80
```

