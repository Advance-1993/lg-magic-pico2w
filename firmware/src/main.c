#include "bsp/board_api.h"
#include "tusb.h"
#include "Common.h"
#include "diagnostic.h"
#include "bridge_hid.h"
#include "host_usb.h"
extern void ble_host_main(void);
// Kept for upstream BLE code; USB diagnostic never re-enumerates.
volatile bool g_usb_reinit_request;
static uint32_t ble_stack[4096] __attribute__((aligned(8)));
int main(void) {
    board_init();
    diag_init();
    bridge_hid_init();
    host_usb_init();
    CMN_Init();
    tud_init(BOARD_TUD_RHPORT);
    if (board_init_after_tusb) board_init_after_tusb();
    flash_safe_execute_core_init();
    diag_log("BOOT LG BRIDGE board=pico2_w HID=%u; no vendor writes\n", LG_ENABLE_HID);
    multicore_launch_core1_with_stack(ble_host_main, ble_stack, sizeof(ble_stack));
    for (;;) { tud_task(); host_usb_task(); diag_usb_task(); bridge_hid_task(); }
}
