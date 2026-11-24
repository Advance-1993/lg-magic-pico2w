# LG Magic Remote → Pico 2 W → USB

Use an LG Magic Remote as a standard USB keyboard, mouse and media controller
for a Windows PC, including Kodi. The remote pairs directly with a **Raspberry Pi
Pico 2 W over Bluetooth Low Energy (BLE)**. No Windows Bluetooth pairing or
background translation app is needed for normal input.

**Start here: [blank-board setup and pairing](docs/SETUP.md).**
**Nederlandse uitleg voor publiceren: [START-HIER.md](START-HIER.md).**

## Compatibility

| Item | Status |
| --- | --- |
| Raspberry Pi Pico 2 W (RP2350, 4 MB) | Tested |
| LG MR25GA remote | Tested on one physical remote |
| LG MR26GA / other models | Not verified; diagnostic investigation required |
| Windows / Kodi | Buttons, scroll, pointer, clicks and dragging tested |
| Microphone / remote firmware updates | Not implemented |

This is a community project, unaffiliated with LG or Raspberry Pi.
A Pico W, Pico 2 without wireless, and Pi Zero 2 W are **not** interchangeable
with the supplied Pico 2 W images. Check the board's printed model.

## Features

- Persistent pairing, reconnection and an optional Windows desktop companion.
- Arrows, Enter/Back, Windows Start, wheel and standard media outputs.
- Calibrated gyro air mouse: AI toggles; Wheel/OK clicks. Hold **200 ms** to drag.
- Editable button outputs, mouse speed, calibration and Bluetooth inactivity limit.
- Default idle disconnect **90 seconds**; 21 choices up to 12 hours.
- USB-host-unavailable disconnect and neutral releases on connection loss.
- LED shows the actual Bluetooth link: solid when connected, off otherwise.
- Safe RAM HID reconnect cache with full-discovery fallback.

The optional companion is a Python/Tk desktop window, not a packaged .exe.
It provides pairing, live inputs and Windows output names, device information,
connection history, key mapping, pointer controls and a backup-first installer.

## Quick start

1. Read [SETUP](docs/SETUP.md), including TV recovery and backup limits.
2. Flash `uf2/mr25ga-pico2w-airmouse-v0.25.uf2` on a confirmed Pico 2 W.
3. Create a Python virtual environment and start the companion.
4. Use **Pair remote** with the original TV fully unplugged.
5. Test inputs and calibrate the pointer on your own remote.

Prebuilt images are application builds, **not dumps of someone's board**.
They contain no saved bonds or private device configuration. Existing board
settings are retained by a normal application update.

## Default controls

| Physical control | USB output / behavior |
| --- | --- |
| Arrows / Back / Home | Arrow keys / Escape / Windows Start |
| Wheel/OK | Enter; left mouse button in pointer mode |
| Wheel rotation | Mouse scroll |
| AI/Voice | Toggle pointer (no microphone) |
| Original Volume + / − | F23 / F24 (available for your own bindings) |
| Channel + / − | Windows media volume up / down |
| Six streaming buttons, captured order | F13–F18 |
| Screen/? / circled home / Guide / 123 | F19 / F20 / F21 / F22 |
| Select/Settings | F12; editable to Media Play/Pause for Kodi |
| Power | No USB action; original TV IR behavior remains |

**F23/F24 do not change TV volume by themselves.** This public package contains
no personal TV automation, IP addresses, credentials, shutdown hotkeys or AHK setup.
F18/F22 are ordinary keys until you deliberately bind them on your own PC.
Streaming branding can vary; confirm the actual code in Live input.

## Documentation

- [Setup, pairing, recovery and daily use](docs/SETUP.md)
- [Controls, raw codes and companion](docs/CONTROLS.md)
- [Build and test from source](docs/DEVELOPMENT.md)
- [Protocol and reconnect architecture](docs/ARCHITECTURE.md)
- [Known limitations and test coverage](docs/VALIDATION.md)
- [Privacy and safe issue reports](PRIVACY.md)
- [Contributing](CONTRIBUTING.md), [security reporting](SECURITY.md)
- [Licensing](LICENSE) and [upstream credits](THIRD_PARTY_NOTICES.md)

## License

Mixed upstream terms apply, including BlueKitchen/Raspberry Pi conditions.
This is **not** a blanket MIT/commercial-use grant for the complete firmware.
See [LICENSE](LICENSE) and retain all third-party notices when sharing firmware.
