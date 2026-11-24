#pragma once
#include <stdint.h>
#include <stdbool.h>
#define HOST_USB_CONFIGURED 1u
#define HOST_USB_SUSPENDED 2u
typedef struct { uint32_t flags, changes, mounts, suspends, resumes; } host_usb_state_t;
void host_usb_init(void);
void host_usb_task(void);
host_usb_state_t host_usb_state(void);
bool host_usb_active(void);
