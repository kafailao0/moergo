#!/bin/bash

set -euo pipefail

export PATH="/nix/var/nix/profiles/default/bin:/usr/local/bin:$PATH"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--docker" ]]; then
    shift
    IMAGE=glove80-zmk-config-docker
    BRANCH="${1:-rgb-layer-26.09}"
    docker build -t "$IMAGE" "$REPO_DIR"
    docker run --rm -v "$REPO_DIR:/config" -e UID="$(id -u)" -e GID="$(id -g)" -e BRANCH="$BRANCH" "$IMAGE"
    exit 0
fi

CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/glove80-zmk"
ZMK_SRC="$CACHE_ROOT/zmk-src"
COMPILE_SCRIPT="$CACHE_ROOT/compileZmk/bin/compileZmk"
export CCACHE_DIR="$CACHE_ROOT/ccache"

mkdir -p "$CCACHE_DIR"

if [[ ! -d "$ZMK_SRC/.git" ]] || ! git -C "$ZMK_SRC" remote get-url origin 2>/dev/null | grep -q "DunderXIII/zmk"; then
    echo "Cloning per-key RGB ZMK source (DunderXIII/zmk @ rgb-layer-26.09)..." >&2
    rm -rf "$ZMK_SRC" "$CACHE_ROOT/compileZmk" "$CACHE_ROOT/build_lh" "$CACHE_ROOT/build_rh"
    git clone --depth 1 -b rgb-layer-26.09 https://github.com/DunderXIII/zmk.git "$ZMK_SRC"
fi

if [[ ! -x "$COMPILE_SCRIPT" ]]; then
    echo "Initializing MoErgo ZMK compiler from Nix cache (one-time setup)..." >&2
    nix-build "$ZMK_SRC/release.nix" -A zmkCompileScript -o "$CACHE_ROOT/compileZmk"
fi

KEYMAP="$REPO_DIR/config/glove80.keymap"
KCONFIG="$REPO_DIR/config/glove80.conf"

build_half() {
    local board="$1"
    local build_dir="$2"

    mkdir -p "$build_dir"
    local kconfig_hash
    kconfig_hash="$(sha256sum "$KCONFIG" | awk '{print $1}')"
    local prev_kconfig_hash=""
    [[ -f "$build_dir/.kconfig_hash" ]] && prev_kconfig_hash="$(cat "$build_dir/.kconfig_hash")"

    cd "$build_dir"
    if [[ -f "$build_dir/zephyr/libzephyr.a" && "$kconfig_hash" == "$prev_kconfig_hash" ]]; then
        eval "$(grep '^export PATH=' "$COMPILE_SCRIPT")"
        eval "$(grep '^export CMAKE_PREFIX_PATH=' "$COMPILE_SCRIPT")"
        export CCACHE_BASEDIR="$PWD"
        export CCACHE_NOHASHDIR=t
        export CCACHE_COMPILERCHECK=none

        local dt_hdr="zephyr/include/generated/devicetree_generated.h"
        local sys_list="zephyr/misc/generated/syscalls_file_list.txt"
        local sys_json="zephyr/misc/generated/syscalls.json"
        local dt_ref
        dt_ref="$(mktemp)"
        touch -r "$dt_hdr" "$dt_ref"

        cmake -DKEYMAP_FILE="$KEYMAP" -DEXTRA_CONF_FILE="$KCONFIG" .

        touch -r "$dt_ref" "$dt_hdr" "$sys_list" "$sys_json"
        rm -f "$dt_ref"

        rm -rf CMakeFiles/app.dir/src/{keymap.c.obj,combo.c.obj,conditional_layer.c.obj,rgb_underglow.c.obj,rgb_underglow_layer.c.obj,pointing,behaviors} app/libapp.a
        ninja
    else
        "$COMPILE_SCRIPT" -b "$board" -k "$KEYMAP" -c "$KCONFIG"
        echo "$kconfig_hash" > "$build_dir/.kconfig_hash"
    fi
}

echo "Building Glove80 firmware (LH + RH with per-key RGB)..." >&2
build_half "glove80_lh" "$CACHE_ROOT/build_lh"
build_half "glove80_rh" "$CACHE_ROOT/build_rh"

cat "$CACHE_ROOT/build_lh/zephyr/zmk.uf2" "$CACHE_ROOT/build_rh/zephyr/zmk.uf2" > "$REPO_DIR/glove80.uf2"
echo "Done: $REPO_DIR/glove80.uf2 ($(stat -c%s "$REPO_DIR/glove80.uf2") bytes)" >&2
