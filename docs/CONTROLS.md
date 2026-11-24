# Buttons and companion

Factory defaults are in `firmware/src/mapping_config.h`. Saved per-board mappings
override them. The live view reads the active mapping; labels are editable locally.

| Raw code | Physical button | Factory output |
| --- | --- | --- |
|8040 /8041 /8007 /8006|Up / Down / Left / Right|Arrow keys|
|8044|Wheel/OK|Enter; left mouse in pointer mode|
|8028|Back|Escape|
|807C|Home house|Left Windows/Start|
|8002 /8003|Volume + / −|F23 / F24|
|8000 /8001|Channel + / −|Media volume + / −|
|808B|AI/Voice|Pointer toggle|
|8056 /805C /8031 /8049 /8048 /800C|Streaming1–6 in captured order|F13–F18|
|8029|Screen with question mark|F19|
|80A1|Home in circle|F20|
|80AB|Guide|F21|
|8045|123|F22|
|8043|Select/Settings|F12|

Power stays unmapped. No AHK automation is installed by this project. Brand names
and physical shortcut order can vary; capture one labeled press at a time.

## Pointer

AI toggles; OK sends immediate USB left-down. The first200ms suppress movement,
then holding allows dragging. Release sends up and freezes motion120ms to avoid
release shake. A short press stays a normal click. Arrows/Back/Home/original volume
leave pointer mode. Watchdog/disconnect/mode exit/USB remount force neutral releases.
Mouse gain1–100 and stationary calibration persist on the Pico. No right-click
gesture, microphone, absolute pointing or threshold slider is implemented.

## Tabs and tools

- Live input: physical label, raw code, Windows output, press/release and scroll.
- Button mappings: readable current table; display labels can be customized.
- Output keys: read/save/reset USB outputs, with flash readback before success.
- Connection: saved inactivity timeout, state and recent RAM-only history.
- Device info: actual connected/saved peer and firmware; battery field is unvalidated.
- Install new Pico: correct-board check, full-flash verified backup, verified load.

Read mappings before editing; never confuse factory defaults with saved settings.
Only one serial connection may be open. Companion can run a narrow local request
transport for the optional `python remote_action.py` helper (explicit pointer-on); nothing binds F22
automatically. Logs, labels and `_runtime` files are local and ignored by Git.

For serial work use `python manage.py --help`, `python manage.py console`, then
`help` for the firmware's command list. Prefer GUI guided pairing over hand-written
forget/pair commands. Never send speculative vendor commands to the remote.
