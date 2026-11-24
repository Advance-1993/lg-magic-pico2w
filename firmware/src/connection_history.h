#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#define LINK_HISTORY_CAPACITY 32u
typedef enum {
    LINK_BOOT,LINK_USB_ON,LINK_USB_OFF,LINK_IDLE,LINK_WAKE,LINK_RESUME,LINK_MANUAL_PAUSE,
    LINK_CONNECTING,LINK_CONNECTED,LINK_SECURED,LINK_READY,LINK_FIRST_REPORT,LINK_DOWN,
    LINK_SECURITY_RETRY,LINK_SECURITY_PAUSE,LINK_CONNECT_FAILED,LINK_HID_FAILED,LINK_TIMEOUT_SAVED,
    LINK_PAIR_ARMED
} link_event_type_t;
typedef struct { uint32_t seq,ms,detail;link_event_type_t type; } link_event_t;
typedef struct { uint32_t boot,next_seq;unsigned count,head;link_event_t events[LINK_HISTORY_CAPACITY]; } link_history_t;
static inline void link_history_init(link_history_t *h,uint32_t boot) {
    memset(h,0,sizeof(*h));h->boot=boot;h->next_seq=1;
}
static inline link_event_t link_history_add(link_history_t *h,uint32_t ms,link_event_type_t type,uint32_t detail) {
    link_event_t e={h->next_seq++,ms,detail,type};if (!h->next_seq) h->next_seq=1;
    h->events[h->head]=e;h->head=(h->head+1)%LINK_HISTORY_CAPACITY;
    if (h->count<LINK_HISTORY_CAPACITY) ++h->count;
    return e;
}
static inline const link_event_t *link_history_get(const link_history_t *h,unsigned oldest_index) {
    if (oldest_index>=h->count) return NULL;
    return &h->events[(h->head+LINK_HISTORY_CAPACITY-h->count+oldest_index)%LINK_HISTORY_CAPACITY];
}
static inline const char *link_event_name(link_event_type_t type) {
    static const char *names[]={"boot","usb_available","usb_unavailable","idle_timeout","peer_wake","resume","manual_pause","connecting","connected","secured","input_ready","first_report","disconnected","security_retry","security_pause","connect_failed","hid_failed","timeout_saved","pair_armed"};
    return (unsigned)type<sizeof(names)/sizeof(names[0]) ? names[type] : "unknown";
}
