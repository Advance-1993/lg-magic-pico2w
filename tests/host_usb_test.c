#include <assert.h>
#include <stdio.h>
#include "../firmware/src/host_usb.c"
static bool configured,suspended;
bool tud_mounted(void) { return configured; }
bool tud_suspended(void) { return suspended; }
int main(void) {
 host_usb_init();host_usb_task();assert(!host_usb_active());
 configured=true;host_usb_task();assert(host_usb_active());
 host_usb_state_t s=host_usb_state();assert(s.mounts==1 && s.changes==1);
 host_usb_task();assert(host_usb_state().changes==1);
 suspended=true;host_usb_task();assert(!host_usb_active() && host_usb_state().suspends==1);
 suspended=false;host_usb_task();assert(host_usb_active() && host_usb_state().resumes==1);
 configured=false;host_usb_task();assert(!host_usb_active());
 puts("PASS: actual USB monitor configured/suspend/resume/unmount and stable snapshots");return 0;
}
