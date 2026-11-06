#!/bin/bash

set -euo pipefail

START_TIME=$(date +%s)

export PATH="/nix/var/nix/profiles/default/bin:/usr/local/bin:$PATH"
if [[ -S "/nix/var/nix/daemon-socket/socket" ]]; then
    export NIX_REMOTE="${NIX_REMOTE:-daemon}"
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

format_duration() {
    local s=$1
    local m=$((s / 60))
    local rem_s=$((s % 60))
    if (( m > 0 )); then
        printf "%dm %ds" "$m" "$rem_s"
    else
        printf "%ds" "$rem_s"
    fi
}

if [[ "${1:-}" == "--docker" ]]; then
    shift
    IMAGE=glove80-zmk-config-docker
    BRANCH="${1:-rgb-layer-26.09}"
    docker build -t "$IMAGE" "$REPO_DIR"
    docker run --rm -v "$REPO_DIR:/config" -e UID="$(id -u)" -e GID="$(id -g)" -e BRANCH="$BRANCH" "$IMAGE"
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    echo "Done docker build in $(format_duration "$ELAPSED")" >&2
    exit 0
fi

CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/glove80-zmk"
ZMK_SRC="$CACHE_ROOT/zmk-src"

if [[ ! -d "$ZMK_SRC/.git" ]] || ! git -C "$ZMK_SRC" remote get-url origin 2>/dev/null | grep -q "DunderXIII/zmk"; then
    echo "Cloning per-key RGB ZMK source (DunderXIII/zmk @ rgb-layer-26.09)..." >&2
    rm -rf "$ZMK_SRC"
    git clone --depth 1 -b rgb-layer-26.09 https://github.com/DunderXIII/zmk.git "$ZMK_SRC"
fi

echo "Building Glove80 firmware (LH + RH with per-key RGB)..." >&2
out="$(nix-build "$REPO_DIR/config" --arg firmware "import $ZMK_SRC {}" --no-out-link)"
cp "$out/glove80.uf2" "$REPO_DIR/glove80.uf2"
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo "Done: $REPO_DIR/glove80.uf2 ($(stat -c%s "$REPO_DIR/glove80.uf2") bytes) in $(format_duration "$ELAPSED")" >&2
