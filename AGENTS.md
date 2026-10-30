# Agent & Developer Guidelines: MoErgo ZMK Layouts

This document details the architecture, modification workflows, build times, and flashing procedures for the MoErgo Glove80 and Go60 keyboards in this repository.

---

## 1. Architecture Overview

- **Dual-Half Split System**: Both Glove80 and Go60 are split keyboards consisting of two independent microcontrollers (Left Half and Right Half).
- **Firmware Compilation**: Builds use MoErgo ZMK distribution with per-key RGB underglow layers (`DunderXIII/zmk @ rgb-layer-26.09`).
- **Combined UF2**: `nix-build` compiles both LH and RH images and packages them into a single `glove80.uf2` or `go60.uf2`.
- **CRITICAL - Flashing Requirement**:
  > [!IMPORTANT]
  > Whenever flashing new firmware, **ALWAYS flash BOTH halves** (`GLV80LHBOOT` and `GLV80RHBOOT`).
  > Flashing only one half leaves the other half running the older firmware version, causing keymap and RGB inconsistencies (e.g. right-side RGB layers or navigation keys appearing unlit or unresponsive).

---

## 2. Standard Layout Update Procedure

Whenever modifying keyboard layouts, follow these steps sequentially:

### Step 1: Update the Keymap File (`*.keymap`)
- Target: `glove80/config/glove80.keymap` or `go60/config/go60.keymap`.
- Update custom behaviors (e.g., tap dances, mod-taps, combos) in `/ { behaviors { ... } };`.
- Update key bindings in `/ { keymap { ... } };` across all relevant layers (`layer_Base`, `layer_PC`, `layer_Gaming`, `layer_SymbolNav`, `layer_Keypad`, etc.).

### Step 2: Update the Per-Key RGB Map (`underglow-layer`)
- Target: `/ { underglow-layer { ... } };` inside `*.keymap`.
- **Always update the RGB map whenever keys or layer behaviors change!**
- Each layer inside `underglow-layer` mirrors the exact physical key positions of the keymap.
- Common color tokens:
  - `MAG` (Magenta): Navigation / arrow keys / PgUp / PgDn.
  - `CYN` (Cyan): Function keys (F1–F12).
  - `ORG` (Orange): Brackets, quotes, operators, and thumb indicators.
  - `GLD` (Gold): Inner symbol cluster.
  - `RED` (Red): Locks, deletions, system/exit keys, CapsLock active.
  - `BLU` (Blue): PC overlay / Bluetooth indicators.
  - `GRN` (Green): Keypad digit block.
  - `___` (Transparent): LED unlit / pass-through.
- Ensure right-hand keys (such as `PG_UP` and `PG_DN` under F12) have their corresponding positions updated in `layer_SymbolNav`.

### Step 3: Synchronize Layout Editor JSON (`*.json`)
- Target: `glove80/config/glove80.json` or `go60/config/go60.json`.
- Keep the MoErgo Layout Editor JSON files synchronized with `.keymap`:
  - Update custom behaviors in `custom_behaviors`.
  - Update the layer arrays in `layers`.
  - Update the documentation in the top-level `"notes"` field summarizing new features and layer changes.
- Keeping JSON in sync guarantees layouts can be imported into the MoErgo web GUI without losing custom modifications.

### Step 4: Build Firmware
- Run the local build script:
  ```bash
  # Glove80
  ./glove80/build.sh

  # Go60
  ./go60/build.sh
  ```
- The build script measures and prints the elapsed compilation time upon completion:
  ```
  Done: /home/.../glove80/glove80.uf2 (888832 bytes) in 3m 42s
  ```

### Step 5: Flash Firmware to BOTH Halves
- Enter bootloader mode on **both halves**:
  - **Left half:** Hold `Magic` + tap `ESC` (or double-click physical reset button). Mounts as `GLV80LHBOOT`.
  - **Right half:** Hold `Magic` + tap `'` (or double-click physical reset button). Mounts as `GLV80RHBOOT`.
- Flash using the helper script:
  ```bash
  ./glove80/flash.sh
  ```
  *(Or copy `glove80.uf2` directly to both `/run/media/$USER/GLV80LHBOOT/` and `/run/media/$USER/GLV80RHBOOT/`)*.

---

## 3. Rough Build Times Reference

Build times using the local Nix environment (`nix-build` with persistent caches in `~/.cache/*-zmk`):

| Keyboard | Build Type | Rough Time Elapsed |
| :--- | :--- | :--- |
| **Glove80** | Clean build (fresh checkout / cold cache) | ~3m 30s – 4m 30s |
| **Glove80** | Incremental build (keymap / RGB edits) | ~1m 30s – 2m 30s |
| **Go60** | Clean build (fresh checkout / cold cache) | ~2m 30s – 3m 30s |
| **Go60** | Incremental build (keymap / RGB edits) | ~1m 00s – 2m 00s |
