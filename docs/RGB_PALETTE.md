# MoErgo ZMK Layout Per-Key RGB Color Palette Reference

This document provides a comprehensive reference for the per-key RGB underglow color coding scheme across the Glove80 and Go60 keyboards.

---

## 1. Color Palette Tokens

| Token | Name | Hex Code | RGB (Dec) | Visual Swatch | Functional Category & Usage |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **`BLU`** | Blue | `#0066FF` | `(0, 102, 255)` | 🟦 | **Modifiers & Connectivity:** Home Row Mods (`hml` / `hmr`), primary thumb Shift, upper thumb mods (Ctrl, Alt, GUI), Gaming active mods, and Bluetooth profile selection in Magic layer. |
| **`ORG`** | Orange | `#FF5500` | `(255, 85, 0)` | 🟧 | **Navigation:** Vim navigation cluster (HJKL / Left, Down, Up, Right), Home, End, PageUp, PageDown, and Glove80 mouse cursor movement keys. |
| **`CYN`** | Cyan | `#00FFFF` | `(0, 255, 255)` | 🩵 | **Numbers & Function Keys:** Number row digits (1–0) in `layer_NumRow`, Keypad digits (0–9) in `layer_Keypad`, and Function keys (F1–F12) in `layer_SymbolNav`. |
| **`WHT`** | White | `#FFFFFF` | `(255, 255, 255)` | ⬜ | **Regular Symbols, Math & PC Overrides:** All standard punctuation / math operators (`@`, `#`, `$`, `%`, `^`, `&`, `*`, `+`, `-`, `=`, `/`, `\`, `|`, `<`, `>`, `~`, `` ` ``), Double Quote (`"`), Keypad operators (`+`, `-`, `*`, `/`, `=`, `.`, Enter), and PC layer Copy/Paste Tap Dance (`td_copy_paste_pc`). |
| **`GLD`** | Gold | `#FFBF00` | `(255, 191, 0)` | 🟨 | **Enclosure Pairs & Base Tap Dances:** Symmetric bracket pairs `[ ]`, `( )`, `{ }` in `layer_SymbolNav`, and macOS Base layer tap dances (`td_copy_paste`, `td_launcher`, `td_screenshot`). |
| **`GRN`** | Green | `#00FF00` | `(0, 255, 0)` | 🟩 | **Layer Toggles & Activators:** Momentary layer thumb triggers (NumRow, SymbolNav) and permanent layer toggle keys (Keypad, PC, Gaming, Mouse). |
| **`MAG`** | Magenta | `#FF00FF` | `(255, 0, 255)` | 🟪 | **Magic Key & System Indicator:** Dedicated indicator for the Magic layer access key across all permanent layers (Base, PC, Gaming). |
| **`RED`** | Red | `#FF0000` | `(255, 0, 0)` | 🟥 | **Locks, Deletions & Exits:** Layer exit / toggle-off keys (e.g. Keypad toggle), Delete keys when standalone, Bootloader / Reset keys in Magic layer, and active CapsLock status indicator. |
| **`NML`** | NumLock | Dynamic | — | 🟢/🔴 | **NumLock Status Indicator:** Green when NumLock is ON, Red when OFF. |
| **`CPL`** | CapsLock | Dynamic | — | ⚫/🔴 | **CapsLock Status Indicator:** Unlit when OFF, Red when CapsLock or Caps Word is active. |
| **`___`** | Black / Off | `#000000` | `(0, 0, 0)` | ⬛ | **Unlit / Pass-Through:** Normal alphanumeric keys, unmodified gaming keys, transparent pass-through positions, or inactive keys. |

---

## 2. Layer Color Mapping Matrix

### Base Layer (`layer_Base`)
- **Blue (`BLU`)**: Home Row Mods (A, S, D, F and J, K, L, ;) and Left Thumb Shift (`&kp LSHFT`). Glove80 upper thumbs (Ctrl, Alt, GUI).
- **Gold (`GLD`)**: macOS tap dances (`td_copy_paste`, `td_launcher`, `td_screenshot`).
- **Green (`GRN`)**: Layer keys (`td_LAYER_Keypad`, NumRow Tab thumb, SymbolNav Del thumb).
- **Magenta (`MAG`)**: Magic key (`&magic LAYER_Magic 0`).
- **Dynamic (`CPL`)**: Caps Lock status on `td_caps`.

### PC Layer (`layer_PC`)
- Mirrors Base layer RGB highlights.
- **White (`WHT`)**: PC Copy/Paste tap dance (`td_copy_paste_pc` — 1x Ctrl+C, 2x Ctrl+V, 3x Win+V), clearly distinguished from Base layer's Gold.
- **Blue (`BLU`)**: Modifiers, Home Row Mods, and thumb Shift.
- **Magenta (`MAG`)**: Magic key.

### Gaming Layer (`layer_Gaming`)
- **Blue (`BLU`)**: Active modifier keys only (Bottom row Cmd/Super, Thumb Shift, Hold-Tap Ctrl/Space, Hold-Tap Alt/Enter).
- **Magenta (`MAG`)**: Magic key.
- **Unlit (`___`)**: All home row keys (ASDF, JKL;), numbers, and overridden non-modifier keys (Grave, Tab, Tilde, Backspace, Delete) remain dark to signify they behave as standard, non-modifier gaming keys.

### SymbolNav Layer (`layer_SymbolNav`)
- **Cyan (`CYN`)**: Function keys (F1–F12).
- **Orange (`ORG`)**: Vim navigation cluster (HJKL arrows), Home, End, PageUp, PageDown.
- **Gold (`GLD`)**: Bracket enclosure pairs `[ ]`, `( )`, `{ }`.
- **White (`WHT`)**: Double Quote (`"`) and all math/symbol operators (`@`, `#`, `!`, `$`, `%`, `^`, `&`, `*`, `+`, `-`, `=`, `/`, `\`, `|`, `<`, `>`, `~`, `` ` ``).

### Keypad Layer (`layer_Keypad`)
- **Cyan (`CYN`)**: 3x3 numeric digit block (0–9).
- **White (`WHT`)**: Arithmetic operators (`+`, `-`, `*`, `/`, `=`, `.`) and Keypad Enter.
- **Red (`RED`)**: Keypad exit toggle key (top-left).

### NumRow Layer (`layer_NumRow`)
- **Cyan (`CYN`)**: Home row numbers 1–0 across A–G and H–;.
- **Dynamic (`CPL`)**: Caps Lock indicator.

### Magic Layer (`layer_Magic`)
- **Blue (`BLU`)**: Bluetooth profile keys (BT 0, BT 1, BT 2).
- **Cyan (`CYN`)**: Volume and media controls (Vol Dn, Vol Up, Mute).
- **Red (`RED`)**: Bootloader, Reset, and system lock keys.
- **Green (`GRN`)**: Layer toggles.
- **Gold (`GLD`)**: RGB underglow controls.
