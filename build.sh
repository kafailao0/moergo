#!/bin/bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/glove80-zmk"
COMPILE_ZMK="$CACHE_ROOT/compileZmk/bin/compileZmk"

if [[ "${1:-}" == "--docker" ]]; then
    shift
    IMAGE=glove80-zmk-config-docker
    BRANCH="${1:-main}"
    docker build -t "$IMAGE" "$REPO_DIR"
    docker run --rm -v "$REPO_DIR:/config" -e UID="$(id -u)" -e GID="$(id -g)" -e BRANCH="$BRANCH" "$IMAGE"
    exit 0
fi

if [[ ! -x "$COMPILE_ZMK" ]]; then
    echo "Initializing compileZmk from Nix..." >&2
    mkdir -p "$CACHE_ROOT"
    if [[ ! -d "$CACHE_ROOT/zmk-src" ]]; then
        git clone --depth 1 -b "${1:-main}" https://github.com/moergo-sc/zmk "$CACHE_ROOT/zmk-src"
    fi
    nix-build "$CACHE_ROOT/zmk-src/release.nix" -A zmkCompileScript -o "$CACHE_ROOT/compileZmk"
fi

mkdir -p "$CACHE_ROOT/build" "$CACHE_ROOT/ccache"
export CCACHE_DIR="$CACHE_ROOT/ccache"

KCONFIG_HASH="$(sha256sum "$REPO_DIR/config/glove80.conf" | awk '{print $1}')"
PREV_KCONFIG_HASH="$(cat "$CACHE_ROOT/build/.kconfig_hash" 2>/dev/null || true)"

if [[ "${1:-}" != "--clean" && -f "$CACHE_ROOT/build/zephyr/libzephyr.a" && "$KCONFIG_HASH" == "$PREV_KCONFIG_HASH" ]]; then
    echo "Building Glove80 firmware locally (fast incremental keymap build)..." >&2
    (
        cd "$CACHE_ROOT/build"
        eval "$(grep -E '^(export PATH=|export CMAKE_PREFIX_PATH=|    merge_rhs_firmware=.*glove80_rh)' "$COMPILE_ZMK")"
        export CCACHE_BASEDIR="$PWD"
        export CCACHE_NOHASHDIR=t
        export CCACHE_COMPILERCHECK=none

        # Save timestamps of OS-wide headers so Ninja only rebuilds ZMK keymap/behavior targets
        touch -r zephyr/include/generated/devicetree_generated.h .stamp_dt
        touch -r zephyr/misc/generated/syscalls_file_list.txt .stamp_sys
        touch -r zephyr/misc/generated/syscalls.json .stamp_syscalls

        cmake . >/dev/null

        touch -r .stamp_dt zephyr/include/generated/devicetree_generated.h
        touch -r .stamp_sys zephyr/misc/generated/syscalls_file_list.txt
        touch -r .stamp_syscalls zephyr/misc/generated/syscalls.json zephyr/misc/generated/struct_tags.json

        rm -rf CMakeFiles/app.dir/src/{keymap.c.obj,combo.c.obj,conditional_layer.c.obj,rgb_underglow.c.obj,pointing,behaviors} app/libapp.a

        ninja
        cat zephyr/zmk.uf2 "$merge_rhs_firmware" > zmk.uf2
    )
else
    echo "Building Glove80 firmware locally (full Left-Half + pre-built RHS)..." >&2
    (
        cd "$CACHE_ROOT/build"
        "$COMPILE_ZMK" -m -b glove80_lh \
            -k "$REPO_DIR/config/glove80.keymap" \
            -c "$REPO_DIR/config/glove80.conf"
        echo "$KCONFIG_HASH" > .kconfig_hash
    )
fi

cp -f "$CACHE_ROOT/build/zmk.uf2" "$REPO_DIR/glove80.uf2"
echo "Done! Firmware written to: $REPO_DIR/glove80.uf2 ($(stat -c %s "$REPO_DIR/glove80.uf2") bytes)" >&2
