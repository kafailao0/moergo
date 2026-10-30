# MoErgo Glove80 Custom Configuration for ZMK

![MoErgo Logo](moergo_logo.png)

This repo is the official ZMK configuration of the MoErgo Glove80 wireless split contoured keyboard. Use it to develop your own keymap and easily build your own ZMK firmware to run on your Glove80.

**NOTE: You can also customize the layout of your Glove80 keyboard with the Glove80 Layout Editor webapp. For most users Glove80 Layout Editor is the recommended and simpler option. More information is available at the official MoErgo Glove80 Support site (see resources below).**

These steps will get you using your keymap on your keyboard in the fastest time possible. It uses the GitHub Actions feature to build your firmware online.

If you are looking to dig deeper into ZMK and develop new functionality, it is recommended to follow the steps of installing ZMK as found on the official ZMK documentation site (linked below).

## Resources
- The [official MoErgo Glove80 Support](https://moergo.com/glove80-support) web site. Glove80 documentation and other technical resources.
- The [official MoErgo Discord Server](https://moergo.com/discord). Instant conversations with other Glove80 users.

- The [official ZMK Documentation](https://zmk.dev/docs) web site. Find the answers to many of your questions about ZMK Firmware.
- The [official ZMK Discord Server](https://discord.gg/8cfMkQksSB). Instant conversations with other ZMK developers and users. Great technical resource!

- The [official Glove80 ZMK Distribution](https://github.com/moergo-sc/zmk). Repositiory for ZMK firmware customized for Glove80. 
 
## Instructions
1. Log into, or sign up for, your personal GitHub account.
2. Create your own repository using this repository as a template ([instructions](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template)) and check it out on your local computer.
3. Edit the keymap file(s) to suit your needs
4. Commit and push your changes to your personal repo. Upon pushing it, GitHub Actions will start building a new version of your firmware with the updated keymap.

## Firmware & Flashing Procedure

### 1. Build Firmware

#### Option A: Local Build (Recommended — ~10–15s)
Run the local build script, which uses MoErgo's `compileZmk` environment with a persistent CMake/Ninja cache and `ccache` (`~/.cache/glove80-zmk`) plus pre-built right-half firmware:
```bash
./build.sh
```
This outputs `glove80.uf2` directly in the repository root (~15s for a new keymap edit, ~9.5s if cached, ~1.5s for syntax validation).

*(To build using Docker instead, run `./build.sh --docker`.)*

#### Option B: Build via GitHub Actions (~2–3 min)
Push changes to your repository to trigger the automated ZMK build workflow:
```bash
git add config/glove80.keymap
git commit -m "Update keymap"
git push origin main
```

### 2. Check Build & Download Firmware (GitHub Actions only)

> **Note on Build Time**: The GitHub Actions workflow typically takes **2 to 3 minutes** to compile the firmware. Do not attempt to download immediately after pushing; wait for the run to succeed.

Using the **GitHub CLI (`gh`)**:
```bash
# Watch the workflow run in real-time until completion
gh run watch

# Or check latest run status
gh run list -L 1

# Download the latest compiled firmware artifact once the run succeeds
rm -rf glove80.uf2 && gh run download -n glove80.uf2
```
This downloads `glove80.uf2`.

Alternatively, download `glove80.uf2` manually from the **Actions** tab on your GitHub repository page under the latest run's **Artifacts** section.

### 3. Enter Bootloader Mode (Manual Physical Action Required)

> **Important**: Entering bootloader mode cannot be done purely via software commands from your computer; it **requires manual physical action on each half**:

1. **Connect via USB**: Ensure each keyboard half you wish to flash is connected to your PC with a USB-C cable (they can be connected at the same time or flashed one by one).
2. **Trigger Bootloader Mode** on **each half**:
   * **Via Keymap**: Hold the `Magic` key (bottom-left corner key on Base or Lower) and tap:
     * **Left half:** The `ESC` key (outermost key on the home row)
     * **Right half:** The `'` (`SQT`) key (outermost key on the home row)
   * **Via Hardware Reset**: Double-click the physical reset button located on the thumb cluster with a pin or paperclip.
3. The keyboard LEDs will flash/pulse, and each half will mount as an external USB mass storage drive:
   * Left half: **`GLV80LHBOOT`**
   * Right half: **`GLV80RHBOOT`**

### 4. Flash Firmware to Both Halves

#### Option A: Using the helper script
Run the provided script to flash both halves:
```bash
./flash.sh
```

> **Tip**: By default, `./flash.sh` runs in **monitor mode**. You can start `./flash.sh` *before* triggering bootloader mode. It will automatically detect, mount, flash, and reboot each half as it appears, supporting both simultaneous and one-by-one sequential flashing.
>
> To check once without waiting: `./flash.sh --once`

#### Option B: Manual Linux command
```bash
# Mount both bootloader drives
udisksctl mount -b /dev/disk/by-label/GLV80LHBOOT
udisksctl mount -b /dev/disk/by-label/GLV80RHBOOT

# Flash Left Half
cp glove80.uf2 /run/media/$USER/GLV80LHBOOT/ && sync

# Flash Right Half
cp glove80.uf2 /run/media/$USER/GLV80RHBOOT/ && sync
```

*Note: Once the `.uf2` file is copied, the keyboard half will automatically write the firmware to flash, unmount the drive, and reboot into keyboard mode.*
