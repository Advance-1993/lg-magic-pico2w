#include "host_usb.h"
#include "tusb.h"
#include <stdatomic.h>
static atomic_uint flags,changes,mounts,suspends,resumes;
void host_usb_init(void) {
    atomic_init(&flags,0);atomic_init(&changes,0);atomic_init(&mounts,0);atomic_init(&suspends,0);atomic_init(&resumes,0);
}
void host_usb_task(void) {
    unsigned next=(tud_mounted() ? HOST_USB_CONFIGURED : 0u)|(tud_suspended() ? HOST_USB_SUSPENDED : 0u);
    unsigned old=atomic_load_explicit(&flags,memory_order_relaxed);
    if (next==old) return;
    if (!(old&HOST_USB_CONFIGURED) && (next&HOST_USB_CONFIGURED)) atomic_fetch_add(&mounts,1);
    if (!(old&HOST_USB_SUSPENDED) && (next&HOST_USB_SUSPENDED)) atomic_fetch_add(&suspends,1);
    if ((old&HOST_USB_SUSPENDED) && !(next&HOST_USB_SUSPENDED) && (next&HOST_USB_CONFIGURED)) atomic_fetch_add(&resumes,1);
    atomic_fetch_add(&changes,1);atomic_store_explicit(&flags,next,memory_order_release);
}
host_usb_state_t host_usb_state(void) {
    return (host_usb_state_t){atomic_load_explicit(&flags,memory_order_acquire),atomic_load(&changes),atomic_load(&mounts),atomic_load(&suspends),atomic_load(&resumes)};
}
bool host_usb_active(void) { return atomic_load_explicit(&flags,memory_order_acquire)==HOST_USB_CONFIGURED; }
