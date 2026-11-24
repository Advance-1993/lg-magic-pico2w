# Provenance and third-party notices

| Component | Source / terms retained |
| --- | --- |
| Base BLE-to-USB bridge | https://github.com/shiomachisoft/picow_ble_usb_hid_bridge at5593015cf86a63d72c1b3c15ce9e02fffae4f48b; firmware/LICENSE.TXT and original source headers |
| hog_host_demo / cached HID client | BlueKitchen, original notices in source; BTstack LICENSE and Pico supplemental terms in LICENSES |
| Pico SDK2.2.0 | https://github.com/raspberrypi/pico-sdk; BSD3 and component notices, LICENSES/pico-sdk.txt |
| CYW43 driver / radio firmware | SDK cyw43-driver, retained license and Pico supplement in LICENSES |
| TinyUSB | https://github.com/hathach/tinyusb; MIT text retained |
| micro-ecc / pico printf | component texts retained in LICENSES |
| Protocol research | https://github.com/brainrom/lg-magic (GPL2 Linux driver; not shipped or executed here) |

Experimental MR26GA research: https://github.com/brainrom/lg-magic/pull/1 and
commit5bac91184f32c7b081aaecddcc2b9a63a024a615. Vendor/motion research:
https://github.com/brainrom/lg-magic/pull/8. These are references, not proof of
MR26GA compatibility or permission to send unverified commands.

This project adapts the base bridge to decode measured MR25GA input into standard
USB reports, adding diagnostics, pairing UI, power policy, safe reconnect caching,
mapping persistence and pointer controls. Original source headers remain intact.
No upstream Linux driver source, research image or patch set from that GPL driver
is bundled in this release. The BTstack cache patch is distributed with its
original source attribution in the corresponding file.

The full project has mixed licensing. Do not replace this with a blanket MIT
badge, remove notices, or assume commercial/other-board rights. Read LICENSE.
Dependency toolchains are downloaded separately and have their own terms.
The prebuilt application includes SDK/BTstack/CYW43/TinyUSB portions; keep the
license directory and inherited bridge notice alongside redistributed binaries.
