{ pkgs ?  import <nixpkgs> {}
, firmware ? import (if builtins.pathExists ../src then ../src else ../../src) {}
}:

let
  config = ./.;
  rgbPatches = [
    ../../patches/rgb-layer-permanent-mode.patch
    ../../patches/rgb-idle-timeout.patch
  ];

  glove80_left  = (firmware.zmk.override {
    board = "glove80_lh";
    keymap = "${config}/glove80.keymap";
    kconfig = "${config}/glove80.conf";
  }).overrideAttrs (old: {
    patches = (old.patches or []) ++ rgbPatches;
  });

  glove80_right = (firmware.zmk.override {
    board = "glove80_rh";
    keymap = "${config}/glove80.keymap";
    kconfig = "${config}/glove80.conf";
  }).overrideAttrs (old: {
    patches = (old.patches or []) ++ rgbPatches;
  });

in firmware.combine_uf2 glove80_left glove80_right
