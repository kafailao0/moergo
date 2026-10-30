# MoErgo ZMK Configurations (`glove80` & `go60`)

Unified ZMK configuration repository for both the **MoErgo Glove80** and **MoErgo Go60** keyboards, including per-key RGB layer indicators (`DunderXIII/zmk @ rgb-layer-26.09`).

## Directory Structure

- [`glove80/`](./glove80): Glove80 keymap (`glove80/config/glove80.keymap`), MoErgo Layout Editor JSON (`glove80/config/glove80.json`), Kconfig (`glove80/config/glove80.conf`), and local build/flash scripts (`glove80/build.sh`, `glove80/flash.sh`).
- [`go60/`](./go60): Go60 keymap (`go60/config/go60.keymap`), MoErgo Layout Editor JSON (`go60/config/go60.json`), Kconfig (`go60/config/go60.conf`), and local build script (`go60/build.sh`).

## Documentation & Developer Guidelines

- See [`AGENTS.md`](./AGENTS.md) for layout modification workflows, RGB mapping instructions, build time references, and dual-half flashing requirements.

## Local Firmware Build

```bash
# Build Glove80 firmware (outputs glove80/glove80.uf2)
./glove80/build.sh

# Build Go60 firmware (outputs go60/go60.uf2)
./go60/build.sh
```
