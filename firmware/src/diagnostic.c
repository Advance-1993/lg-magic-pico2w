#include "diagnostic.h"
#include "pico/stdlib.h"
#include "pico/bootrom.h"
#include "pico/util/queue.h"
#include "tusb.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <stdatomic.h>
typedef struct { char text[1200]; } log_line;
static queue_t logs, commands;
static atomic_uint dropped;
void diag_init(void) {
    queue_init(&logs, sizeof(log_line), 64);
    queue_init(&commands, 96, 8);
}
void diag_log(const char *fmt, ...) {
    log_line line;
    int prefix = snprintf(line.text, sizeof(line.text), "[%lu] ", (unsigned long)to_ms_since_boot(get_absolute_time()));
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(line.text + prefix, sizeof(line.text) - prefix, fmt, ap);
    va_end(ap);
    if (!queue_try_add(&logs, &line)) atomic_fetch_add(&dropped, 1);
}
void diag_hex(const char *kind, unsigned service, unsigned id, const uint8_t *data, unsigned len) {
    // BTstack HID events already include the report ID as byte zero.
    // Chunk descriptors and reports to retain all bytes without truncation.
    for (unsigned offset = 0; offset < len; offset += 256) {
        char hex[513];
        unsigned n = len - offset;
        if (n > 256) n = 256;
        for (unsigned i = 0; i < n; ++i) snprintf(hex + 2*i, 3, "%02X", data[offset+i]);
        hex[2*n] = 0;
        diag_log("%s svc=%u id=%02X len=%u offset=%u data=%s\n", kind, service, id, len, offset, hex);
    }
    if (!len) diag_log("%s svc=%u id=%02X len=0\n", kind, service, id);
}
bool diag_get_command(char *command) { return queue_try_remove(&commands, command); }
void diag_usb_task(void) {
    static log_line pending;
    static size_t offset, length;
    static char command[96];
    static unsigned used;
    static bool overflow;
    if (!tud_cdc_connected()) return;
    while (tud_cdc_available()) {
        char c = tud_cdc_read_char();
        if (c == '\n' || c == '\r') {
            if (overflow) diag_log("COMMAND too long; rejected\n");
            else if (used) {
                command[used] = 0;
                if (!strcmp(command, "bootsel")) reset_usb_boot(0, 0);
                else if (!strcmp(command, "help")) diag_log("LG BRIDGE version=%s pico2_w HID=%u; commands: status, history, reconnect probe, power timeout [seconds], power status/sleep/idle on/off, scan, pair AA:BB:CC:DD:EE:FF 0|1, disconnect, resume, forget [AA:BB:CC:DD:EE:FF 0|1], bootsel; HID commands: mouse on/off/status, mouse gain 1..100 (decimals allowed), calibrate; map list/reset/set CODE key|consumer|pointer|none VALUE; no vendor writes\n", LG_BRIDGE_VERSION, LG_ENABLE_HID);
                else if (!queue_try_add(&commands, command)) diag_log("COMMAND queue full\n");
            }
            used = 0;
            overflow = false;
        } else if (used < sizeof(command)-1) command[used++] = c;
        else overflow = true;
    }
    if (offset == length && queue_try_remove(&logs, &pending)) {
        offset = 0;
        length = strlen(pending.text);
    }
    if (offset < length) {
        unsigned n = tud_cdc_write_available();
        if (n > length-offset) n = length-offset;
        offset += tud_cdc_write(pending.text+offset, n);
        tud_cdc_write_flush();
    }
    static uint32_t last;
    uint32_t now = to_ms_since_boot(get_absolute_time());
    if (now-last >= 5000) {
        last = now;
        diag_log("HEARTBEAT dropped_log_lines=%u\n", atomic_load(&dropped));
    }
}
