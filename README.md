# MoErgo ZMK Configurations (`glove80` & `go60`)

Unified ZMK configuration repository for both the **MoErgo Glove80** and **MoErgo Go60** keyboards, including per-key RGB layer indicators (`DunderXIII/zmk @ rgb-layer-26.09`).

## Directory Structure

- [`glove80/`](./glove80): Glove80 keymap (`glove80/config/glove80.keymap`), MoErgo Layout Editor JSON (`glove80/config/glove80.json`), Kconfig (`glove80/config/glove80.conf`), and local build/flash scripts (`glove80/build.sh`, `glove80/flash.sh`).
- [`go60/`](./go60): Go60 keymap (`go60/config/go60.keymap`), MoErgo Layout Editor JSON (`go60/config/go60.json`), Kconfig (`go60/config/go60.conf`), and local build script (`go60/build.sh`).
- [`viewer/`](./viewer): Interactive web visualizer and firmware simulator for both Glove80 and Go60 layouts (see [`viewer/README.md`](./viewer/README.md)).
- [`scripts/`](./scripts): Layout data extraction and visualizer compiler (`scripts/build_viewer.py`).

## Interactive Layout Viewer

The repository includes a web-based visualizer and simulator for exploring layers, composite layer stacks, tap-dances, and per-key RGB underglow:

- **Build viewer:** `python3 scripts/build_viewer.py`
- **Serve locally:** `python3 viewer/serve.py 8088` (accessible at `http://localhost:8088/`)
- For feature details and shortcuts, see [`viewer/README.md`](./viewer/README.md).

## Documentation & Developer Guidelines

- See [`AGENTS.md`](./AGENTS.md) for layout modification workflows, RGB mapping instructions, build time references, and dual-half flashing requirements.

## Local Firmware Build

```bash
# Build Glove80 firmware (outputs glove80/glove80.uf2)
./glove80/build.sh

# Build Go60 firmware (outputs go60/go60.uf2)
./go60/build.sh
```
