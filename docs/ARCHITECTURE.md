# Architecture and protocol

BLE central on the Pico scans for the explicitly selected remote, uses persistent
bond/encryption, subscribes to HID-over-GATT reports and decodes measured MR25GA
input. TinyUSB exposes keyboard, relative mouse and consumer control plus CDC.
The Linux lg-magic driver is a protocol reference, not a Pico dependency.

Only validated20-byte FD reports are decoded: byte0=FD, button code big-endian
bytes17–18, signed wheel byte19. Gyro axes are signed big-endian pairs at5–10;
measured mouse X uses gyro Z and Y uses gyro X, after bias/deadband/filtering.
This is not a generic descriptor-forwarding bridge or universal LG profile.

## Main sources

- `hog_host_demo.c`: scanning, selected identity, security, HID discovery and power policy.
- `bridge_hid.c`: decoder, standard USB outputs, calibration, clicks and dragging.
- `host_usb.c`, `power_policy.h`: host availability, activity and quiet-gated wake.
- `hid_reconnect.c`, `hids_client_cached.c`: one RAM HID cache, admission/fallback.
- `mapping_config.h`, `power_config.h`: validated persistent records.
- `companion.py`, `manage.py`: optional desktop UI and guided serial tooling.

Cache is limited to the same public bonded identity with encryption. It copies
bounded descriptors/services/report metadata, not live listener pointers. Standard
Service Changed invalidates it. CCC writes require success; failures use full
discovery. First connection after boot still discovers fully. No vendor command.

`hids_client_cached.c` derives from Pico SDK2.2.0 BTstack commit
501e6d2b86e6c92bfb9c390bcf55709938e25ac1. Original hids_client.c SHA256:
b06ef344f0c22dfe795be82a2b2d8756ecfa18111fcbf497a945f8c71d7e93a7.
CMake checks this before substitution in this build graph. The SDK is not edited.
See `references/hids-client-cache-v0.22.patch`; retain original source licenses.

Disconnect, watchdog and remount retry neutral keyboard/mouse/media reports before
new input; never remove those guarantees to optimize latency. Power history is a
bounded RAM ring. Do not write flash on each report or event. Full flash can contain
BLE keys; build outputs must never be made by reading back a provisioned board.
