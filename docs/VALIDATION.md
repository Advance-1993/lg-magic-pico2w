# Validation and limitations

Core0.25 behavior was physically tested on one Pico2W/MR25GA with Windows/Kodi:
buttons, wheel, pointer,200ms hold-to-drag, release and short Kodi clicks.
Earlier same-hardware tests covered bond persistence, USB power cycle, battery
removal, disconnect release,90second inactivity, USB-host-unavailable pause and
LED link behavior. Repeat cached connect setup measured about0.8–0.9seconds from
connect request; this is not a guaranteed physical-button-to-action latency.

Seven native suites exercise real production code for power/activity, USB,
settings/history, reconnect, cache snapshots and USB mouse click/drag/release.
41 Python tests cover companion parsing, mappings, installer transactions,
pairing tools, local transport and timeout display/readback.

## Public export

The public source is a cleaned0.25 snapshot. Personal host automation, local
identities, histories, configuration and full flash backups are excluded. Test
identities are fictional. The public UF2s are rebuilt application images with
compiler path mapping, not patched binaries or flash dumps. Their checksums differ
from the privately tested builds because compilation paths were removed.

Local build/tests, identity checks and privacy checks are recorded in
`PUBLICATION-CHECKS.json` after preparation. These exact public UF2 bytes have not
been flashed to the original board by the export process. Do not represent that
as an additional hardware test. GitHub Actions is configured but has not run on
GitHub until the repository is uploaded. A clean Windows setup on a second PC
and a second physical remote remain untested.

MR26GA compatibility, battery percentage, battery lifetime/current, equivalent
LG-TV sensor management, every regional shortcut label, microphone and simultaneous
TV/Pico pairing are unverified or unsupported. No guessed vendor commands are used.
