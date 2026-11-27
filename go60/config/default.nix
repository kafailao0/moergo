{ pkgs ?  import <nixpkgs> {}
, firmware ? import (if builtins.pathExists ../src then ../src else ../../src) {}
}:

let
  config = ./.;
  rgbPatches = [
    ../../patches/rgb-layer-permanent-mode.patch
    ../../patches/rgb-idle-timeout.patch
  ];

  go60_left = (firmware.zmk.override {
    board = "go60_lh";
    keymap = "${config}/go60.keymap";
    kconfig = "${config}/go60.conf";
  }).overrideAttrs (old: {
    patches = (old.patches or []) ++ rgbPatches;
  });

  go60_right = (firmware.zmk.override {
    board = "go60_rh";
    keymap = "${config}/go60.keymap";
    kconfig = "${config}/go60.conf";
  }).overrideAttrs (old: {
    patches = (old.patches or []) ++ rgbPatches;
    cmakeFlags = (old.cmakeFlags or []) ++ [ "-DDTS_EXTRA_CPPFLAGS=-DIS_GO60_RH=1" ];
  });

in firmware.combine_uf2 go60_left go60_right "go60"
