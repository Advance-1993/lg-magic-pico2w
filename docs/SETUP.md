# From a blank Pico 2 W to working input

## 1. Hardware and recovery

You need a **Pico 2 W**, a USB **data** cable, an MR25GA, batteries, Windows and
access to the remote's original TV. No soldering or separate Bluetooth dongle.
Check the model printed inside the remote's battery compartment.

Confirm that you can restore the remote to its TV before changing registration.
For the tested remote: hold **Back + Home for five seconds** to unregister;
then point at the powered-on original TV and press **Wheel/OK** to register.
Check the instructions for your actual model. Unplug the original TV from mains
during Pico pairing so it cannot capture the remote. Do not use Back+Home for
ordinary wake/reconnection. Only Pico firmware/configuration is changed.

## 2. Preserve existing firmware where possible

A truly blank board has no previous application to preserve. If the board has
unknown firmware, back it up **before** copying a UF2. The companion's Install
new Pico flow needs official `picotool` on PATH (or `tools/picotool/picotool.exe`).
It checks RP2350/4MB/secure-boot-disabled identity, saves and verifies all external
flash, pins operations to the detected serial, verifies firmware and reboots.
RP2350 identity alone cannot prove the wireless board model; check its label.

Backups contain private pairing keys/configuration: store locally, never upload.
They cover external flash only, not RAM or OTP, and belong to that same board.
If backup fails, stop rather than overwrite an application you want to preserve.
No erase, OTP modification or forced reset is part of the installer.

## 3. Install the prebuilt application

For a confirmed blank board, or after a successful backup:

1. Hold BOOTSEL while connecting USB, then release it. ROM boot mode does not erase.
2. Verify the UF2 against `uf2/SHA256SUMS.txt` (PowerShell: `Get-FileHash path -Algorithm SHA256`).
3. Copy `uf2/mr25ga-pico2w-airmouse-v0.25.uf2` to the Pico's boot drive.
4. The board reboots and Windows enumerates USB keyboard, mouse, media and serial.

Do not copy an old upstream Pico W binary. The diagnostic image has CDC serial
only and cannot control the PC; use it for an unknown remote protocol.
A normal application update retains saved bonds, mappings, timeout and calibration.

## 4. Run the optional companion

Install Python 3.13 with Tk support from python.org (the Windows installer normally
includes Tk). Open PowerShell in this project directory:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe companion.py
```

Alternatively run `companion.ps1` after creating the environment, if local
PowerShell policy permits. The Python command requires no policy change.
Use **Connect USB**. Close other serial monitors; only one app owns the port.
Windows supplies ordinary HID/CDC drivers. `picotool` bootloader access can need
the official supported Windows driver/setup; see its upstream instructions.

## 5. Pair your remote

1. Keep the original TV fully unplugged. Put the remote close to the Pico.
2. In the companion choose **Pair remote** and follow each confirmation.
3. Confirm physical MR25GA and TV recovery. The wizard pauses the old connection.
4. Hold Back+Home once for five seconds, then press Wheel/OK near the Pico.
5. Select the freshly observed address/type. Do not copy somebody else's address.
6. Confirm replacement; the wizard removes the stale local bond and arms that peer.
7. If asked, press **only Wheel/OK** again. Do not repeat unregistration.
8. Check HID readiness **and actual Live input**. Pairing alone is not usable input.

The Pico stores one selected peer. Bluetooth remains encrypted; no guessed
vendor commands, motion activation writes, microphone or remote updates are used.
Unknown model: use CDC-only diagnostic, record descriptors/labeled reports and
adapt the decoder; an advertising name alone does not establish compatibility.

CLI alternative: `.venv/Scripts/python.exe manage.py pair`.

## 6. Verify and calibrate

Test arrows/OK/Back and both wheel directions in Kodi. Channel buttons control
Windows media volume. Original volume buttons send F23/F24 until you remap them.
Use Output keys to choose Media Play/Pause for Settings if wanted; save and verify.

Use AI to enable pointer; test directions, short clicks and holding OK200ms to drag
a window. Calibrate with the remote flat and completely untouched until completion.
Save speed to taste; the built-in default calibration is only a starting point.
Arrow/Back/Home exit pointer mode. Test USB reconnect and battery removal yourself.

## 7. Inactivity, LED and everyday use

Connection tab: save inactivity timeout; default90seconds. Choices are30,60,90,180
seconds;4–13minutes;30,45,60minutes;2,4,6,12hours. The Pico enforces it with the
companion closed. Real buttons/scroll and active pointer motion count as use;
neutral gyro packets with pointer off do not. Pointer-only idle limit is120seconds.

Idle disconnect retains the bond. Picking up or pressing a BLE-capable button can
wake the remote; the first action is forwarded only if the remote sends it after
the link is ready. Otherwise press again. Not all buttons necessarily transmit BLE.
LED is solid only while a controller link exists, off without one. Pickup alone can
reconnect. USB-host unavailable (e.g. shutdown/suspend) pauses radio after a grace
period even if USB still supplies power. No direct battery-life measurement is claimed.

## Troubleshooting / return to TV

No response: check batteries, USB data cable, actual board model, selected serial,
TV isolation and Live input. Try an ordinary button; then Resume remote. Re-pair
only if needed. Close companion before a separate serial tool. A stale cache has
automatic full-discovery fallback; no security downgrade is needed.

To restore TV use, disconnect the Pico, power on the original TV, follow its
unregister/register instructions above and verify TV operation. Returning to the
Pico later may require fresh pairing. Sharing a remote simultaneously with TV
and Pico is not a supported mode; some IR buttons can still control a nearby TV.
